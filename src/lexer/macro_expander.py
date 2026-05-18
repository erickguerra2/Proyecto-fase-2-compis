"""
Expande las macros del .yal y las sustituye en cada patrón.
"""
import re


def expand_macros(definitions: dict, rules_patterns: list) -> list:
    resolved = {}
    def resolve(name, seen=None):
        if name in resolved: return resolved[name]
        if seen is None: seen = set()
        if name in seen: raise ValueError(f"Referencia circular en definición: {name}")
        seen.add(name)
        expr = definitions[name]
        expr = _substitute(expr, definitions, seen, resolved)
        resolved[name] = expr
        return expr

    for name in definitions:
        resolve(name)

    expanded = []
    for pattern in rules_patterns:
        exp = _substitute(pattern, definitions, set(), resolved)
        expanded.append(exp)
    return expanded


def _substitute(expr: str, definitions: dict, seen: set, resolved: dict) -> str:
    result = []
    i = 0
    while i < len(expr):
        # intenta leer un identificador en la posición actual
        m = re.match(r'[A-Za-z_]\w*', expr[i:])
        if m:
            name = m.group(0)
            if name in definitions:
                sub = resolved.get(name)
                if sub is None:
                    sub = _substitute(definitions[name], definitions, seen | {name}, resolved)
                    resolved[name] = sub
                result.append(f"({sub})")
                i += len(name)
                continue
        result.append(expr[i])
        i += 1
    return "".join(result)


def normalize_charset(expr: str) -> str:
    return expr.strip()
