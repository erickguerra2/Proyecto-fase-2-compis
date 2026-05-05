"""Deteccion de indicadores de ambiguedad en gramaticas libres de contexto."""

from __future__ import annotations
from src.cfg_grammar import Grammar


class AmbiguityWarning:
    """Representa un caso de posible ambiguedad detectado."""
    def __init__(self, kind: str, nt: str, detail: str):
        self.kind   = kind    # tipo de ambiguedad
        self.nt     = nt      # no-terminal afectado
        self.detail = detail  # descripcion

    def __str__(self):
        return f"  [{self.kind}] {self.nt}: {self.detail}"


def detect_ambiguity(grammar: Grammar) -> list:
    """Devuelve lista de AmbiguityWarning con indicadores de ambiguedad."""
    warnings = []

    for nt, prods in grammar.productions.items():
        non_eps = [p for p in prods if p]

        # Prefijos comunes: A -> a B | a C
        firsts = [p[0] for p in non_eps]
        seen = set()
        for sym in firsts:
            if sym in seen:
                warnings.append(AmbiguityWarning(
                    "PREFIJO_COMUN", nt,
                    f"multiples producciones comienzan con '{sym}' "
                    f"-> aplicar factorizacion"
                ))
                break
            seen.add(sym)

        # Producciones identicas
        seen_prods = set()
        for p in prods:
            key = tuple(p)
            if key in seen_prods:
                warnings.append(AmbiguityWarning(
                    "PRODUCCION_DUPLICADA", nt,
                    f"produccion '{' '.join(p) if p else 'epsilon'}' aparece mas de una vez"
                ))
            seen_prods.add(key)

        # Recursividad en ambos lados: fuente clasica de ambiguedad
        left_rec  = [p for p in non_eps if p[0]  == nt]
        right_rec = [p for p in non_eps if p[-1] == nt]
        if left_rec and right_rec:
            warnings.append(AmbiguityWarning(
                "REC_AMBOS_LADOS", nt,
                f"tiene recursividad izquierda Y derecha "
                f"-> gramatica casi seguramente ambigua "
                f"(ej: E->E+E produce arboles multiples para a+b+c)"
            ))

        # Producciones epsilon multiples
        eps_count = sum(1 for p in prods if not p)
        if eps_count > 1:
            warnings.append(AmbiguityWarning(
                "EPSILON_MULTIPLE", nt,
                f"tiene {eps_count} producciones epsilon"
            ))

    return warnings


def report_ambiguity(grammar: Grammar) -> str:
    """Genera un reporte de la deteccion de ambiguedad."""
    warnings = detect_ambiguity(grammar)
    lines = ["Analisis de Ambiguedad:"]
    if not warnings:
        lines.append("  Sin indicadores de ambiguedad detectados.")
    else:
        lines.append(f"  ADVERTENCIA: {len(warnings)} indicador(es) encontrado(s):")
        for w in warnings:
            lines.append(str(w))
    return "\n".join(lines)


def is_ambiguous(grammar: Grammar) -> bool:
    """True si se detectaron indicadores de ambiguedad."""
    return len(detect_ambiguity(grammar)) > 0
