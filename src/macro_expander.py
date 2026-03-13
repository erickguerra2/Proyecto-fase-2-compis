"""
Expande las macros del .yal y las sustituye en cada patrón.
"""
import re


def expand_macros(definitions: dict, rules_patterns: list) -> list:
    # resuelve cada definición antes de usarla en los patrones
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

    # aplica las definiciones resueltas a cada patrón
    expanded = []
    for pattern in rules_patterns:
        exp = _substitute(pattern, definitions, set(), resolved)
        expanded.append(exp)
    return expanded


def _substitute(expr: str, definitions: dict, seen: set, resolved: dict) -> str:
    # busca identificadores que coincidan con alguna definición conocida
    result = []
    i = 0
    while i < len(expr):
        # intenta leer un identificador en la posición actual
        m = re.match(r'[A-Za-z_]\w*', expr[i:])
        if m:
            name = m.group(0)
            if name in definitions:
                # reemplaza el nombre por su definición entre paréntesis
                sub = resolved.get(name)
                if sub is None:
                    # todavía no estaba resuelta, se resuelve ahora
                    sub = _substitute(definitions[name], definitions, seen | {name}, resolved)
                    resolved[name] = sub
                result.append(f"({sub})")
                i += len(name)
                continue
        result.append(expr[i])
        i += 1
    return "".join(result)


def normalize_charset(expr: str) -> str:
    # limpia el charset antes de pasarlo al regex_parser
    return expr.strip()
