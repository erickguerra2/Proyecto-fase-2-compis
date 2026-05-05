"""Lector de gramáticas libres de contexto desde archivos .grm."""

from __future__ import annotations
from typing import Dict, List, Set


class Grammar:
    """Gramática libre de contexto."""

    def __init__(self) -> None:
        self.productions: Dict[str, List[List[str]]] = {}
        self.start: str = ""
        self.nonterminals: Set[str] = set()
        self.terminals: Set[str] = set()

    @classmethod
    def from_file(cls, path: str) -> "Grammar":
        g = cls()
        first = True
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "->" not in line:
                    continue
                lhs, _, rhs_block = line.partition("->")
                lhs = lhs.strip()
                if not lhs:
                    continue
                if first:
                    g.start = lhs
                    first = False
                g.nonterminals.add(lhs)
                if lhs not in g.productions:
                    g.productions[lhs] = []
                for alt in rhs_block.split("|"):
                    symbols = alt.strip().split()
                    # producción vacía
                    if symbols in (["epsilon"], ["ε"], []):
                        symbols = []
                    g.productions[lhs].append(symbols)
        # Identificar terminales: todo símbolo que NO sea no-terminal
        for prods in g.productions.values():
            for prod in prods:
                for sym in prod:
                    if sym not in g.nonterminals:
                        g.terminals.add(sym)
        return g

    @classmethod
    def from_dict(cls, start: str,
                  rules: Dict[str, List[List[str]]]) -> "Grammar":
        g = cls()
        g.start = start
        g.productions = {k: list(v) for k, v in rules.items()}
        g.nonterminals = set(rules.keys())
        for prods in g.productions.values():
            for prod in prods:
                for sym in prod:
                    if sym not in g.nonterminals:
                        g.terminals.add(sym)
        return g

    def __str__(self) -> str:
        lines = [f"Start: {self.start}"]
        for nt, prods in self.productions.items():
            for p in prods:
                body = " ".join(p) if p else "ε"
                lines.append(f"  {nt} -> {body}")
        return "\n".join(lines)
