"""Lector de archivos .yapar con soporte de %token, IGNORE y producciones."""

from __future__ import annotations
import re
from typing import Dict, List, Set, Tuple
from src.cfg_grammar import Grammar


class YAParError(Exception):
    pass


def _strip_comments(text: str) -> str:
    """Elimina comentarios /* ... */ del texto."""
    return re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)


def parse_yapar(path: str) -> Tuple[Grammar, Set[str]]:
    """Lee un archivo .yapar y devuelve (Grammar, ignored_tokens)."""
    with open(path, encoding='utf-8') as fh:
        raw = fh.read()

    text = _strip_comments(raw)

    if '%%' not in text:
        raise YAParError(f"El archivo '{path}' no contiene '%%' para separar tokens de producciones.")

    token_section, _, prod_section = text.partition('%%')

    declared_tokens: Set[str] = set()
    ignored_tokens:  Set[str] = set()

    for line in token_section.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('%token'):
            names = line[len('%token'):].split()
            for name in names:
                declared_tokens.add(name)
        elif line.startswith('IGNORE'):
            names = line[len('IGNORE'):].split()
            for name in names:
                ignored_tokens.add(name)

    productions_raw = prod_section.strip()
    blocks = [b.strip() for b in productions_raw.split(';') if b.strip()]

    grammar = Grammar()
    first_nt = True

    for block in blocks:
        # El nombre de la produccion viene antes de ':'
        if ':' not in block:
            continue
        lhs, _, rhs_block = block.partition(':')
        lhs = lhs.strip()
        if not lhs:
            continue

        if first_nt:
            grammar.start = lhs
            first_nt = False

        grammar.nonterminals.add(lhs)
        if lhs not in grammar.productions:
            grammar.productions[lhs] = []

        for alt in rhs_block.split('|'):
            symbols = alt.strip().split()
            if not symbols or symbols in (['epsilon'], ['ε']):
                symbols = []
            grammar.productions[lhs].append(symbols)

    for prods in grammar.productions.values():
        for prod in prods:
            for sym in prod:
                if sym not in grammar.nonterminals:
                    grammar.terminals.add(sym)

    return grammar, ignored_tokens


def report_yapar(path: str) -> None:
    """Imprime un resumen del archivo .yapar cargado."""
    grammar, ignored = parse_yapar(path)

    print(f"\n{'='*64}")
    print(f"  YAPar: {path}")
    print(f"{'='*64}")
    print(f"  Simbolo inicial : {grammar.start}")
    print(f"  No-terminales   : {', '.join(sorted(grammar.nonterminals))}")
    print(f"  Terminales      : {', '.join(sorted(grammar.terminals))}")
    print(f"  Tokens ignorados: {', '.join(sorted(ignored)) if ignored else 'ninguno'}")
    print()
    for nt, prods in grammar.productions.items():
        for p in prods:
            body = ' '.join(p) if p else 'epsilon'
            print(f"  {nt:<24} -> {body}")
