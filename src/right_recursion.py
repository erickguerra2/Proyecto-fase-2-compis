"""
right_recursion.py  -  Deteccion y manejo de recursividad por la derecha.

Diferencia clave con la recursividad IZQUIERDA:
  - Izquierda: A -> A alpha | beta   (el NT aparece al INICIO de la produccion)
               PROBLEMA para parsers descendentes (top-down) -> cuelga en bucle
               SOLUCION: eliminar con transformacion A -> beta A', A' -> alpha A' | e

  - Derecha:   A -> alpha A | beta   (el NT aparece al FINAL de la produccion)
               CORRECTO para parsers descendentes (top-down) -> funciona bien
               PROBLEMA para parsers ascendentes (bottom-up LR) si es ambigua

Este modulo:
  1. Detecta recursividad derecha directa
  2. Puede CONVERTIRLA a forma iterativa equivalente usando NT auxiliares
     (util para ilustrar la simetria con la eliminacion izquierda)
  3. Puede detectar ambiguedad derivada de recursividad derecha

Ejemplo:
    A -> alpha A | beta    (derecha)
    se convierte en:
    A  -> beta A_r
    A_r -> alpha A_r | epsilon

Nota: en un parser descendente la recursividad derecha NO necesita
eliminarse. Este modulo existe para demostrar la teoria y para
cuando el objetivo sea generar CNF (Forma Normal de Chomsky).
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


# ─────────────────────────────────────────────
# Deteccion
# ─────────────────────────────────────────────

def has_right_recursion(grammar: Grammar) -> bool:
    """True si algun NT tiene recursividad directa por la derecha."""
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if prod and prod[-1] == nt:
                return True
    return False


def right_recursive_nts(grammar: Grammar) -> list:
    """Devuelve lista de NTs con recursividad directa por la derecha."""
    result = []
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if prod and prod[-1] == nt:
                result.append(nt)
                break
    return result


# ─────────────────────────────────────────────
# Eliminacion (opcional - solo para ilustrar teoria / CNF)
# ─────────────────────────────────────────────

def eliminate_right_recursion(grammar: Grammar) -> Grammar:
    """
    Elimina la recursividad directa POR LA DERECHA de todos los NTs.

    Transformacion simetrica a la eliminacion izquierda:

    ANTES:   A -> alpha A | beta
    DESPUES: A   -> beta A_r
             A_r -> alpha A_r | epsilon

    Donde A_r es el NT auxiliar (Right tail).

    ADVERTENCIA: esta transformacion no es necesaria para parsers
    descendentes. Se incluye solo para demostracion teorica y para
    preparar la gramatica para CNF.
    """
    new_prods: dict = {}

    for nt in grammar.productions:
        prods = grammar.productions[nt]
        recursive = [p for p in prods if p and p[-1] == nt]   # A -> alpha A
        base      = [p for p in prods if not (p and p[-1] == nt)]

        if not recursive:
            new_prods[nt] = [list(p) for p in prods]
            continue

        # Nombre auxiliar: A_r
        nt_r = nt + "_r"
        while nt_r in grammar.productions or nt_r in new_prods:
            nt_r += "r"

        # A -> beta A_r
        new_base = []
        for b in base:
            new_base.append(list(b) + [nt_r])
        if not new_base:
            new_base.append([nt_r])
        new_prods[nt] = new_base

        # A_r -> alpha A_r | epsilon
        new_rec = []
        for r in recursive:
            alpha = r[:-1]   # quita el ultimo simbolo (el propio A)
            new_rec.append(list(alpha) + [nt_r])
        new_rec.append([])   # epsilon
        new_prods[nt_r] = new_rec

    return Grammar.from_dict(grammar.start, new_prods)


# ─────────────────────────────────────────────
# Reporte
# ─────────────────────────────────────────────

def report_recursion(grammar: Grammar) -> str:
    """Genera un reporte legible del tipo de recursividad encontrada."""
    lines = ["Analisis de Recursividad:"]
    found_any = False
    for nt, prods in grammar.productions.items():
        left  = [p for p in prods if p and p[0]  == nt]
        right = [p for p in prods if p and p[-1] == nt]
        if left:
            found_any = True
            for p in left:
                lines.append(f"  [IZQUIERDA] {nt} -> {' '.join(p)}  <- PROBLEMA para top-down")
        if right:
            found_any = True
            for p in right:
                lines.append(f"  [DERECHA  ] {nt} -> {' '.join(p)}  <- OK para top-down")
    if not found_any:
        lines.append("  Sin recursividad directa detectada.")
    return "\n".join(lines)
