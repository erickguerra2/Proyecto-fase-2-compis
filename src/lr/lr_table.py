"""Tabla ACTION/GOTO compartida por SLR(1) y LALR."""

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
from src.lr.lr0 import LR0State


SHIFT  = "shift"
REDUCE = "reduce"
ACCEPT = "accept"


class LRAction:
    """Entrada en la tabla de accion."""
    def __init__(self, kind: str,
                 state: Optional[int] = None,
                 nt: Optional[str] = None,
                 prod: Optional[Tuple] = None):
        self.kind  = kind
        self.state = state  # para shift
        self.nt    = nt     # para reduce
        self.prod  = prod   # para reduce

    def __str__(self) -> str:
        if self.kind == SHIFT:
            return f"s{self.state}"
        if self.kind == REDUCE:
            body = " ".join(self.prod) if self.prod else "eps"
            return f"r({self.nt}->{body})"
        return "acc"

    def __eq__(self, other) -> bool:
        return (isinstance(other, LRAction) and
                self.kind == other.kind and
                self.state == other.state and
                self.nt == other.nt and
                self.prod == other.prod)


class LRConflict:
    """Conflicto detectado en la tabla LR."""
    def __init__(self, state: int, symbol: str,
                 existing: LRAction, incoming: LRAction):
        self.state    = state
        self.symbol   = symbol
        self.existing = existing
        self.incoming = incoming

    @property
    def kind(self) -> str:
        kinds = {self.existing.kind, self.incoming.kind}
        if SHIFT in kinds and REDUCE in kinds:
            return "shift-reduce"
        return "reduce-reduce"

    def __str__(self) -> str:
        if self.kind == "reduce-reduce":
            return (f"  [reduce-reduce] Estado {self.state}, simbolo '{self.symbol}': "
                    f"{self.existing} vs {self.incoming}"
                    f" -> conflicto reduce-reduce, la gramatica es ambigua")
        return (f"  [shift-reduce] Estado {self.state}, simbolo '{self.symbol}': "
                f"{self.existing} vs {self.incoming}"
                f" -> conflicto shift-reduce, no parseable por este tipo de parser")


class LRTable:
    """Tabla action/goto para parsers LR."""

    def __init__(self, states: List[LR0State]):
        self.n_states  = len(states)
        self.action:   Dict[Tuple[int, str], LRAction] = {}
        self.goto_t:   Dict[Tuple[int, str], int]      = {}
        self.conflicts: List[LRConflict]               = []

    def set_action(self, state: int, symbol: str, action: LRAction) -> None:
        key = (state, symbol)
        if key in self.action and self.action[key] != action:
            existing = self.action[key]
            self.conflicts.append(LRConflict(state, symbol, existing, action))
                # en shift-reduce gana el shift
            kinds = {existing.kind, action.kind}
            if SHIFT in kinds and REDUCE in kinds and action.kind == SHIFT:
                self.action[key] = action
        else:
            self.action[key] = action

    def set_goto(self, state: int, nt: str, target: int) -> None:
        self.goto_t[(state, nt)] = target

    def get_action(self, state: int, symbol: str) -> Optional[LRAction]:
        return self.action.get((state, symbol))

    def get_goto(self, state: int, nt: str) -> Optional[int]:
        return self.goto_t.get((state, nt))

    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def has_reduce_reduce_conflicts(self) -> bool:
        return any(c.kind == "reduce-reduce" for c in self.conflicts)

    def report(self) -> str:
        if not self.conflicts:
            return "Tabla LR: sin conflictos."
        sr = [c for c in self.conflicts if c.kind == "shift-reduce"]
        rr = [c for c in self.conflicts if c.kind == "reduce-reduce"]
        lines = [f"Tabla LR: {len(self.conflicts)} conflictos:"]
        if rr:
            lines.append(f"  {len(rr)} reduce-reduce: la gramatica es ambigua, dos derivaciones para la misma cadena")
        if sr:
            lines.append(f"  {len(sr)} shift-reduce: no parseable por este parser sin resolver el conflicto")
        for c in self.conflicts:
            lines.append(str(c))
        return "\n".join(lines)

    def print_table(self, terminals: list, nonterminals: list) -> None:
        terms = sorted(terminals)
        nts   = sorted(nonterminals)
        col_w = 18

        print(f"\n{'='*60}")
        header = f"  {'Estado':<8} | " + " | ".join(f"{t:<{col_w}}" for t in terms)
        if nts:
            header += " || " + " | ".join(f"{nt:<{col_w}}" for nt in nts)
        print(header)
        print("  " + "-" * len(header))

        for s in range(self.n_states):
            row = f"  {s:<8} | "
            row += " | ".join(
                f"{str(self.action.get((s, t), '')):<{col_w}}" for t in terms
            )
            if nts:
                row += " || " + " | ".join(
                    f"{str(self.goto_t.get((s, nt), '')):<{col_w}}" for nt in nts
                )
            print(row)
        print()
