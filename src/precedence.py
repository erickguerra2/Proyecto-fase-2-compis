"""Analisis de precedencia y asociatividad de operadores en la gramatica."""

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
    """Reporta la jerarquia de precedencia y asociatividad de operadores."""
    lines = ["Analisis de Precedencia y Asociatividad:"]

    depth = _compute_depths(grammar)

    op_levels = []
    for nt, prods in grammar.productions.items():
        ops_here = set()
        assoc    = None
        for prod in prods:
            if not prod:
                continue
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
        return "\n".join(lines)

    op_levels.sort(key=lambda x: x[0])
    lines.append(f"  {'Nivel':<8} {'NT':<20} {'Operadores':<20} Asociatividad")
    lines.append("  " + "-"*60)
    for d, nt, ops, assoc in op_levels:
        assoc_str = assoc or "ninguna"
        lines.append(f"  {d:<8} {nt:<20} {', '.join(ops):<20} {assoc_str}")

    lines.append("")
    lines.append("  Mayor nivel numerico = mayor precedencia")
    return "\n".join(lines)


def _compute_depths(grammar: Grammar) -> dict:
    """Calcula profundidad de cada NT desde el simbolo inicial (BFS)."""
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
