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


def _compute_unit_pairs(grammar) -> set:
    """Pares (A, B) donde A =>* B via producciones unitarias (cierre transitivo)."""
    pairs = {(nt, nt) for nt in grammar.nonterminals}
    changed = True
    while changed:
        changed = False
        new_pairs = set()
        for (a, b) in pairs:
            for prod in grammar.productions.get(b, []):
                if len(prod) == 1 and prod[0] in grammar.nonterminals:
                    c = prod[0]
                    if (a, c) not in pairs:
                        new_pairs.add((a, c))
                        changed = True
        pairs |= new_pairs
    return pairs


def has_unit_productions(grammar) -> bool:
    """True si existe alguna produccion unitaria A -> B (B no-terminal)."""
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if len(prod) == 1 and prod[0] in grammar.nonterminals:
                return True
    return False


def eliminate_unit_productions(grammar):
    """Elimina A -> B copiando las producciones no-unitarias de B a A."""
    from src.cfg_grammar import Grammar
    pairs = _compute_unit_pairs(grammar)
    new_rules = {nt: [] for nt in grammar.productions}

    for (a, b) in pairs:
        for prod in grammar.productions.get(b, []):
            if len(prod) == 1 and prod[0] in grammar.nonterminals:
                continue
            if prod not in new_rules[a]:
                new_rules[a].append(list(prod))

    for nt, prods in grammar.productions.items():
        if not new_rules[nt]:
            if [] in prods:
                new_rules[nt] = [[]]

    return Grammar.from_dict(grammar.start, new_rules)


def has_epsilon_only_nts(grammar) -> list:
    """Retorna lista de NTs cuya unica produccion es epsilon (excepto el simbolo inicial)."""
    result = []
    for nt, prods in grammar.productions.items():
        if nt == grammar.start:
            continue
        if prods and all(len(p) == 0 for p in prods):
            result.append(nt)
    return result


def inline_epsilon_only_nts(grammar):
    """Elimina NTs solo-epsilon sustituyendolos en cada produccion donde aparecen."""
    from src.cfg_grammar import Grammar
    eps_only = set(has_epsilon_only_nts(grammar))
    if not eps_only:
        return grammar

    new_rules = {}
    for nt, prods in grammar.productions.items():
        if nt in eps_only:
            continue
        new_prods = []
        for prod in prods:
            new_prod = [sym for sym in prod if sym not in eps_only]
            if new_prod not in new_prods:
                new_prods.append(new_prod)
        new_rules[nt] = new_prods if new_prods else [[]]

    return Grammar.from_dict(grammar.start, new_rules)


def fix_production_issues(grammar) -> tuple:
    """Corrige NTs solo-epsilon y producciones unitarias. Retorna (gramatica, cambios, aplicados)."""
    changes = []
    applied = set()

    eps_nts = has_epsilon_only_nts(grammar)
    if eps_nts:
        grammar = inline_epsilon_only_nts(grammar)
        for nt in eps_nts:
            changes.append(f"  [{nt}] NT solo-epsilon eliminado e inlineado donde se usaba")
        applied.add("epsilon_only_inlined")

    if has_unit_productions(grammar):
        unit_found = [
            f"{nt} -> {prod[0]}"
            for nt, prods in grammar.productions.items()
            for prod in prods
            if len(prod) == 1 and prod[0] in grammar.nonterminals
        ]
        grammar = eliminate_unit_productions(grammar)
        for u in unit_found:
            changes.append(f"  Produccion unitaria eliminada: {u}")
        applied.add("unit_productions_eliminated")

    return grammar, changes, applied


def report_fix_production_issues(grammar) -> tuple:
    """Detecta y corrige producciones unitarias y NTs solo-epsilon. Retorna (gramatica, reporte, aplicados)."""
    eps_nts   = has_epsilon_only_nts(grammar)
    has_units = has_unit_productions(grammar)

    if not eps_nts and not has_units:
        return grammar, "Producciones: sin problemas unitarios ni NTs solo-epsilon.", set()

    grammar, changes, applied = fix_production_issues(grammar)
    remaining_eps   = has_epsilon_only_nts(grammar)
    remaining_units = has_unit_productions(grammar)

    lines = ["Correccion de Producciones:"]
    lines.extend(changes)
    if remaining_eps or remaining_units:
        lines.append("  ADVERTENCIA: algunos problemas no pudieron resolverse automaticamente.")
    else:
        lines.append("  Producciones corregidas sin problemas residuales.")
    return grammar, "\n".join(lines), applied


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
