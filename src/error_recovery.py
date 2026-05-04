"""
error_recovery.py  -  Recuperacion de errores sintacticos.

Teoria (PDF pagina 1 - Recuperacion de errores):

  panic-mode:
    Descartar simbolos hasta encontrar un token de sincronizacion (; y {)
    Es el mas simple: cuando hay error, avanzar hasta encontrar un
    token "seguro" desde donde continuar el analisis.

  phrase-level:
    Reemplazar un prefijo de la entrada restante con una cadena que
    permite al parser continuar.
    Ejemplo: agregar o eliminar un ';' faltante.

  production-level:
    Producciones con una derivacion no deseada (manejadas en la gramatica).

  Global (minimo de edicion):
    Buscar un AST reduciendo las modificaciones, eliminaciones e
    inserciones de caracteres (algoritmo de distancia minima de edicion).
    Es el mas costoso computacionalmente.

Este modulo implementa panic-mode y phrase-level, que son los mas
usados en compiladores reales (ej: GCC usa una combinacion de ambos).
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Set


# ─────────────────────────────────────────────────────────────
# Tokens de sincronizacion (panic-mode)
# ─────────────────────────────────────────────────────────────

# Tokens "seguros" desde donde se puede reanudar el analisis
# Tomados directamente del PDF: "; y {"
DEFAULT_SYNC_TOKENS: Set[str] = {
    "SEMI", "SEMICOLON", ";",
    "LBRACE", "{",
    "RBRACE", "}",
    "RPAREN", ")",
    "EOF",
}


class SyntaxError_:
    """Representa un error sintactico detectado con su posicion y contexto."""
    def __init__(self, pos: int, token: tuple, expected: str,
                 recovery: str = "", skipped: list = None):
        self.pos      = pos
        self.token    = token
        self.expected = expected
        self.recovery = recovery
        self.skipped  = skipped or []

    def __str__(self):
        tok_str = f"'{self.token[1]}' ({self.token[0]})" if self.token else "EOF"
        msg = f"  Error en pos {self.pos}: token inesperado {tok_str}"
        if self.expected:
            msg += f"\n    Se esperaba: {self.expected}"
        if self.recovery:
            msg += f"\n    Recuperacion [{self.recovery}]"
        if self.skipped:
            skipped_str = ", ".join(f"'{l}'" for _, l in self.skipped[:5])
            msg += f"\n    Tokens descartados: {skipped_str}"
        return msg


# ─────────────────────────────────────────────────────────────
# Panic Mode (PDF: "Descartar Simbolos hasta token de sincronizacion")
# ─────────────────────────────────────────────────────────────

def panic_mode_recovery(
    tokens: List[Tuple[str, str]],
    error_pos: int,
    sync_tokens: Set[str] = None
) -> Tuple[int, List[Tuple[str, str]], SyntaxError_]:
    """
    Panic-mode: desde error_pos, descarta tokens hasta encontrar
    uno de sincronizacion.

    Devuelve:
      - nueva posicion (despues del token de sincronizacion)
      - tokens descartados
      - objeto SyntaxError_ con el diagnostico
    """
    if sync_tokens is None:
        sync_tokens = DEFAULT_SYNC_TOKENS

    skipped = []
    pos = error_pos

    while pos < len(tokens):
        tok_type, tok_lexeme = tokens[pos]
        if tok_type in sync_tokens or tok_lexeme in sync_tokens:
            break
        skipped.append(tokens[pos])
        pos += 1

    # Avanzar sobre el token de sincronizacion (consumirlo)
    if pos < len(tokens):
        pos += 1

    err = SyntaxError_(
        pos=error_pos,
        token=tokens[error_pos] if error_pos < len(tokens) else ("EOF", ""),
        expected="token de sincronizacion",
        recovery="panic-mode",
        skipped=skipped
    )
    return pos, skipped, err


# ─────────────────────────────────────────────────────────────
# Phrase-level (PDF: "Eliminar o Agregar ;")
# ─────────────────────────────────────────────────────────────

def phrase_level_recovery(
    tokens: List[Tuple[str, str]],
    error_pos: int,
    expected_type: str
) -> Tuple[List[Tuple[str, str]], Optional[SyntaxError_]]:
    """
    Phrase-level: intenta corregir el error insertando o eliminando
    el token esperado.

    Estrategias:
      1. INSERCION: si el token esperado podria ir aqui, lo inserta
      2. ELIMINACION: si el token actual es inesperado, lo elimina

    Devuelve la lista de tokens modificada y el error registrado.
    """
    insertable = {"SEMI", "SEMICOLON", ";", "RPAREN", ")", "RBRACE", "}"}
    new_tokens = list(tokens)
    err = None

    if expected_type in insertable and error_pos <= len(tokens):
        # Insertar el token que falta
        lexeme_map = {
            "SEMI": ";", "SEMICOLON": ";",
            "RPAREN": ")", "RBRACE": "}"
        }
        lexeme = lexeme_map.get(expected_type, expected_type)
        new_tokens.insert(error_pos, (expected_type, lexeme))
        err = SyntaxError_(
            pos=error_pos,
            token=tokens[error_pos] if error_pos < len(tokens) else ("EOF", ""),
            expected=expected_type,
            recovery=f"phrase-level: se inserto '{lexeme}' en posicion {error_pos}"
        )
    elif error_pos < len(tokens):
        # Eliminar el token inesperado
        bad_tok = new_tokens.pop(error_pos)
        err = SyntaxError_(
            pos=error_pos,
            token=bad_tok,
            expected=expected_type,
            recovery=f"phrase-level: se elimino '{bad_tok[1]}' en posicion {error_pos}",
            skipped=[bad_tok]
        )

    return new_tokens, err


# ─────────────────────────────────────────────────────────────
# Reporte
# ─────────────────────────────────────────────────────────────

def format_errors(errors: List[SyntaxError_]) -> str:
    """Formatea la lista de errores para mostrar al usuario."""
    if not errors:
        return "  Sin errores sintacticos."
    lines = [f"  {len(errors)} error(es) sintactico(s) encontrado(s):"]
    for i, e in enumerate(errors, 1):
        lines.append(f"\n  Error #{i}:")
        lines.append(str(e))
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Production-level (PDF: "producciones con derivacion no deseada")
# ─────────────────────────────────────────────────────────────

def production_level_report(grammar) -> str:
    """
    Production-level recovery:
    Identifica producciones que podrian generar derivaciones no deseadas
    (producciones epsilon sin control, producciones muy generales).
    En lugar de recuperarse en tiempo de ejecucion, este analisis
    sugiere correcciones a la gramatica misma antes de parsear.
    """
    lines = ["Analisis production-level (PDF p.1):"]
    issues = []

    for nt, prods in grammar.productions.items():
        # NT que solo tiene epsilon (siempre deriva vacio — puede ser error)
        if prods == [[]] or prods == []:
            issues.append(f"  {nt} -> solo epsilon: podria generar derivaciones no deseadas")

        # Producciones que aceptan cualquier cosa (muy permisivas)
        for p in prods:
            if len(p) == 1 and p[0] in grammar.nonterminals:
                # Produccion unitaria: puede causar ciclos o ambiguedad
                issues.append(f"  {nt} -> {p[0]}: produccion unitaria, verificar si es intencional")

    if issues:
        lines.append(f"  {len(issues)} advertencia(s):")
        lines.extend(issues)
    else:
        lines.append("  Sin producciones problematicas detectadas.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Global (PDF: "Buscar AST reduciendo modificaciones")
# ─────────────────────────────────────────────────────────────

def global_min_edit_distance(tokens: list, grammar_terminals: set) -> str:
    """
    Global error recovery (PDF p.1):
    Estima el minimo de ediciones (insercion, eliminacion, sustitucion)
    necesarias para que la entrada sea valida.

    Implementacion simplificada: cuenta tokens que NO son terminales
    de la gramatica como candidatos a eliminar/sustituir.
    Un compilador real (ej: GCC) usa algoritmos de distancia de edicion
    sobre el arbol de derivacion parcial.
    """
    visible = [(t, l) for t, l in tokens if t not in ("WS", "WHITESPACE", "NEWLINE")]
    unknown = [(t, l) for t, l in visible if t not in grammar_terminals]
    lines   = ["Analisis global (minimo de edicion) (PDF p.1):"]
    if not unknown:
        lines.append("  Todos los tokens son terminales validos de la gramatica.")
        lines.append("  Costo minimo de edicion estimado: 0")
    else:
        lines.append(f"  Tokens no reconocidos por la gramatica: {len(unknown)}")
        for t, l in unknown[:5]:
            lines.append(f"    '{l}' ({t}) -> candidato a eliminar o sustituir")
        lines.append(f"  Costo minimo de edicion estimado: >= {len(unknown)}")
    return "\n".join(lines)
