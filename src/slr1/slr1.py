"""Construccion de tabla SLR(1) y parser."""

from __future__ import annotations
from typing import List, Tuple, Optional
from src.cfg_grammar import Grammar
from src.first_follow import compute_first, compute_follow, EOF_SYM
from src.lr.lr0 import build_lr0, LR0State
from src.lr.lr_table import LRTable, LRAction, SHIFT, REDUCE, ACCEPT


def build_slr1_table(grammar: Grammar) -> Tuple[LRTable, List[LR0State], str]:
    """
    Construye la tabla SLR(1).
    Retorna (tabla, estados, simbolo_inicial_aumentado).
    """
    states, aug_start = build_lr0(grammar)
    follow = compute_follow(grammar, compute_first(grammar))
    table  = LRTable(states)

    for state in states:
        for item in state.items:
            sym = item.next_symbol

            if sym is not None and sym in grammar.terminals:
                target = state.transitions.get(sym)
                if target is not None:
                    table.set_action(state.id, sym, LRAction(SHIFT, state=target))

            elif sym is not None and sym == "$":
                target = state.transitions.get(sym)
                if target is not None:
                    table.set_action(state.id, sym, LRAction(SHIFT, state=target))

            elif item.is_complete:
                if item.nt == aug_start:
                    table.set_action(state.id, EOF_SYM, LRAction(ACCEPT))
                else:
                    for terminal in follow.get(item.nt, set()):
                        table.set_action(
                            state.id, terminal,
                            LRAction(REDUCE, nt=item.nt, prod=item.prod)
                        )

        for sym, target in state.transitions.items():
            if sym in grammar.nonterminals:
                table.set_goto(state.id, sym, target)

    return table, states, aug_start


class SLR1ParseError(Exception):
    pass


class SLR1Parser:
    """Parser SLR(1) con pila de estados."""

    def __init__(self, grammar: Grammar, tokens: List[Tuple]) -> None:
        self.grammar = grammar
        self.tokens  = [(t, l) for t, l in tokens
                        if t not in ("WS", "WHITESPACE", "NEWLINE")]
        self.table, self.states, self.aug_start = build_slr1_table(grammar)
        self.recovery_log: List[str] = []

    def is_slr1(self) -> bool:
        return not self.table.has_conflicts()

    def parse(self) -> bool:
        """Ejecuta el parsing SLR(1). Retorna True si acepta."""
        if not self.is_slr1():
            conflicts = "\n".join(str(c) for c in self.table.conflicts[:3])
            raise SLR1ParseError(
                f"La gramatica tiene {len(self.table.conflicts)} conflicto(s) SLR(1).\n"
                + conflicts
            )

        input_tokens = self.tokens + [(EOF_SYM, EOF_SYM)]
        pos   = 0
        stack = [0]
        self.recovery_log = []

        while True:
            state              = stack[-1]
            cur_type, cur_lex  = input_tokens[pos]

            action = (self.table.get_action(state, cur_type) or
                      self.table.get_action(state, cur_lex))

            if action is None:
                self.recovery_log.append(
                    f"  [RECOVERY] token '{cur_lex}' ({cur_type}) descartado"
                )
                pos += 1
                if pos >= len(input_tokens):
                    raise SLR1ParseError("Fin de entrada durante recuperacion.")
                continue

            if action.kind == SHIFT:
                stack.append(action.state)
                pos += 1

            elif action.kind == REDUCE:
                prod_len = len(action.prod)
                for _ in range(prod_len):
                    stack.pop()
                top   = stack[-1]
                goto  = self.table.get_goto(top, action.nt)
                if goto is None:
                    raise SLR1ParseError(
                        f"GOTO indefinido: estado {top}, NT '{action.nt}'"
                    )
                stack.append(goto)

            elif action.kind == ACCEPT:
                return True

    def recovery_report(self) -> str:
        if not self.recovery_log:
            return "  Sin acciones de recuperacion SLR(1)."
        lines = [f"  {len(self.recovery_log)} accion(es) de recuperacion:"]
        lines.extend(self.recovery_log)
        return "\n".join(lines)


def report_slr1(grammar: Grammar) -> str:
    table, _, _ = build_slr1_table(grammar)
    return table.report()
