"""Deteccion y correccion de ambiguedad en gramaticas."""

from __future__ import annotations
from typing import Tuple, List, Set, Optional
from src.cfg_grammar import Grammar
from src.parse_tree  import ParseTree


class AmbiguityWarning:
    def __init__(self, kind: str, nt: str, detail: str):
        self.kind   = kind
        self.nt     = nt
        self.detail = detail

    def __str__(self):
        return f"  [{self.kind}] {self.nt}: {self.detail}"


# deteccion estructural

def detect_ambiguity(grammar: Grammar) -> list:
    """Busca patrones de ambiguedad estructural en la gramatica.
    Los prefijos comunes no se reportan aqui, esos van en detect_ll1_problems.
    """
    warnings = []

    for nt, prods in grammar.productions.items():
        non_eps = [p for p in prods if p]

        seen_prods: set = set()
        for p in prods:
            key = tuple(p)
            if key in seen_prods:
                warnings.append(AmbiguityWarning(
                    "PRODUCCION_DUPLICADA", nt,
                    f"produccion '{' '.join(p) if p else 'epsilon'}' aparece mas de una vez"
                    f" -> la misma cadena tiene dos derivaciones identicas"
                ))
            seen_prods.add(key)

        left_rec  = [p for p in non_eps if p[0]  == nt and len(p) > 1]
        right_rec = [p for p in non_eps if p[-1] == nt and len(p) > 1]
        if left_rec and right_rec:
            warnings.append(AmbiguityWarning(
                "REC_AMBOS_LADOS", nt,
                "recursividad izquierda Y derecha, patron E->E op E"
                " -> la misma cadena puede tener dos arboles distintos"
            ))

        eps_count = sum(1 for p in prods if not p)
        if eps_count > 1:
            warnings.append(AmbiguityWarning(
                "EPSILON_MULTIPLE", nt,
                f"{eps_count} producciones epsilon -> dos derivaciones de la cadena vacia"
            ))

    return warnings


def detect_ll1_problems(grammar: Grammar) -> list:
    """Prefijos comunes que impiden LL(1) pero no son ambiguedad como tal."""
    warnings = []
    for nt, prods in grammar.productions.items():
        non_eps = [p for p in prods if p]
        firsts: set = set()
        for p in non_eps:
            sym = p[0]
            if sym in firsts:
                warnings.append(AmbiguityWarning(
                    "PREFIJO_COMUN", nt,
                    f"multiples producciones comienzan con '{sym}'"
                    f" -> aplicar factorizacion para LL(1), no es ambiguedad"
                ))
                break
            firsts.add(sym)
    return warnings


def is_ambiguous(grammar: Grammar) -> bool:
    return len(detect_ambiguity(grammar)) > 0


# correccion

def fix_ambiguity(grammar: Grammar) -> Tuple[Grammar, List[str], Set[str]]:
    """Intenta corregir las ambiguedades que se pueden resolver automaticamente."""
    from src.ll1.left_recursion import has_left_recursion, eliminate_left_recursion

    warnings = detect_ambiguity(grammar)
    changes: List[str] = []
    applied: Set[str]  = set()
    kinds   = {w.kind for w in warnings}

    new_rules = {}
    for nt, prods in grammar.productions.items():
        seen: list = []
        for p in prods:
            if p not in seen:
                seen.append(p)
        if len(seen) < len(prods):
            changes.append(f"  [{nt}] producciones duplicadas eliminadas")
        eps     = [p for p in seen if not p]
        non_eps = [p for p in seen if p]
        if len(eps) > 1:
            changes.append(f"  [{nt}] epsilons duplicados reducidos a uno")
            eps = [[]]
        new_rules[nt] = non_eps + eps

    grammar = Grammar.from_dict(grammar.start, new_rules)

    if "REC_AMBOS_LADOS" in kinds and has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
        changes.append(
            "  Recursividad izquierda eliminada, patron E->E op E"
            " -> gramatica transformada a forma no recursiva izquierda"
        )
        applied.add("left_recursion_eliminated")

    return grammar, changes, applied


def _print_tree(tree: Optional[ParseTree], lines: list, indent: str = "  ") -> None:
    if tree is None:
        lines.append(indent + "no disponible")
        return
    for ln in tree.render().split("\n"):
        lines.append(indent + ln)


def full_chain_analysis(
        grammar:      Grammar,
        tokens:       list,
        initial_tree: Optional[ParseTree],
        parser_name:  str  = "parser",
        fix:          bool = True,
        pre_parse:    bool = False
) -> Tuple[Grammar, str, Set[str]]:
    """Analiza ambiguedad y muestra arboles de derivacion.
    pre_parse=True: analisis antes del parse. fix=True: corrige si es LL(1).
    """
    from src.parse_tree import build_trees_from_tokens, build_duplicate_trees

    lines: List[str] = []

    cadena_tokens = " ".join(
        t[1] if len(t) > 1 and t[1] and t[1] != t[0] else t[0]
        for t in tokens if t[0] not in ("WS", "WHITESPACE", "NEWLINE", "$")
    )

    if initial_tree is not None:
        cadena = initial_tree.yield_string() or cadena_tokens
        lines.append(f"Arbol de derivacion [{cadena}]:")
        _print_tree(initial_tree, lines)
    elif not pre_parse:
        lines.append(f"Cadena: \"{cadena_tokens}\"")
        lines.append("  El parser no pudo construir el arbol, hay conflictos en la tabla.")

    warnings = detect_ambiguity(grammar)
    if not warnings:
        if pre_parse:
            lines.append("Analisis de ambiguedad: sin indicadores en la gramatica.")
        else:
            lines.append("Analisis de ambiguedad: sin indicadores detectados.")
            lines.append("  Cada cadena tiene exactamente un arbol de derivacion.")
        return grammar, "\n".join(lines), set()

    lines.append(f"Analisis de ambiguedad: {len(warnings)} indicadores de ambiguedad:")
    for w in warnings:
        lines.append(str(w))

    done: set = set()
    for w in warnings:
        key = (w.kind, w.nt)
        if key in done:
            continue
        done.add(key)

        if w.kind == "REC_AMBOS_LADOS":
            tree_l, tree_r = build_trees_from_tokens(grammar, w.nt, tokens)
            if tree_l and tree_r and tree_l.yield_string() == tree_r.yield_string():
                cadena_w = tree_l.yield_string()
                lines.append(f"  [{w.nt}] La cadena \"{cadena_w}\" tiene dos arboles distintos:")
                lines.append("    Arbol 1, asociacion izquierda:")
                _print_tree(tree_l, lines, "      ")
                lines.append("    Arbol 2, asociacion derecha:")
                _print_tree(tree_r, lines, "      ")

        elif w.kind == "PRODUCCION_DUPLICADA":
            seen_p: set = set()
            for prod in grammar.productions.get(w.nt, []):
                k = tuple(prod)
                if k in seen_p:
                    witness, t1, t2 = build_duplicate_trees(grammar, w.nt, prod)
                    prod_str = " ".join(prod) if prod else "epsilon"
                    lines.append(f"  [{w.nt}] Produccion duplicada '{prod_str}',"
                                  f" cadena \"{witness}\" tiene dos derivaciones identicas:")
                    lines.append("    Arbol 1, primera aparicion:")
                    _print_tree(t1, lines, "      ")
                    lines.append("    Arbol 2, segunda aparicion:")
                    _print_tree(t2, lines, "      ")
                    break
                seen_p.add(k)

        elif w.kind == "EPSILON_MULTIPLE":
            lines.append(f"  [{w.nt}] Dos derivaciones de la cadena vacia:")
            lines.append(f"    Arbol 1: {w.nt} -> epsilon, primera produccion")
            lines.append(f"    Arbol 2: {w.nt} -> epsilon, segunda produccion")

    if not fix:
        lines.append("Correccion de ambiguedad: no aplica para parsers LR, SLR1 y LALR.")
        lines.append("  Para corregir la ambiguedad se requiere redisenar la gramatica")
        lines.append("  agregando reglas de precedencia y asociatividad explícitas.")
        return grammar, "\n".join(lines), set()

    grammar_fixed, changes, applied = fix_ambiguity(grammar)
    remaining = detect_ambiguity(grammar_fixed)

    lines.append("Correccion de ambiguedad:")
    if changes:
        for c in changes:
            lines.append(c)
    else:
        lines.append("  Sin transformaciones automaticas disponibles.")

    if remaining:
        lines.append(f"  ADVERTENCIA: {len(remaining)} indicadores sin resolver automaticamente:")
        for w in remaining:
            lines.append(str(w))
            if w.kind == "REC_AMBOS_LADOS":
                lines.append(f"    Motivo [{w.nt}]: la eliminacion de recursividad izquierda no fue"
                              f" suficiente. Se requiere rediseno manual con precedencia explícita.")
        lines.append("  Los arboles anteriores persisten: la gramatica sigue siendo ambigua.")
        return grammar_fixed, "\n".join(lines), applied

    from src.ll1.ll1_table import build_ll1_table
    _, ll1_conflicts = build_ll1_table(grammar_fixed)
    if ll1_conflicts:
        lines.append(f"  ADVERTENCIA: la transformacion automatica no es suficiente.")
        lines.append(f"  La gramatica transformada tiene {len(ll1_conflicts)} conflicto(s) LL(1).")
        lines.append(f"  El patron 'E -> E op E' requiere estratificacion manual por precedencia.")
        lines.append(f"  Gramatica transformada (con conflictos pendientes):")
        for nt, prods in grammar_fixed.productions.items():
            alts = " | ".join(" ".join(p) if p else "epsilon" for p in prods)
            lines.append(f"    {nt} -> {alts}")
        return grammar_fixed, "\n".join(lines), applied

    lines.append("  Gramatica sin indicadores de ambiguedad tras las correcciones.")
    lines.append("  La cadena produce exactamente un arbol de derivacion.")
    return grammar_fixed, "\n".join(lines), applied
