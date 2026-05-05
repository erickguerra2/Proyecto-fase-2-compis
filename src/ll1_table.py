"""
ll1_table.py  -  Tabla de parsing LL(1) y parser predictivo.

Teoria:
  TABLA M[A, a]:
    Para cada produccion A -> alpha:
      1. Para cada 'a' en FIRST(alpha) - {epsilon}: M[A,a] = alpha
      2. Si epsilon in FIRST(alpha):
           Para cada 'b' en FOLLOW(A): M[A,b] = alpha

  La gramatica es LL(1) si ninguna celda tiene mas de una produccion.

  PARSER PREDICTIVO O(n):
    Pila: [S, $]  Entrada: w$
    - X == a (terminal): pop + avanzar
    - X es NT y M[X,a] existe: pop X, push produccion en inverso
    - M[X,a] vacio: RECUPERAR con FOLLOW

  NODOS EPSILON:
    A -> epsilon genera un hijo ParseNode('epsilon', lexeme='e')
    para que el arbol sea completo.

  RECUPERACION CON FOLLOW:
    Si M[A,a] vacio:
      'a' in FOLLOW(A) -> aplicar epsilon, NO consumir token
      'a' NOT in FOLLOW(A) -> descartar token
    Si terminal en pila no coincide -> pop (insercion ficticia)
"""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from src.cfg_grammar  import Grammar
from src.first_follow import compute_first, compute_follow, first_of_string, EPSILON, EOF_SYM
from src.parse_tree   import ParseNode

LLTable = Dict[Tuple[str, str], List[List[str]]]


class LL1Conflict:
    def __init__(self, nt: str, terminal: str, prods: list):
        self.nt = nt; self.terminal = terminal; self.prods = prods

    def __str__(self):
        alts = "  |  ".join(" ".join(p) if p else "epsilon" for p in self.prods)
        return f"  CONFLICTO M[{self.nt}, '{self.terminal}'] = {{ {alts} }}"


def build_ll1_table(grammar: Grammar) -> Tuple[LLTable, List[LL1Conflict]]:
    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    table: LLTable = {}
    conflicts: List[LL1Conflict] = []

    for nt, prods in grammar.productions.items():
        for prod in prods:
            alpha_first = first_of_string(prod, first) if prod else {EPSILON}

            for terminal in alpha_first - {EPSILON}:
                key = (nt, terminal)
                if key not in table: table[key] = []
                if prod not in table[key]: table[key].append(prod)

            if EPSILON in alpha_first:
                for terminal in follow.get(nt, set()):
                    key = (nt, terminal)
                    if key not in table: table[key] = []
                    if prod not in table[key]: table[key].append(prod)

    for (nt, terminal), prods in table.items():
        if len(prods) > 1:
            conflicts.append(LL1Conflict(nt, terminal, prods))

    return table, conflicts


def is_ll1(grammar: Grammar) -> bool:
    _, conflicts = build_ll1_table(grammar)
    return len(conflicts) == 0


def print_ll1_table(grammar: Grammar) -> None:
    table, conflicts = build_ll1_table(grammar)
    all_terms = sorted(set(t for (_, t) in table))
    nts = sorted(grammar.nonterminals)
    col_w = 24

    print(f"\n{'='*64}")
    print(f"  Tabla de Parsing LL(1)")
    print(f"  {'Sin conflictos - ES LL(1)' if not conflicts else str(len(conflicts)) + ' conflicto(s) - NO es LL(1)'}")
    print(f"{'='*64}")

    hdr = f"  {'NT':<20} | " + " | ".join(f"{t:<{col_w}}" for t in all_terms)
    print(hdr)
    print("  " + "-" * len(hdr))

    for nt in nts:
        cells = []
        for t in all_terms:
            prods = table.get((nt, t), [])
            if not prods:
                cells.append(" " * col_w)
            elif len(prods) == 1:
                body = " ".join(prods[0]) if prods[0] else "e"
                entry = f"{nt}->{body}"
                cells.append(f"{entry:<{col_w}}")
            else:
                cells.append(f"{'!!CONFLICTO!!':<{col_w}}")
        print(f"  {nt:<20} | " + " | ".join(cells))

    if conflicts:
        print(f"\n  Conflictos:")
        for c in conflicts: print(str(c))


def report_ll1(grammar: Grammar) -> str:
    _, conflicts = build_ll1_table(grammar)
    lines = ["Analisis LL(1):"]
    if not conflicts:
        lines.append("  La gramatica ES LL(1): no hay conflictos.")
        lines.append("  Parser predictivo O(n) sin backtracking puede usarse.")
    else:
        lines.append(f"  La gramatica NO es LL(1): {len(conflicts)} conflicto(s).")
        for c in conflicts: lines.append(str(c))
        lines.append("  Aplicar: eliminar recursividad izquierda + factorizacion.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Parser predictivo LL(1) — parser principal
# ─────────────────────────────────────────────────────────────

class LL1ParseError(Exception):
    pass


class LL1Parser:
    """
    Parser predictivo LL(1) basado en tabla M[NT, terminal].
    Es el parser PRINCIPAL del proyecto.

    - O(n): sin backtracking
    - Recuperacion de errores con FOLLOW sets
    - Nodos epsilon explicitos en el arbol
    - Si la gramatica NO es LL(1), lanza LL1ParseError
    """

    def __init__(self, grammar: Grammar,
                 tokens: List[Tuple[str, str]]) -> None:
        self.grammar   = grammar
        self.tokens    = [(t, l) for t, l in tokens
                          if t not in ("WS", "WHITESPACE", "NEWLINE")]
        self.table, self.conflicts = build_ll1_table(grammar)
        self.first     = compute_first(grammar)
        self.follow    = compute_follow(grammar, self.first)
        self.recovery_log: List[str] = []

    def is_ll1(self) -> bool:
        return len(self.conflicts) == 0

    def parse(self) -> ParseNode:
        """
        Algoritmo de parsing predictivo con pila explicita.

        Pila: [(simbolo, nodo_arbol), ...]
        Tope = ultimo elemento de la lista.

        Para cada paso:
          - Si tope es terminal y coincide con token: pop + avanzar
          - Si tope es NT: buscar M[NT, token] y expandir
          - Si M[NT, token] vacio: recuperar con FOLLOW
        """
        if not self.is_ll1():
            raise LL1ParseError(
                f"La gramatica tiene {len(self.conflicts)} conflicto(s) LL(1).\n"
                + "\n".join(str(c) for c in self.conflicts[:3])
            )

        input_tokens = self.tokens + [(EOF_SYM, EOF_SYM)]
        pos = 0
        self.recovery_log = []

        root = ParseNode(self.grammar.start)
        stack: List[Tuple[str, Optional[ParseNode]]] = [
            (EOF_SYM, None),
            (self.grammar.start, root),
        ]

        while stack:
            top_sym, top_node = stack[-1]
            cur_type, cur_lex = input_tokens[pos]

            # ── EXITO ─────────────────────────────────────────────
            if top_sym == EOF_SYM:
                if cur_type == EOF_SYM:
                    break
                else:
                    raise LL1ParseError(f"Entrada no consumida: {input_tokens[pos:]}")

            # ── Terminal en tope ───────────────────────────────────
            if top_sym in self.grammar.terminals:
                if self._match(top_sym, cur_type, cur_lex):
                    if top_node:
                        top_node.lexeme = cur_lex
                    stack.pop()
                    pos += 1
                else:
                    # Recuperacion: pop terminal de la pila
                    self.recovery_log.append(
                        f"  [RECOVERY/pop_terminal] '{top_sym}' descartado "
                        f"de pila, se encontro '{cur_lex}' ({cur_type})"
                    )
                    stack.pop()
                continue

            # ── NT en tope: consultar tabla ────────────────────────
            prod_list = (self.table.get((top_sym, cur_type)) or
                         self.table.get((top_sym, cur_lex)))

            if not prod_list:
                # ── Recuperacion con FOLLOW ────────────────────────
                follow_set = self.follow.get(top_sym, set())

                if cur_type in follow_set or cur_lex in follow_set:
                    # 'a' in FOLLOW(A): epsilon, no consumir token
                    self.recovery_log.append(
                        f"  [RECOVERY/skip_nt] {top_sym} -> epsilon "
                        f"('{cur_type}' in FOLLOW)"
                    )
                    if top_node:
                        top_node.children.append(ParseNode("epsilon", lexeme="e"))
                    stack.pop()
                else:
                    # 'a' NOT in FOLLOW(A): descartar token
                    self.recovery_log.append(
                        f"  [RECOVERY/skip_token] '{cur_lex}' ({cur_type}) "
                        f"descartado (no en FOLLOW({top_sym}))"
                    )
                    pos += 1
                    if pos >= len(input_tokens):
                        raise LL1ParseError("Fin de entrada durante recuperacion.")
                continue

            production = prod_list[0]  # LL(1): exactamente una entrada
            stack.pop()

            # ── Produccion epsilon ─────────────────────────────────
            if not production:
                if top_node:
                    top_node.children.append(ParseNode("epsilon", lexeme="e"))
                continue

            # ── Produccion normal: apilar hijos en orden inverso ───
            child_nodes = []
            for sym in production:
                child = ParseNode(sym)
                if top_node:
                    top_node.children.append(child)
                child_nodes.append((sym, child))

            for sym, node in reversed(child_nodes):
                stack.append((sym, node))

        return root

    def recovery_report(self) -> str:
        if not self.recovery_log:
            return "  Sin acciones de recuperacion LL(1)."
        lines = [f"  {len(self.recovery_log)} accion(es) de recuperacion (FOLLOW-based):"]
        lines.extend(self.recovery_log)
        return "\n".join(lines)

    @staticmethod
    def _match(expected: str, tok_type: str, tok_lexeme: str) -> bool:
        return expected == tok_type or expected == tok_lexeme
