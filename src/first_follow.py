"""
first_follow.py  -  Conjuntos FIRST y FOLLOW para gramaticas LL(1).

Teoria:

  FIRST(alpha):
    Conjunto de terminales que pueden aparecer al INICIO de cualquier
    cadena derivable desde alpha.
    Si alpha puede derivar epsilon, entonces epsilon pertenece a FIRST(alpha).

    Reglas de calculo:
      1. Si X es terminal: FIRST(X) = {X}
      2. Si X -> epsilon:  epsilon in FIRST(X)
      3. Si X -> Y1 Y2...Yk:
           agregar FIRST(Y1) - {epsilon} a FIRST(X)
           si epsilon in FIRST(Y1): agregar FIRST(Y2) - {epsilon}, etc.
           si epsilon in FIRST(Yi) para todo i: agregar epsilon

  FOLLOW(A):
    Conjunto de terminales que pueden aparecer DESPUES de A en
    alguna forma sentencial.
    $ (fin de cadena) pertenece a FOLLOW del simbolo inicial.

    Reglas de calculo:
      1. $ in FOLLOW(S)  donde S es el simbolo inicial
      2. Si A -> alpha B beta:
           FIRST(beta) - {epsilon} subset FOLLOW(B)
           si epsilon in FIRST(beta): FOLLOW(A) subset FOLLOW(B)
      3. Si A -> alpha B:
           FOLLOW(A) subset FOLLOW(B)

  Importancia:
    FIRST y FOLLOW se usan para construir la tabla de parsing LL(1)
    y para saber cuando aplicar una produccion epsilon.
"""

from __future__ import annotations
from typing import Dict, Set
from src.cfg_grammar import Grammar

EPSILON = "epsilon"
EOF_SYM = "$"


def compute_first(grammar: Grammar) -> Dict[str, Set[str]]:
    """
    Calcula FIRST(X) para cada simbolo X de la gramatica.
    Devuelve un dict: simbolo -> conjunto de terminales (+ 'epsilon').
    """
    first: Dict[str, Set[str]] = {}

    # Inicializar: terminales tienen FIRST = {ellos mismos}
    for t in grammar.terminals:
        first[t] = {t}
    first[EPSILON] = {EPSILON}

    # Inicializar NTs con conjunto vacio
    for nt in grammar.nonterminals:
        first[nt] = set()

    changed = True
    while changed:
        changed = False
        for nt, prods in grammar.productions.items():
            for prod in prods:
                before = len(first[nt])

                if not prod:
                    # A -> epsilon
                    first[nt].add(EPSILON)
                else:
                    # A -> Y1 Y2 ... Yk
                    all_nullable = True
                    for sym in prod:
                        sym_first = first.get(sym, {sym})
                        # agregar FIRST(sym) - {epsilon}
                        first[nt] |= (sym_first - {EPSILON})
                        if EPSILON not in sym_first:
                            all_nullable = False
                            break
                    if all_nullable:
                        first[nt].add(EPSILON)

                if len(first[nt]) != before:
                    changed = True

    return first


def first_of_string(symbols: list, first: Dict[str, Set[str]]) -> Set[str]:
    """
    Calcula FIRST de una cadena de simbolos (no solo uno).
    Util para calcular FIRST(beta) en las reglas de FOLLOW.
    """
    result = set()
    all_nullable = True
    for sym in symbols:
        sym_first = first.get(sym, {sym})
        result |= (sym_first - {EPSILON})
        if EPSILON not in sym_first:
            all_nullable = False
            break
    if all_nullable:
        result.add(EPSILON)
    return result


def compute_follow(grammar: Grammar,
                   first: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """
    Calcula FOLLOW(A) para cada no-terminal A.
    Devuelve un dict: NT -> conjunto de terminales (+ '$').
    """
    follow: Dict[str, Set[str]] = {nt: set() for nt in grammar.nonterminals}
    follow[grammar.start].add(EOF_SYM)

    changed = True
    while changed:
        changed = False
        for nt, prods in grammar.productions.items():
            for prod in prods:
                for i, sym in enumerate(prod):
                    if sym not in grammar.nonterminals:
                        continue
                    before = len(follow[sym])
                    beta = prod[i+1:]   # lo que viene despues de sym

                    if beta:
                        beta_first = first_of_string(beta, first)
                        follow[sym] |= (beta_first - {EPSILON})
                        if EPSILON in beta_first:
                            follow[sym] |= follow[nt]
                    else:
                        # sym es el ultimo simbolo: FOLLOW(nt) ⊆ FOLLOW(sym)
                        follow[sym] |= follow[nt]

                    if len(follow[sym]) != before:
                        changed = True

    return follow


def print_first_follow(grammar: Grammar) -> None:
    """Imprime los conjuntos FIRST y FOLLOW formateados."""
    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)

    print(f"\n{'='*64}")
    print("  Conjuntos FIRST y FOLLOW")
    print(f"{'='*64}")
    print(f"  {'NT':<24} {'FIRST':<30} FOLLOW")
    print("  " + "-"*62)
    for nt in sorted(grammar.nonterminals):
        f1 = ", ".join(sorted(first.get(nt, set())))
        f2 = ", ".join(sorted(follow.get(nt, set())))
        print(f"  {nt:<24} {f1:<30} {f2}")


def report_first_follow(grammar: Grammar) -> str:
    first  = compute_first(grammar)
    follow = compute_follow(grammar, first)
    lines  = ["Conjuntos FIRST y FOLLOW:"]
    lines.append(f"  {'NT':<24} {'FIRST':<34} FOLLOW")
    lines.append("  " + "-"*66)
    for nt in sorted(grammar.nonterminals):
        f1 = "{" + ", ".join(sorted(first.get(nt, set()))) + "}"
        f2 = "{" + ", ".join(sorted(follow.get(nt, set()))) + "}"
        lines.append(f"  {nt:<24} {f1:<34} {f2}")
    return "\n".join(lines)
