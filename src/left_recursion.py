"""Eliminacion de recursividad izquierda directa en gramaticas libres de contexto."""

from __future__ import annotations
from copy import deepcopy
from src.cfg_grammar import Grammar


def has_left_recursion(grammar: Grammar) -> bool:
    """Devuelve True si algún no-terminal tiene recursividad izquierda directa."""
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if prod and prod[0] == nt:
                return True
    return False


def eliminate_left_recursion(grammar: Grammar) -> Grammar:
    """Elimina la recursividad izquierda directa de todos los no-terminales."""
    new_prods: dict = {}

    for nt in grammar.productions:
        prods = grammar.productions[nt]
        recursive = [p for p in prods if p and p[0] == nt]   # A → A α
        base      = [p for p in prods if not (p and p[0] == nt)]  # A → β

        if not recursive:
            new_prods[nt] = [list(p) for p in prods]
            continue

        nt_prime = nt + "'"
        while nt_prime in grammar.productions or nt_prime in new_prods:
            nt_prime += "'"

        new_base = []
        for b in base:
            new_base.append(list(b) + [nt_prime])
        if not new_base:
            new_base.append([nt_prime])
        new_prods[nt] = new_base

        new_rec = []
        for r in recursive:
            alpha = r[1:]
            new_rec.append(list(alpha) + [nt_prime])
        new_rec.append([])  # epsilon
        new_prods[nt_prime] = new_rec

    new_grammar = Grammar.from_dict(grammar.start, new_prods)
    return new_grammar
