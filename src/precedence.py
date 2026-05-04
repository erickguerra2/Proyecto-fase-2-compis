"""
precedence.py  -  Precedencia y Asociatividad en gramaticas.

Teoria (diapositiva 8):

  PRECEDENCIA:
    Define que operadores "ligan mas fuerte".
    Ejemplo: 5 + 4 * 3 = 5 + (4 * 3)   <- * tiene mayor precedencia que +
             a | b*  = a | (b*)          <- * tiene mayor precedencia que |

  ASOCIATIVIDAD:
    Define como se agrupan operadores del mismo nivel cuando aparecen
    juntos.
    - Asociativa izquierda: 9 + 5 + 2 = (9 + 5) + 2
    - Asociativa derecha:   var1 = var2 = var3 = var1 = (var2 = var3)

  COMO SE IMPLEMENTA EN UNA GRAMATICA LIBRE DE CONTEXTO:
    Se codifica la precedencia en la jerarquia de no-terminales.
    Mayor profundidad = mayor precedencia.

    Ejemplo (diapositiva 21 - eliminacion de ambiguedad):
      ANTES (ambigua, sin precedencia):
        E -> E + E | E * E | id

      DESPUES (no ambigua, con precedencia):
        E -> E + T | T      <- + tiene MENOR precedencia (nivel alto)
        T -> T * F | F      <- * tiene MAYOR precedencia (nivel bajo)
        F -> (E) | id

    Asociatividad:
      - Izquierda: E -> E + T  (recursion izquierda)
      - Derecha:   E -> T + E  (recursion derecha)

Este modulo analiza la gramatica y reporta la precedencia/asociatividad
implícita que codifica.
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


COMMON_OPERATORS = {
    # Aritmeticos
    "PLUS": "+",  "OP_PLUS": "+",
    "MINUS": "-", "OP_MINUS": "-",
    "STAR": "*",  "OP_TIMES": "*",
    "SLASH": "/", "OP_DIV": "/",
    "MOD": "%",   "OP_MOD": "%",
    # Comparacion
    "OP_EQ": "==", "OP_NEQ": "!=",
    "OP_LT": "<",  "OP_LE": "<=",
    "OP_GT": ">",  "OP_GE": ">=",
    # Logicos
    "OP_AND": "&&", "OP_OR": "||", "OP_NOT": "!",
    # Asignacion
    "ASSIGN": "=", "OP_ASSIGN": "=",
}


def analyze_precedence(grammar: Grammar) -> str:
    """
    Analiza la gramatica y reporta la jerarquia de precedencia implícita.
    La profundidad del NT en el arbol de dependencias indica la precedencia:
    cuanto mas profundo, mayor precedencia.
    """
    lines = ["Analisis de Precedencia y Asociatividad (diapositiva 8):"]

    # Calcular profundidad de cada NT desde el simbolo inicial
    depth = _compute_depths(grammar)

    # Detectar operadores en cada NT y su asociatividad
    op_levels = []
    for nt, prods in grammar.productions.items():
        ops_here = set()
        assoc    = None
        for prod in prods:
            if not prod:
                continue
            # Buscar operadores terminales en la produccion
            for sym in prod:
                if sym in COMMON_OPERATORS:
                    ops_here.add(COMMON_OPERATORS[sym])
            # Detectar asociatividad
            if prod and prod[0] == nt:
                assoc = "IZQUIERDA"
            elif prod and prod[-1] == nt:
                assoc = "DERECHA"

        if ops_here:
            d = depth.get(nt, 0)
            op_levels.append((d, nt, sorted(ops_here), assoc))

    if not op_levels:
        lines.append("  No se detectaron operadores con precedencia explicita.")
        lines.append("  Tip: usar jerarquia de NTs para codificar precedencia")
        lines.append("       (mayor profundidad = mayor precedencia)")
        return "\n".join(lines)

    op_levels.sort(key=lambda x: x[0])
    lines.append(f"  {'Nivel':<8} {'NT':<20} {'Operadores':<20} Asociatividad")
    lines.append("  " + "-"*60)
    for d, nt, ops, assoc in op_levels:
        assoc_str = assoc or "ninguna"
        lines.append(f"  {d:<8} {nt:<20} {', '.join(ops):<20} {assoc_str}")

    lines.append("")
    lines.append("  Regla: mayor nivel numerico = mayor precedencia")
    lines.append("  Ejemplo de la diapositiva 8:")
    lines.append("    5 + 4*3 = 5 + (4*3)  porque * esta en nivel mas profundo que +")
    return "\n".join(lines)


def _compute_depths(grammar: Grammar) -> dict:
    """BFS desde el simbolo inicial para calcular profundidad de cada NT."""
    depth = {grammar.start: 0}
    queue = [grammar.start]
    while queue:
        current = queue.pop(0)
        d = depth[current]
        for prod in grammar.productions.get(current, []):
            for sym in prod:
                if sym in grammar.nonterminals and sym not in depth:
                    depth[sym] = d + 1
                    queue.append(sym)
    return depth
