from __future__ import annotations
from typing import Dict, List, Set


class Grammar:

    def __init__(self) -> None:
        self.productions: Dict[str, List[List[str]]] = {}
        self.start: str = ""
        self.nonterminals: Set[str] = set()
        self.terminals: Set[str] = set()

    @classmethod
    def from_dict(cls, start: str,
                  rules: Dict[str, List[List[str]]]) -> "Grammar":
        g = cls()
        g.start = start
        g.productions = {k: [list(p) for p in v] for k, v in rules.items()}
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
                body = " ".join(p) if p else "e"
                lines.append(f"  {nt} -> {body}")
        return "\n".join(lines)
