"""
ambiguity.py  -  Deteccion de ambiguedad en gramaticas libres de contexto.

Teoria (diapositivas 19-20):
  Una gramatica es AMBIGUA si existe al menos una cadena que puede
  derivarse de MAS DE UNA forma, produciendo arboles distintos.

  Ejemplo ambiguo (diapositiva 20):
      E -> E + E | E * E | id
      "1 + 2 * 3" puede derivarse de dos formas diferentes:
        Arbol 1: (1 + 2) * 3   <- + tiene mayor precedencia
        Arbol 2: 1 + (2 * 3)   <- * tiene mayor precedencia

  Como eliminarla (diapositiva 21):
    Reescribir la gramatica con reglas de precedencia explicita:
      E -> E + T | T
      T -> T * F | F
      F -> (E) | id

  NOTA: Decidir si una CFG arbitraria es ambigua es un problema
  INDECIDIBLE en general. Este modulo detecta casos concretos:
    1. Prefijos comunes no factorizados (A -> a b | a c)
    2. NTs que producen la misma cadena por caminos distintos
    3. Producciones que se superponen con misma longitud
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


# ─────────────────────────────────────────────────────────────
# Deteccion de indicadores de ambiguedad
# ─────────────────────────────────────────────────────────────

class AmbiguityWarning:
    """Representa un caso de posible ambiguedad detectado."""
    def __init__(self, kind: str, nt: str, detail: str):
        self.kind   = kind    # tipo de ambiguedad
        self.nt     = nt      # no-terminal afectado
        self.detail = detail  # descripcion

    def __str__(self):
        return f"  [{self.kind}] {self.nt}: {self.detail}"


def detect_ambiguity(grammar: Grammar) -> list:
    """
    Detecta indicadores de ambiguedad en la gramatica.
    Devuelve lista de AmbiguityWarning (vacia = no se detecto ambiguedad).
    """
    warnings = []

    for nt, prods in grammar.productions.items():
        non_eps = [p for p in prods if p]

        # ── 1. Prefijos comunes ────────────────────────────────────
        # A -> a B | a C  => dos derivaciones comienzan igual
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

        # ── 2. Producciones identicas ──────────────────────────────
        seen_prods = set()
        for p in prods:
            key = tuple(p)
            if key in seen_prods:
                warnings.append(AmbiguityWarning(
                    "PRODUCCION_DUPLICADA", nt,
                    f"produccion '{' '.join(p) if p else 'epsilon'}' aparece mas de una vez"
                ))
            seen_prods.add(key)

        # ── 3. Recursividad en ambos lados (fuente clasica de ambiguedad) ──
        left_rec  = [p for p in non_eps if p[0]  == nt]
        right_rec = [p for p in non_eps if p[-1] == nt]
        if left_rec and right_rec:
            warnings.append(AmbiguityWarning(
                "REC_AMBOS_LADOS", nt,
                f"tiene recursividad izquierda Y derecha "
                f"-> gramatica casi seguramente ambigua "
                f"(ej: E->E+E produce arboles multiples para a+b+c)"
            ))

        # ── 4. Producciones epsilon multiples ─────────────────────
        eps_count = sum(1 for p in prods if not p)
        if eps_count > 1:
            warnings.append(AmbiguityWarning(
                "EPSILON_MULTIPLE", nt,
                f"tiene {eps_count} producciones epsilon"
            ))

    return warnings


def report_ambiguity(grammar: Grammar) -> str:
    """Genera un reporte legible de la deteccion de ambiguedad."""
    warnings = detect_ambiguity(grammar)
    lines = ["Analisis de Ambiguedad (diapositivas 19-20):"]
    if not warnings:
        lines.append("  Sin indicadores de ambiguedad detectados.")
    else:
        lines.append(f"  ADVERTENCIA: {len(warnings)} indicador(es) encontrado(s):")
        for w in warnings:
            lines.append(str(w))
        lines.append("")
        lines.append("  Para eliminar la ambiguedad (diapositiva 21):")
        lines.append("  -> Reescribir con jerarquia de precedencia explicita")
        lines.append("  -> Aplicar factorizacion (elimina prefijos comunes)")
        lines.append("  -> Eliminar recursividad en ambos lados")
    return "\n".join(lines)


def is_ambiguous(grammar: Grammar) -> bool:
    """True si se detectaron indicadores de ambiguedad."""
    return len(detect_ambiguity(grammar)) > 0
