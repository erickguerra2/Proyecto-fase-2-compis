"""Eliminacion de recursividad izquierda directa e indirecta (algoritmo Dragon Book)."""

from __future__ import annotations
from src.cfg_grammar import Grammar


def _left_reachable(grammar: Grammar) -> dict:
    """Cierre transitivo de 'puede aparecer como primer simbolo izquierdo'."""
    reachable = {nt: set() for nt in grammar.nonterminals}
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if prod and prod[0] in grammar.nonterminals:
                reachable[nt].add(prod[0])
    changed = True
    while changed:
        changed = False
        for nt in grammar.nonterminals:
            for mid in list(reachable[nt]):
                for target in reachable.get(mid, set()):
                    if target not in reachable[nt]:
                        reachable[nt].add(target)
                        changed = True
    return reachable


def has_left_recursion(grammar: Grammar) -> bool:
    """True si hay recursividad izquierda directa o indirecta."""
    reachable = _left_reachable(grammar)
    return any(nt in reachable[nt] for nt in grammar.nonterminals)


def _order_nonterminals(grammar: Grammar) -> list:
    """Orden BFS desde el simbolo inicial para el algoritmo de eliminacion."""
    from collections import deque
    ordered, visited = [], set()
    queue = deque([grammar.start])
    while queue:
        nt = queue.popleft()
        if nt in visited:
            continue
        visited.add(nt)
        ordered.append(nt)
        for prod in grammar.productions.get(nt, []):
            for sym in prod:
                if sym in grammar.nonterminals and sym not in visited:
                    queue.append(sym)
    for nt in grammar.productions:
        if nt not in visited:
            ordered.append(nt)
    return ordered


def _eliminate_direct(nt: str, prods: list, all_nts: set) -> tuple:
    """Elimina recursividad directa de un NT. Retorna (nuevas_prods, nt_prima, prods_prima)."""
    recursive = [p for p in prods if p and p[0] == nt]
    base      = [p for p in prods if not (p and p[0] == nt)]
    if not recursive:
        return prods, None, None

    nt_prime = nt + "'"
    while nt_prime in all_nts:
        nt_prime += "'"

    new_base = [list(b) + [nt_prime] for b in base] or [[nt_prime]]
    prime_prods = [list(r[1:]) + [nt_prime] for r in recursive] + [[]]
    return new_base, nt_prime, prime_prods


def eliminate_left_recursion(grammar: Grammar) -> Grammar:
    """Elimina recursividad izquierda directa e indirecta."""
    ordered  = _order_nonterminals(grammar)
    new_rules = {nt: [list(p) for p in prods]
                 for nt, prods in grammar.productions.items()}
    all_nts = set(new_rules)

    for i, ai in enumerate(ordered):
        # Sustituir Aj (j < i) en producciones de Ai
        for aj in ordered[:i]:
            expanded = []
            for prod in new_rules[ai]:
                if prod and prod[0] == aj:
                    gamma = prod[1:]
                    for aj_prod in new_rules[aj]:
                        expanded.append(list(aj_prod) + list(gamma))
                else:
                    expanded.append(prod)
            new_rules[ai] = expanded

        # Eliminar recursividad directa resultante
        new_base, nt_prime, prime_prods = _eliminate_direct(ai, new_rules[ai], all_nts)
        new_rules[ai] = new_base
        if nt_prime:
            new_rules[nt_prime] = prime_prods
            all_nts.add(nt_prime)
            ordered.append(nt_prime)

    return Grammar.from_dict(grammar.start, new_rules)


def report_left_recursion(grammar: Grammar) -> str:
    reachable = _left_reachable(grammar)
    direct, indirect = [], []

    for nt, prods in grammar.productions.items():
        for prod in prods:
            if prod and prod[0] == nt:
                direct.append(f"  {nt} -> {' '.join(prod)}")
                break

    for nt in grammar.nonterminals:
        if nt in reachable[nt] and not any(
            prod and prod[0] == nt
            for prod in grammar.productions.get(nt, [])
        ):
            indirect.append(f"  {nt} (via: {', '.join(reachable[nt] & {nt})})")

    if not direct and not indirect:
        return "Recursividad izquierda: ninguna"

    lines = []
    if direct:
        lines.append(f"Recursividad izquierda directa ({len(direct)}):")
        lines.extend(direct)
    if indirect:
        lines.append(f"Recursividad izquierda indirecta ({len(indirect)}):")
        lines.extend(indirect)
    return "\n".join(lines)
