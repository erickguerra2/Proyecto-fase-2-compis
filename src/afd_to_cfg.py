"""Conversion de AFD (generado por el lexer) a Gramatica Libre de Contexto."""

from __future__ import annotations
from src.cfg_grammar import Grammar


def afd_to_cfg(transitions: dict, accept: dict,
               start_state: int = 0,
               token_name: str = "LEXER") -> Grammar:
    """Convierte un AFD (TRANSITIONS/ACCEPT del lexer) a una CFG equivalente."""
    states = set()
    states.add(start_state)
    for src, chars in transitions.items():
        states.add(src)
        for dst in chars.values():
            states.add(dst)

    def nt(state: int) -> str:
        return f"S{state}"

    prods: dict = {}

    for s in states:
        prods[nt(s)] = []

    for src, chars in sorted(transitions.items()):
        for char, dst in sorted(chars.items()):
            safe_char = _safe_terminal(char)
            production = [safe_char, nt(dst)]
            if production not in prods[nt(src)]:
                prods[nt(src)].append(production)

    for state in accept:
        if [] not in prods[nt(state)]:
            prods[nt(state)].append([])

    prods = {k: v for k, v in prods.items() if v}

    return Grammar.from_dict(nt(start_state), prods)


def _safe_terminal(char: str) -> str:
    """Convierte un caracter a un nombre de terminal legible."""
    special = {
        ' ': 'SPACE', '\t': 'TAB', '\n': 'NEWLINE',
        '+': 'PLUS',  '-': 'MINUS', '*': 'STAR', '/': 'SLASH',
        '(': 'LPAREN','(': 'LPAREN',')': 'RPAREN',
        '=': 'ASSIGN',';': 'SEMI',  ',': 'COMMA',
        '<': 'LT',    '>': 'GT',    '!': 'NOT',
        '&': 'AND',   '|': 'OR',    '^': 'XOR',
        '{': 'LBRACE','}': 'RBRACE','[': 'LBRACK',']': 'RBRACK',
        '.': 'DOT',   ':': 'COLON', '?': 'QMARK', '@': 'AT',
        '"': 'DQUOTE',"'": 'SQUOTE','\\': 'BACKSLASH',
        '_': 'UNDERSCORE', '#': 'HASH', '%': 'PERCENT',
    }
    if char in special:
        return special[char]
    if char.isalnum():
        return f"'{char}'"
    return f"CHAR_{ord(char)}"


def print_afd_cfg_conversion(transitions: dict, accept: dict,
                              start_state: int = 0) -> Grammar:
    """
    Muestra el proceso de conversion AFD -> CFG y devuelve la gramatica.
    """
    grammar = afd_to_cfg(transitions, accept, start_state)

    states  = set([start_state])
    for src, chars in transitions.items():
        states.add(src)
        for dst in chars.values():
            states.add(dst)

    print(f"\n{'='*64}")
    print("  Conversion AFD -> CFG")
    print(f"{'='*64}")
    print(f"  AFD:")
    print(f"    Estados       : {sorted(states)}")
    print(f"    Estado inicial: {start_state}")
    print(f"    Aceptacion    : {dict(sorted(accept.items()))}")
    print()
    print(f"  CFG resultante:")
    print(f"    Simbolo inicial: {grammar.start}")
    print(f"    No-terminales : {', '.join(sorted(grammar.nonterminals))}")
    print()
    for nt, prods in sorted(grammar.productions.items()):
        for p in prods:
            body = " ".join(p) if p else "ε"
            print(f"    {nt:<10} -> {body}")

    return grammar


def load_afd_from_lexer(lexer_mod) -> tuple:
    """Extrae TRANSITIONS, ACCEPT y START_STATE de un lexer generado."""
    transitions  = getattr(lexer_mod, "TRANSITIONS",  {})
    accept       = getattr(lexer_mod, "ACCEPT",       {})
    start_state  = getattr(lexer_mod, "START_STATE",  0)
    return transitions, accept, start_state
