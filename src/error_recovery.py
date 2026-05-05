"""Recuperacion de errores sintacticos: panic-mode, phrase-level, production-level y global."""

from __future__ import annotations
from typing import List, Tuple, Optional, Set


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


def panic_mode_recovery(
    tokens: List[Tuple[str, str]],
    error_pos: int,
    sync_tokens: Set[str] = None
) -> Tuple[int, List[Tuple[str, str]], SyntaxError_]:
    """Descarta tokens desde error_pos hasta encontrar un token de sincronizacion."""
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


def phrase_level_recovery(
    tokens: List[Tuple[str, str]],
    error_pos: int,
    expected_type: str
) -> Tuple[List[Tuple[str, str]], Optional[SyntaxError_]]:
    """Intenta corregir el error insertando o eliminando el token esperado."""
    insertable = {"SEMI", "SEMICOLON", ";", "RPAREN", ")", "RBRACE", "}"}
    new_tokens = list(tokens)
    err = None

    if expected_type in insertable and error_pos <= len(tokens):
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
        bad_tok = new_tokens.pop(error_pos)
        err = SyntaxError_(
            pos=error_pos,
            token=bad_tok,
            expected=expected_type,
            recovery=f"phrase-level: se elimino '{bad_tok[1]}' en posicion {error_pos}",
            skipped=[bad_tok]
        )

    return new_tokens, err


def format_errors(errors: List[SyntaxError_]) -> str:
    """Formatea la lista de errores para mostrar al usuario."""
    if not errors:
        return "  Sin errores sintacticos."
    lines = [f"  {len(errors)} error(es) sintactico(s) encontrado(s):"]
    for i, e in enumerate(errors, 1):
        lines.append(f"\n  Error #{i}:")
        lines.append(str(e))
    return "\n".join(lines)


def production_level_report(grammar) -> str:
    """Identifica producciones que podrian generar derivaciones no deseadas."""
    lines = ["Analisis production-level:"]
    issues = []

    for nt, prods in grammar.productions.items():
        if prods == [[]] or prods == []:
            issues.append(f"  {nt} -> solo epsilon: podria generar derivaciones no deseadas")

        for p in prods:
            if len(p) == 1 and p[0] in grammar.nonterminals:
                issues.append(f"  {nt} -> {p[0]}: produccion unitaria, verificar si es intencional")

    if issues:
        lines.append(f"  {len(issues)} advertencia(s):")
        lines.extend(issues)
    else:
        lines.append("  Sin producciones problematicas detectadas.")
    return "\n".join(lines)


def global_min_edit_distance(tokens: list, grammar_terminals: set) -> str:
    """Estima el minimo de ediciones necesarias para que la entrada sea valida."""
    visible = [(t, l) for t, l in tokens if t not in ("WS", "WHITESPACE", "NEWLINE")]
    unknown = [(t, l) for t, l in visible if t not in grammar_terminals]
    lines   = ["Analisis global (minimo de edicion):"]
    if not unknown:
        lines.append("  Todos los tokens son terminales validos de la gramatica.")
        lines.append("  Costo minimo de edicion estimado: 0")
    else:
        lines.append(f"  Tokens no reconocidos por la gramatica: {len(unknown)}")
        for t, l in unknown[:5]:
            lines.append(f"    '{l}' ({t}) -> candidato a eliminar o sustituir")
        lines.append(f"  Costo minimo de edicion estimado: >= {len(unknown)}")
    return "\n".join(lines)
