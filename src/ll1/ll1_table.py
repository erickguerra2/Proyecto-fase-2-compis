"""Tabla LL(1) y parser predictivo."""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from src.cfg_grammar  import Grammar
from src.first_follow import compute_first, compute_follow, first_of_string, EPSILON, EOF_SYM
from src.error_recovery import panic_mode_recovery, phrase_level_recovery, SyntaxError_, format_errors
from src.parse_tree import ParseTree

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


def print_ll1_table(grammar: Grammar) -> None:
    table, conflicts = build_ll1_table(grammar)
    all_terms = sorted(set(t for (_, t) in table))
    nts = sorted(grammar.nonterminals)
    col_w = 24

    print(f"\n{'='*64}")
    print(f"  Tabla de Parsing LL(1)")
    print(f"  {'Sin conflictos - ES LL(1)' if not conflicts else str(len(conflicts)) + ' conflictos - NO es LL(1)'}")
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

class LL1ParseError(Exception):
    pass


class LL1Parser:
    """Parser predictivo LL(1)."""

    def __init__(self, grammar: Grammar,
                 tokens: List[Tuple]) -> None:
        self.grammar   = grammar
        self.tokens    = [tok for tok in tokens
                          if tok[0] not in ("WS", "WHITESPACE", "NEWLINE")]
        self.table, self.conflicts = build_ll1_table(grammar)
        self.first     = compute_first(grammar)
        self.follow    = compute_follow(grammar, self.first)
        self.recovery_log: List[SyntaxError_] = []
        self.parse_tree = None

    def is_ll1(self) -> bool:
        return len(self.conflicts) == 0

    def parse(self) -> bool:
        """Parsing con pila explicita. Retorna True si acepta."""
        if not self.is_ll1():
            raise LL1ParseError(
                f"La gramatica tiene {len(self.conflicts)} conflictos LL(1).\n"
                + "\n".join(str(c) for c in self.conflicts[:3])
            )

        input_tokens = self.tokens + [(EOF_SYM, EOF_SYM, None, None)]
        pos = 0
        self.recovery_log = []

        stack: List[str] = [EOF_SYM, self.grammar.start]

        while stack:
            top_sym = stack[-1]
            tok      = input_tokens[pos]
            cur_type, cur_lex = tok[0], tok[1]
            cur_line, cur_col = tok[2], tok[3]
            pos_str = f" [linea {cur_line}, col {cur_col}]" if cur_line is not None else ""

            if top_sym == EOF_SYM:
                if cur_type == EOF_SYM:
                    break
                else:
                    raise LL1ParseError(
                        f"Entrada no consumida: token inesperado '{cur_lex}' ({cur_type}){pos_str}"
                    )

            if top_sym in self.grammar.terminals:
                if self._match(top_sym, cur_type, cur_lex):
                    stack.pop()
                    pos += 1
                else:
                    before = len(input_tokens)
                    new_tokens, err = phrase_level_recovery(input_tokens, pos, top_sym)
                    if err:
                        self.recovery_log.append(err)
                        input_tokens = new_tokens
                        if len(new_tokens) > before:
                            pass
                        else:
                            stack.pop()
                    else:
                        stack.pop()
                continue

            prod_list = (self.table.get((top_sym, cur_type)) or
                         self.table.get((top_sym, cur_lex)))

            if not prod_list:
                follow_set = self.follow.get(top_sym, set())
                if cur_type in follow_set or cur_lex in follow_set:
                    err = SyntaxError_(
                        pos=pos, token=tok,
                        expected=f"produccion para {top_sym}",
                        recovery=f"phrase-level: epsilon ('{cur_type}' en FOLLOW de {top_sym})"
                    )
                    self.recovery_log.append(err)
                    stack.pop()
                else:
                    new_pos, _, err = panic_mode_recovery(input_tokens, pos)
                    self.recovery_log.append(err)
                    pos = new_pos
                    if pos >= len(input_tokens):
                        raise LL1ParseError("Fin de entrada durante recuperacion.")
                continue

            production = prod_list[0]
            stack.pop()
            if not production:
                continue
            for sym in reversed(production):
                stack.append(sym)

        self.parse_tree = self._build_parse_tree(input_tokens)
        return True

    def _build_parse_tree(self, input_tokens: list) -> ParseTree:
        """Arma el arbol de derivacion de forma top-down usando la tabla."""
        pos = [0]

        def expand(symbol: str) -> ParseTree:
            if symbol == EOF_SYM:
                return ParseTree(symbol)

            if symbol in self.grammar.terminals or symbol not in self.grammar.productions:
                tok = input_tokens[pos[0]] if pos[0] < len(input_tokens) else (EOF_SYM, EOF_SYM, None, None)
                if self._match(symbol, tok[0], tok[1]):
                    label = tok[1] if tok[1] and tok[1] != tok[0] else symbol
                    pos[0] += 1
                    return ParseTree(label)
                return ParseTree(symbol)

            tok = input_tokens[pos[0]] if pos[0] < len(input_tokens) else (EOF_SYM, EOF_SYM, None, None)
            prod_list = self.table.get((symbol, tok[0])) or self.table.get((symbol, tok[1]))

            if not prod_list:
                return ParseTree(symbol, [ParseTree("e")])

            prod = prod_list[0]
            if not prod:
                return ParseTree(symbol, [ParseTree("e")])

            children = [expand(s) for s in prod]
            return ParseTree(symbol, children)

        return expand(self.grammar.start)

    def recovery_report(self) -> str:
        if not self.recovery_log:
            return "  Sin acciones de recuperacion LL(1)."
        return format_errors(self.recovery_log)

    @staticmethod
    def _match(expected: str, tok_type: str, tok_lexeme: str) -> bool:
        return expected == tok_type or expected == tok_lexeme
