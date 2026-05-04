"""
afd_to_cfg.py  -  Conversion de AFD a Gramatica Libre de Contexto (CFG).

Teoria (diapositivas 26-29):

  ¿Es posible representar una expresion regular con una CFG?
  SI. Todo lenguaje regular es tambien un lenguaje libre de contexto.
  (La jerarquia de Chomsky: Tipo 3 ⊂ Tipo 2)

  Algoritmo de conversion AFD -> CFG:
    Para cada estado qi del AFD:
      Crear un no-terminal Si

    Para cada transicion qi -a-> qj:
      Agregar produccion:  Si -> a Sj

    Para cada estado de aceptacion qi:
      Agregar produccion:  Si -> epsilon

    El simbolo inicial es S0 (estado inicial del AFD).

  Ejemplo (diapositiva 26-29): AFD para (a|b)*abb
    Estado 0: inicio
    Estado 1: leyo 'a' desde estado 0
    Estado 2: leyo 'ab' desde estado 1
    Estado 3: leyo 'abb' desde estado 2 (aceptacion)

    Producciones resultantes:
      S0 -> a S1 | b S0
      S1 -> a S1 | b S2
      S2 -> a S1 | b S3
      S3 -> epsilon   (estado de aceptacion)

  Resultado: la CFG generada reconoce exactamente el mismo lenguaje
  que el AFD original. Tipo 3 ⊂ Tipo 2 queda demostrado.

  Nota: la CFG resultante tiene recursividad DERECHA (tipica de
  expresiones regulares convertidas a CFG). Es correcta para
  parsers descendentes (top-down).
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


def afd_to_cfg(transitions: dict, accept: dict,
               start_state: int = 0,
               token_name: str = "LEXER") -> Grammar:
    """
    Convierte un AFD (formato del Proyecto 1) a una CFG.

    Parametros:
      transitions : dict de {estado: {caracter: estado_siguiente}}
                    (TRANSITIONS del lexer generado)
      accept      : dict de {estado: tipo_token}
                    (ACCEPT del lexer generado)
      start_state : estado inicial del AFD (default 0)
      token_name  : nombre del token para etiquetar las producciones

    Devuelve: Grammar con las producciones del AFD convertido.
    """
    states = set()
    states.add(start_state)
    for src, chars in transitions.items():
        states.add(src)
        for dst in chars.values():
            states.add(dst)

    # Nombrar cada estado como NT: S0, S1, S2, ...
    def nt(state: int) -> str:
        return f"S{state}"

    prods: dict = {}

    # Inicializar todos los estados
    for s in states:
        prods[nt(s)] = []

    # Para cada transicion qi -char-> qj: agregar Si -> char Sj
    for src, chars in sorted(transitions.items()):
        for char, dst in sorted(chars.items()):
            # Escapar caracteres especiales para la produccion
            safe_char = _safe_terminal(char)
            production = [safe_char, nt(dst)]
            if production not in prods[nt(src)]:
                prods[nt(src)].append(production)

    # Para cada estado de aceptacion: Si -> epsilon
    for state in accept:
        if [] not in prods[nt(state)]:
            prods[nt(state)].append([])

    # Eliminar NTs sin producciones (estados inalcanzables)
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
    print("  Conversion AFD -> CFG (Diapositivas 26-29)")
    print(f"{'='*64}")
    print(f"  Jerarquia Chomsky: Tipo 3 (Regular) ⊂ Tipo 2 (Libre de contexto)")
    print(f"  Todo lenguaje regular puede representarse como CFG.")
    print()
    print(f"  AFD:")
    print(f"    Estados       : {sorted(states)}")
    print(f"    Estado inicial: {start_state}")
    print(f"    Aceptacion    : {dict(sorted(accept.items()))}")
    print()
    print(f"  Algoritmo de conversion:")
    print(f"    Cada estado qi   -> no-terminal Si")
    print(f"    qi -a-> qj       -> produccion Si -> a Sj")
    print(f"    qi en Aceptacion -> produccion Si -> epsilon")
    print()
    print(f"  CFG resultante G = (Σ, N, P, S0):")
    print(f"    Simbolo inicial: {grammar.start}")
    print(f"    No-terminales : {', '.join(sorted(grammar.nonterminals))}")
    print()
    for nt, prods in sorted(grammar.productions.items()):
        for p in prods:
            body = " ".join(p) if p else "ε"
            print(f"    {nt:<10} -> {body}")
    print()
    print(f"  La CFG tiene recursividad DERECHA (tipica de lenguajes regulares).")
    print(f"  Es correcta para parsers descendentes (top-down).")

    return grammar


def load_afd_from_lexer(lexer_mod) -> tuple:
    """Extrae TRANSITIONS, ACCEPT y START_STATE de un lexer generado."""
    transitions  = getattr(lexer_mod, "TRANSITIONS",  {})
    accept       = getattr(lexer_mod, "ACCEPT",       {})
    start_state  = getattr(lexer_mod, "START_STATE",  0)
    return transitions, accept, start_state
