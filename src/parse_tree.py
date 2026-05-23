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
    """Posiciones donde aparece la secuencia de operadores al nivel 0 (fuera de parentesis)."""
    n = len(ops)
    positions = []
    depth = 0
    i = 0
    while i <= len(tokens) - n:
        ttype = tokens[i][0]
        tlex  = tokens[i][1] if len(tokens[i]) > 1 else ""
        if ttype == "LPAREN" or tlex == "(":
            depth += 1
            i += 1
            continue
        if ttype == "RPAREN" or tlex == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and all(
            tokens[i + j][0] == ops[j] or tokens[i + j][1] == ops[j]
            for j in range(n)
        ):
            positions.append(i)
        i += 1
    return positions


# Construccion de arboles desde tokens REALES de la cadena de entrada

def _collect_splits(rec_prods: list, toks: list) -> list:
    """Posiciones de todos los operadores al nivel 0, para todas las producciones recursivas."""
    splits = []
    seen   = set()
    for prod in rec_prods:
        ops = prod[1:-1]
        for pos in _find_op_positions(toks, ops):
            if pos not in seen:
                splits.append((pos, len(ops)))
                seen.add(pos)
    splits.sort(key=lambda x: x[0])
    return splits


def _build_assoc_tree(nt: str, rec_prods: list, toks: list, left_assoc: bool) -> 'ParseTree':
    """Construye un arbol de la cadena con asociacion izquierda o derecha.

    left_assoc=True  -> divide en el operador mas a la derecha -> (a op b) op c
    left_assoc=False -> divide en el operador mas a la izquierda -> a op (b op c)
    """
    splits = _collect_splits(rec_prods, toks)
    if not splits:
        return _leaf_tree(nt, rec_prods, toks)

    pos, olen = splits[-1] if left_assoc else splits[0]
    left_toks  = toks[:pos]
    op_nodes   = [ParseTree(_tok_label(toks[pos + j])) for j in range(olen)]
    right_toks = toks[pos + olen:]

    return ParseTree(nt, [
        _build_assoc_tree(nt, rec_prods, left_toks,  left_assoc),
        *op_nodes,
        _build_assoc_tree(nt, rec_prods, right_toks, left_assoc),
    ])


def _leaf_tree(nt: str, rec_prods: list, toks: list) -> 'ParseTree':
    """Nodo hoja: token unico, epsilon, o expresion entre parentesis."""
    if not toks:
        return ParseTree(nt, [ParseTree("e")])
    is_lparen = lambda t: t[0] == "LPAREN" or (len(t) > 1 and t[1] == "(")
    is_rparen = lambda t: t[0] == "RPAREN" or (len(t) > 1 and t[1] == ")")
    if len(toks) >= 2 and is_lparen(toks[0]) and is_rparen(toks[-1]):
        inner = _build_assoc_tree(nt, rec_prods, toks[1:-1], True)
        return ParseTree(nt, [ParseTree("("), inner, ParseTree(")")])
    return ParseTree(nt, [ParseTree(_tok_label(t)) for t in toks])


def build_trees_from_tokens(
        grammar: Grammar, nt: str, tokens: list
) -> Tuple[Optional['ParseTree'], Optional['ParseTree']]:
    """Construye dos arboles de derivacion de la cadena real: asociacion izquierda y derecha.

    Usa todos los operadores de todas las producciones E->E op E para encontrar
    puntos de division distintos. Retorna (arbol_izq, arbol_der) o (None, None).
    """
    non_eps   = [p for p in grammar.productions.get(nt, []) if p]
    rec_prods = [p for p in non_eps if p[0] == nt and p[-1] == nt and len(p) > 1]
    if not rec_prods:
        return None, None

    real_tokens = [t for t in tokens
                   if t[0] not in ("WS", "WHITESPACE", "NEWLINE", "$", "SEMI")
                   and (len(t) < 2 or t[1] != ";")]

    splits = _collect_splits(rec_prods, real_tokens)
    if len(splits) < 2 or splits[0][0] == splits[-1][0]:
        return None, None

    tree_left  = _build_assoc_tree(nt, rec_prods, real_tokens, True)
    tree_right = _build_assoc_tree(nt, rec_prods, real_tokens, False)
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
