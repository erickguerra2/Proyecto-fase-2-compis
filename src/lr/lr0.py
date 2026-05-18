"""Construccion del automata LR(0): items, closure, goto y coleccion canonica."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
from src.cfg_grammar import Grammar

AUGMENT_SUFFIX = "'"


@dataclass(frozen=True)
class LR0Item:
    """Item LR(0): produccion con punto marcando la posicion del parser."""
    nt:   str
    prod: Tuple[str, ...]
    dot:  int

    @property
    def next_symbol(self) -> Optional[str]:
        """Simbolo inmediatamente despues del punto. None si el punto esta al final."""
        return self.prod[self.dot] if self.dot < len(self.prod) else None

    @property
    def is_complete(self) -> bool:
        return self.dot >= len(self.prod)

    def advance(self) -> "LR0Item":
        return LR0Item(self.nt, self.prod, self.dot + 1)

    def __str__(self) -> str:
        symbols = list(self.prod)
        symbols.insert(self.dot, "•")
        body = " ".join(symbols) if symbols else "•"
        return f"{self.nt} -> {body}"


@dataclass
class LR0State:
    """Estado del automata LR(0): conjunto de items con sus transiciones."""
    id:          int
    items:       frozenset
    transitions: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = [f"Estado {self.id}:"]
        for item in sorted(self.items, key=str):
            lines.append(f"  {item}")
        return "\n".join(lines)


def augment_grammar(grammar: Grammar) -> Tuple[Grammar, str]:
    """Agrega produccion S' -> S para el simbolo inicial aumentado."""
    new_start = grammar.start + AUGMENT_SUFFIX
    while new_start in grammar.nonterminals:
        new_start += AUGMENT_SUFFIX

    new_rules = {new_start: [[grammar.start]]}
    for nt, prods in grammar.productions.items():
        new_rules[nt] = [list(p) for p in prods]

    return Grammar.from_dict(new_start, new_rules), new_start


def closure(items: Set[LR0Item], grammar: Grammar) -> frozenset:
    """Calcula el closure de un conjunto de items LR(0)."""
    result = set(items)
    changed = True
    while changed:
        changed = False
        for item in list(result):
            sym = item.next_symbol
            if sym and sym in grammar.nonterminals:
                for prod in grammar.productions.get(sym, []):
                    new_item = LR0Item(sym, tuple(prod), 0)
                    if new_item not in result:
                        result.add(new_item)
                        changed = True
    return frozenset(result)


def goto(items: frozenset, symbol: str, grammar: Grammar) -> frozenset:
    """Calcula GOTO(items, symbol): items con el punto avanzado sobre symbol."""
    moved = {item.advance() for item in items
             if item.next_symbol == symbol}
    return closure(moved, grammar) if moved else frozenset()


def build_lr0(grammar: Grammar) -> Tuple[List[LR0State], str]:
    """
    Construye la coleccion canonica de estados LR(0).
    Retorna (estados, simbolo_inicial_aumentado).
    """
    aug_grammar, aug_start = augment_grammar(grammar)

    start_item  = LR0Item(aug_start, tuple(aug_grammar.productions[aug_start][0]), 0)
    start_items = closure({start_item}, aug_grammar)

    states:    List[LR0State]         = []
    seen:      Dict[frozenset, int]   = {}
    queue:     List[frozenset]        = [start_items]

    seen[start_items] = 0
    states.append(LR0State(id=0, items=start_items))

    while queue:
        current_items = queue.pop(0)
        current_id    = seen[current_items]

        symbols = {item.next_symbol for item in current_items
                   if item.next_symbol is not None}

        for sym in symbols:
            next_items = goto(current_items, sym, aug_grammar)
            if not next_items:
                continue
            if next_items not in seen:
                new_id = len(states)
                seen[next_items] = new_id
                new_state = LR0State(id=new_id, items=next_items)
                states.append(new_state)
                queue.append(next_items)
            states[current_id].transitions[sym] = seen[next_items]

    return states, aug_start


def report_lr0(states: List[LR0State]) -> str:
    """Reporte textual del automata LR(0)."""
    lines = [f"Automata LR(0): {len(states)} estado(s)"]
    for state in states:
        lines.append(str(state))
        for sym, target in sorted(state.transitions.items()):
            lines.append(f"    GOTO({sym}) -> Estado {target}")
    return "\n".join(lines)
