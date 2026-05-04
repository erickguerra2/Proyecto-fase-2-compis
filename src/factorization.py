"""
factorization.py  –  Factorización por la izquierda (Left Factoring).

Teoría (diapositiva 24-25):
    Dada:   A → a β1 | a β2
    Produce:
            A  → a A'
            A' → β1 | β2

Necesario para que el parser descendente pueda elegir la producción
correcta mirando un solo token (sin ambigüedad de prefijo).

Ejemplo del PDF (Factorización):
    INSTR → if EXPR then INSTR else INSTR
    INSTR → if EXPR then INSTR
    →
    INSTR  → if EXPR then INSTR INSTR'
    INSTR' → else INSTR | ε
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


def needs_factorization(grammar: Grammar) -> bool:
    """Detecta si algún NT tiene dos producciones con el mismo primer símbolo."""
    for nt, prods in grammar.productions.items():
        firsts = [p[0] for p in prods if p]
        if len(firsts) != len(set(firsts)):
            return True
    return False


def left_factor(grammar: Grammar) -> Grammar:
    """
    Aplica factorización por la izquierda hasta que no queden prefijos comunes.
    Devuelve una nueva gramática.
    """
    new_prods = {nt: [list(p) for p in prods]
                 for nt, prods in grammar.productions.items()}

    changed = True
    while changed:
        changed = False
        extra: dict = {}

        for nt in list(new_prods.keys()):
            prods = new_prods[nt]
            # Agrupar producciones por primer símbolo
            groups: dict[str, list] = {}
            eps_prods = []
            for p in prods:
                if not p:
                    eps_prods.append(p)
                else:
                    groups.setdefault(p[0], []).append(p)

            factored = list(eps_prods)
            for sym, group in groups.items():
                if len(group) == 1:
                    factored.append(group[0])
                    continue
                # Hay 2+ producciones con el mismo primer símbolo → factorizar
                changed = True
                nt_prime = nt + "'"
                while nt_prime in new_prods or nt_prime in extra:
                    nt_prime += "'"

                # A → sym A'
                factored.append([sym, nt_prime])

                # A' → resto1 | resto2 | ...
                tails = []
                for p in group:
                    tail = p[1:]   # quitar el prefijo común
                    tails.append(tail if tail else [])   # [] = ε
                extra[nt_prime] = tails

            new_prods[nt] = factored

        new_prods.update(extra)

    return Grammar.from_dict(grammar.start, new_prods)
