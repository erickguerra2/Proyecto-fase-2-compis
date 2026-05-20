"""Arboles de derivacion: estructura, renderizado ASCII y construccion desde tokens reales."""

from __future__ import annotations
from typing import List, Optional, Tuple
from src.cfg_grammar import Grammar


class ParseTree:
    """Nodo de un arbol de derivacion (parse tree)."""

    def __init__(self, label: str, children: Optional[List['ParseTree']] = None):
        self.label    = label
        self.children = list(children) if children else []

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def yield_string(self) -> str:
        if self.is_leaf():
            return "" if self.label == "e" else self.label
        parts = [c.yield_string() for c in self.children]
        return " ".join(p for p in parts if p)

    def render(self) -> str:
        lines: List[str] = []
        _render_node(self, lines, "", "")
        return "\n".join(lines)


def _render_node(node: ParseTree, lines: list, prefix: str, child_prefix: str) -> None:
    lines.append(prefix + node.label)
    for i, child in enumerate(node.children):
        last = (i == len(node.children) - 1)
        if last:
            _render_node(child, lines, child_prefix + "\\-- ", child_prefix + "    ")
        else:
            _render_node(child, lines, child_prefix + "+-- ", child_prefix + "|   ")


# Helpers para buscar operadores en la lista de tokens real

def _tok_label(tok) -> str:
    """Devuelve la etiqueta legible de un token (lexema si existe, tipo si no)."""
    return tok[1] if len(tok) > 1 and tok[1] and tok[1] != tok[0] else tok[0]


def _find_op_positions(tokens: list, ops: list) -> List[int]:
    """Posiciones (indices) donde aparece la secuencia de operadores en tokens."""
    n = len(ops)
    positions = []
    for i in range(len(tokens) - n + 1):
        if all(tokens[i + j][0] == ops[j] or tokens[i + j][1] == ops[j]
               for j in range(n)):
            positions.append(i)
    return positions


def _split_by_ops(tokens: list, op_positions: List[int], op_len: int) -> List[list]:
    """Divide tokens en segmentos separados por las posiciones de operador."""
    segments, prev = [], 0
    for pos in op_positions:
        segments.append(tokens[prev:pos])
        prev = pos + op_len
    segments.append(tokens[prev:])
    return segments


# Construccion de arboles desde tokens REALES de la cadena de entrada

def build_trees_from_tokens(
        grammar: Grammar, nt: str, tokens: list
) -> Tuple[Optional['ParseTree'], Optional['ParseTree']]:
    """Para NT con patron E->E op E y los tokens reales del input,
    construye el arbol de asociacion izquierda y el de derecha.

    tokens: lista de (tipo, lexema, linea, col) del input real.
    Retorna (arbol_izquierda, arbol_derecha) o (None, None).
    """
    non_eps  = [p for p in grammar.productions.get(nt, []) if p]
    rec_prod = next(
        (p for p in non_eps if p[0] == nt and p[-1] == nt and len(p) > 1),
        None
    )
    if not rec_prod:
        return None, None

    ops         = rec_prod[1:-1]
    real_tokens = [t for t in tokens if t[0] not in ("WS", "WHITESPACE", "NEWLINE", "$")]

    op_positions = _find_op_positions(real_tokens, ops)
    if not op_positions:
        return None, None

    segments = _split_by_ops(real_tokens, op_positions, len(ops))
    if len(segments) < 2:
        return None, None

    def seg_tree(seg: list) -> 'ParseTree':
        if not seg:
            return ParseTree(nt, [ParseTree("e")])
        # Si el segmento tiene sub-operadores, expandir recursivamente
        sub_ops = _find_op_positions(seg, ops)
        if sub_ops:
            sub_segs = _split_by_ops(seg, sub_ops, len(ops))
            acc = seg_tree(sub_segs[0])
            for i, sop in enumerate(sub_ops):
                op_nodes = [ParseTree(_tok_label(seg[sop + j])) for j in range(len(ops))]
                acc = ParseTree(nt, [acc] + op_nodes + [seg_tree(sub_segs[i + 1])])
            return acc
        # Un solo token o varios terminales sin operador: hoja NT -> terminales
        children = [ParseTree(_tok_label(t)) for t in seg]
        return ParseTree(nt, children) if len(children) > 1 else ParseTree(nt, children)

    def op_leaves(pos: int) -> List['ParseTree']:
        return [ParseTree(_tok_label(real_tokens[pos + j])) for j in range(len(ops))]

    # Asociacion izquierda: seg0 op seg1 op seg2 de izquierda a derecha
    tree_left = seg_tree(segments[0])
    for i, opos in enumerate(op_positions):
        tree_left = ParseTree(nt, [tree_left] + op_leaves(opos) + [seg_tree(segments[i + 1])])

    # Asociacion derecha: seg0 op seg1 op seg2 de derecha a izquierda
    tree_right = seg_tree(segments[-1])
    for i in range(len(op_positions) - 1, -1, -1):
        opos = op_positions[i]
        tree_right = ParseTree(nt, [seg_tree(segments[i])] + op_leaves(opos) + [tree_right])

    return tree_left, tree_right


# Arboles para producciones duplicadas

def build_duplicate_trees(
        grammar: Grammar, nt: str, prod: list
) -> Tuple[str, Optional['ParseTree'], Optional['ParseTree']]:
    """Para una produccion duplicada construye dos arboles identicos en estructura.
    Ambos representan derivaciones distintas de la misma cadena usando copias
    diferentes de la misma produccion."""
    def make_tree() -> 'ParseTree':
        children = [_derive_leaf(grammar, sym) for sym in prod] if prod else [ParseTree("e")]
        return ParseTree(nt, children)

    t1      = make_tree()
    t2      = make_tree()
    witness = t1.yield_string() or nt
    return witness, t1, t2


# Derivacion minima, fallback cuando no hay tokens reales

def _derive_leaf(grammar: Grammar, symbol: str,
                 visited: Optional[frozenset] = None) -> 'ParseTree':
    if visited is None:
        visited = frozenset()
    if symbol not in grammar.productions or symbol in grammar.terminals:
        return ParseTree(symbol)
    if symbol in visited:
        return ParseTree(symbol)
    visited = visited | {symbol}
    prods   = grammar.productions.get(symbol, [])
    non_rec = [p for p in prods if p and symbol not in p]
    candidates = sorted(non_rec, key=len) if non_rec else sorted(prods, key=len)
    if not candidates:
        return ParseTree(symbol)
    prod = candidates[0]
    if not prod:
        return ParseTree(symbol, [ParseTree("e")])
    return ParseTree(symbol, [_derive_leaf(grammar, s, visited) for s in prod])
