"""
chomsky.py  -  Conversion a Forma Normal de Chomsky (CNF / FNC).

Jerarquia de Chomsky (diapositiva 6 del PDF):
  Tipo 3 - Lenguajes regulares       -> Automatas finitos
  Tipo 2 - Lenguajes libres contexto -> Automatas descendentes  <-- aqui estamos
  Tipo 1 - Sensibles al contexto     -> Automatas lineales
  Tipo 0 - Recursivamente enumerables-> Maquinas de Turing

Una gramatica libre de contexto esta en Forma Normal de Chomsky (CNF) si
TODAS sus producciones tienen una de estas dos formas:
  A -> B C       (exactamente dos no-terminales)
  A -> a         (exactamente un terminal)

Pasos de conversion (orden estandar):
  1. START  - Nuevo simbolo inicial S0 -> S (evita que S aparezca en RHS)
  2. DEL    - Eliminar producciones epsilon (A -> e), excepto S0 -> e
  3. UNIT   - Eliminar producciones unitarias (A -> B)
  4. TERM   - Reemplazar terminales en producciones largas (A -> a B => A -> Xa B)
  5. BIN    - Romper producciones de longitud > 2 en binarias

Al final: toda produccion es A->BC o A->a (o S0->e si el lenguaje incluye e).
"""

from __future__ import annotations
from src.cfg_grammar import Grammar


# ─────────────────────────────────────────────────────────────
# Paso 1 - START: nuevo simbolo inicial
# ─────────────────────────────────────────────────────────────

def _step_start(prods: dict, start: str) -> tuple:
    """Agrega S0 -> start para que el inicio no aparezca en ningun RHS."""
    # Revisar si el simbolo inicial aparece en algun RHS
    appears_in_rhs = any(
        start in prod
        for rules in prods.values()
        for prod in rules
    )
    if not appears_in_rhs:
        return prods, start   # no hace falta

    new_start = start + "0"
    while new_start in prods:
        new_start += "0"

    new_prods = {new_start: [[start]]}
    new_prods.update({k: [list(p) for p in v] for k, v in prods.items()})
    return new_prods, new_start


# ─────────────────────────────────────────────────────────────
# Paso 2 - DEL: eliminar producciones epsilon
# ─────────────────────────────────────────────────────────────

def _nullable(prods: dict) -> set:
    """Calcula el conjunto de NTs que pueden derivar epsilon."""
    nullable = set()
    changed = True
    while changed:
        changed = False
        for nt, rules in prods.items():
            if nt in nullable:
                continue
            for prod in rules:
                if not prod or all(s in nullable for s in prod):
                    nullable.add(nt)
                    changed = True
                    break
    return nullable


def _step_del(prods: dict, start: str) -> dict:
    """Elimina producciones epsilon sin perder las cadenas que generaban."""
    nullable = _nullable(prods)

    new_prods = {}
    for nt, rules in prods.items():
        new_rules = []
        for prod in rules:
            if not prod:
                continue   # eliminar epsilon por ahora
            # Generar todas las variantes omitiendo los NTs nullables
            variants = _expand_nullable(prod, nullable)
            for v in variants:
                if v and v not in new_rules:
                    new_rules.append(v)
        new_prods[nt] = new_rules

    # Si el simbolo inicial era nullable, conservar S -> epsilon
    if start in nullable:
        new_prods[start] = [[]] + new_prods.get(start, [])

    return new_prods


def _expand_nullable(prod: list, nullable: set) -> list:
    """
    Genera todas las sub-secuencias de prod omitiendo combinaciones
    de simbolos nullables.
    """
    result = [prod]
    for i, sym in enumerate(prod):
        if sym in nullable:
            new_variants = []
            for variant in result:
                # version sin sym en posicion i (ajustada al nuevo indice)
                idx = next((j for j, s in enumerate(variant) if s == sym
                            and variant[:j].count(sym) == prod[:i].count(sym)), None)
                if idx is not None:
                    without = variant[:idx] + variant[idx+1:]
                    if without and without not in new_variants and without not in result:
                        new_variants.append(without)
            result.extend(new_variants)
    return result


# ─────────────────────────────────────────────────────────────
# Paso 3 - UNIT: eliminar producciones unitarias A -> B
# ─────────────────────────────────────────────────────────────

def _unit_closure(nt: str, prods: dict, nonterminals: set) -> set:
    """Conjunto de NTs alcanzables desde nt via producciones unitarias."""
    visited = {nt}
    queue   = [nt]
    while queue:
        current = queue.pop()
        for prod in prods.get(current, []):
            if len(prod) == 1 and prod[0] in nonterminals:
                target = prod[0]
                if target not in visited:
                    visited.add(target)
                    queue.append(target)
    return visited


def _step_unit(prods: dict, nonterminals: set) -> dict:
    """Elimina A -> B reemplazandola con las producciones no-unitarias de B."""
    new_prods = {}
    for nt in prods:
        reachable = _unit_closure(nt, prods, nonterminals)
        new_rules = []
        for target in reachable:
            for prod in prods.get(target, []):
                # Copiar solo producciones no-unitarias
                is_unit = (len(prod) == 1 and prod[0] in nonterminals)
                if not is_unit and prod not in new_rules:
                    new_rules.append(list(prod))
        new_prods[nt] = new_rules
    return new_prods


# ─────────────────────────────────────────────────────────────
# Paso 4 - TERM: reemplazar terminales en producciones largas
# ─────────────────────────────────────────────────────────────

def _step_term(prods: dict, nonterminals: set) -> dict:
    """
    En producciones de longitud >= 2, reemplaza cada terminal 'a' con
    un NT auxiliar X_a -> a.
    """
    terminal_map: dict = {}   # terminal -> NT auxiliar
    new_prods = {nt: [list(p) for p in rules] for nt, rules in prods.items()}

    for nt in list(new_prods.keys()):
        for i, prod in enumerate(new_prods[nt]):
            if len(prod) < 2:
                continue   # A -> a ya esta en CNF
            new_prod = []
            for sym in prod:
                if sym not in nonterminals:
                    # Es un terminal en produccion larga -> necesita NT auxiliar
                    if sym not in terminal_map:
                        aux = "X_" + _safe_name(sym)
                        while aux in new_prods or aux in terminal_map.values():
                            aux += "_"
                        terminal_map[sym] = aux
                        new_prods[aux] = [[sym]]
                        nonterminals.add(aux)
                    new_prod.append(terminal_map[sym])
                else:
                    new_prod.append(sym)
            new_prods[nt][i] = new_prod

    return new_prods


def _safe_name(sym: str) -> str:
    """Convierte un terminal en nombre valido para NT auxiliar."""
    names = {
        '+': 'PLUS', '-': 'MINUS', '*': 'STAR', '/': 'SLASH',
        '(': 'LP',   ')': 'RP',    '=': 'EQ',   ';': 'SEMI',
        ',': 'COMMA','<': 'LT',    '>': 'GT',    '!': 'NOT',
    }
    return names.get(sym, sym)


# ─────────────────────────────────────────────────────────────
# Paso 5 - BIN: romper producciones largas en binarias
# ─────────────────────────────────────────────────────────────

def _step_bin(prods: dict, nonterminals: set) -> dict:
    """
    Convierte producciones de longitud > 2 en cadenas de producciones binarias.
    A -> B C D E  =>  A -> B Y1,  Y1 -> C Y2,  Y2 -> D E
    """
    new_prods = {}
    counter   = [0]

    def fresh(base: str) -> str:
        name = f"{base}_bin{counter[0]}"
        counter[0] += 1
        while name in new_prods or name in prods or name in nonterminals:
            name += "_"
        nonterminals.add(name)
        return name

    for nt, rules in prods.items():
        new_rules = []
        for prod in rules:
            if len(prod) <= 2:
                new_rules.append(list(prod))
                continue
            # Binarizar: A -> B C D E
            # => A -> B Y1,  Y1 -> C Y2,  Y2 -> D E
            current_nt = nt
            remaining = list(prod)
            while len(remaining) > 2:
                head   = remaining[0]
                tail   = remaining[1:]
                new_nt = fresh(nt)
                if current_nt == nt:
                    new_rules.append([head, new_nt])
                else:
                    new_prods[current_nt] = [[head, new_nt]]
                current_nt = new_nt
                remaining  = tail
            # Ultima produccion binaria
            if current_nt == nt:
                new_rules.append(list(remaining))
            else:
                new_prods[current_nt] = [list(remaining)]
        new_prods[nt] = new_rules

    return new_prods


# ─────────────────────────────────────────────────────────────
# API publica
# ─────────────────────────────────────────────────────────────

def to_cnf(grammar: Grammar, verbose: bool = False) -> Grammar:
    """
    Convierte una gramatica libre de contexto a Forma Normal de Chomsky.
    Si verbose=True imprime el estado despues de cada paso.
    """
    prods = {nt: [list(p) for p in rules]
             for nt, rules in grammar.productions.items()}
    start = grammar.start
    nts   = set(grammar.nonterminals)

    def show(step: str):
        if verbose:
            print(f"\n  [CNF] {step}")
            for nt2, rules in prods.items():
                for p in rules:
                    body = " ".join(p) if p else "epsilon"
                    print(f"    {nt2} -> {body}")

    # Paso 1: START
    prods, start = _step_start(prods, start)
    nts = set(prods.keys())
    show("Paso 1 START - nuevo simbolo inicial")

    # Paso 2: DEL (eliminar epsilon)
    prods = _step_del(prods, start)
    nts   = set(prods.keys())
    show("Paso 2 DEL - eliminar epsilon")

    # Paso 3: UNIT (eliminar unitarias)
    prods = _step_unit(prods, nts)
    nts   = set(prods.keys())
    show("Paso 3 UNIT - eliminar producciones unitarias")

    # Paso 4: TERM (aislar terminales)
    prods = _step_term(prods, nts)
    nts   = set(prods.keys())
    show("Paso 4 TERM - aislar terminales en producciones largas")

    # Paso 5: BIN (binarizar)
    prods = _step_bin(prods, nts)
    nts   = set(prods.keys())
    show("Paso 5 BIN - binarizar producciones largas")

    return Grammar.from_dict(start, prods)


def is_cnf(grammar: Grammar) -> bool:
    """Verifica si una gramatica ya esta en CNF."""
    for nt, prods in grammar.productions.items():
        for prod in prods:
            if len(prod) == 0:
                if nt != grammar.start:
                    return False
            elif len(prod) == 1:
                if prod[0] in grammar.nonterminals:
                    return False   # produccion unitaria A -> B
            elif len(prod) == 2:
                if any(s not in grammar.nonterminals for s in prod):
                    return False   # debe ser A -> B C (ambos NTs)
            else:
                return False   # produccion de longitud > 2
    return True
