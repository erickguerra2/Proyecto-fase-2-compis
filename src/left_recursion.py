"""
left_recursion.py  –  Eliminación de recursividad por la izquierda.

Teoría (diapositiva 22):
    Dada:   A  → A α  |  β
    Produce:
            A  → β A'
            A' → α A' | ε

Esto se aplica a TODAS las producciones del no-terminal A:
    Si A tiene varias producciones recursivas α1, α2, ... y
    varias bases β1, β2, ...

    A  → β1 A' | β2 A' | ...
    A' → α1 A' | α2 A' | ... | ε

El módulo también detecta si NO hay recursividad izquierda y
devuelve la gramática sin cambios en ese caso.
"""

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
    """
    Elimina la recursividad izquierda DIRECTA de todos los no-terminales.
    Devuelve una nueva gramática transformada.

    Ejemplo:
        E → E + T | E - T | T
    Se transforma en:
        E  → T E'
        E' → + T E' | - T E' | ε
    """
    new_prods: dict = {}

    for nt in grammar.productions:
        prods = grammar.productions[nt]
        recursive = [p for p in prods if p and p[0] == nt]   # A → A α
        base      = [p for p in prods if not (p and p[0] == nt)]  # A → β

        if not recursive:
            # Sin recursividad izquierda: copiar tal cual
            new_prods[nt] = [list(p) for p in prods]
            continue

        # Nombre del nuevo no-terminal auxiliar: E → E'
        nt_prime = nt + "'"
        # Asegurarse de que el nombre no exista ya
        while nt_prime in grammar.productions or nt_prime in new_prods:
            nt_prime += "'"

        # A  → β1 A' | β2 A' | ...
        new_base = []
        for b in base:
            new_base.append(list(b) + [nt_prime])
        if not new_base:
            # Si no hay base, algo raro — igual generamos una con sólo A'
            new_base.append([nt_prime])
        new_prods[nt] = new_base

        # A' → α1 A' | α2 A' | ... | ε
        new_rec = []
        for r in recursive:
            alpha = r[1:]          # quita el primer símbolo (el propio A)
            new_rec.append(list(alpha) + [nt_prime])
        new_rec.append([])         # ε
        new_prods[nt_prime] = new_rec

    # Construir nueva gramática respetando el símbolo inicial
    new_grammar = Grammar.from_dict(grammar.start, new_prods)
    return new_grammar
