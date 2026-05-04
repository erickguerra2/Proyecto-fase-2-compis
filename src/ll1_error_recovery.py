"""
ll1_error_recovery.py  -  Recuperacion de errores especifica para LL(1).

A diferencia del panic-mode generico, la recuperacion LL(1) usa la
informacion de la tabla M[NT, terminal] y los conjuntos FOLLOW para
tomar decisiones mas precisas sobre donde continuar.

Algoritmo estandar (Aho, Lam, Sethi, Ullman - Dragon Book):

  Cuando M[A, a] esta vacio (error):

  1. Si 'a' esta en FOLLOW(A):
       -> Aplicar produccion epsilon (saltar A, no consumir 'a')
       -> El parser asume que A derivo epsilon y continua

  2. Si 'a' NO esta en FOLLOW(A):
       -> Descartar 'a' de la entrada (avanzar un token)
       -> Reportar error y continuar

  3. Si el tope de la pila es un terminal t != a:
       -> Descartar t de la pila (insercion ficticia)
       -> Reportar error y continuar

Esta estrategia es mas informada que el panic-mode porque:
  - Usa FOLLOW(A) para saber cuando saltar un NT sin consumir tokens
  - Minimiza los tokens descartados
  - Produce mensajes de error mas precisos
"""

from __future__ import annotations
from typing import List, Tuple, Set, Dict, Optional

from src.first_follow import compute_first, compute_follow, EOF_SYM


class LL1RecoveryAction:
    """Accion tomada durante la recuperacion de un error LL(1)."""
    def __init__(self, kind: str, detail: str,
                 pos: int, token: tuple):
        self.kind   = kind    # 'skip_token' | 'skip_nt' | 'pop_terminal'
        self.detail = detail
        self.pos    = pos
        self.token  = token

    def __str__(self):
        tok = f"'{self.token[1]}' ({self.token[0]})" if self.token else "EOF"
        return f"  [LL1-RECOVERY/{self.kind}] pos={self.pos} token={tok}: {self.detail}"


class LL1ErrorRecovery:
    """
    Manejador de errores LL(1) basado en conjuntos FOLLOW.
    Se inyecta en el LL1Parser para manejar celdas vacias en la tabla.
    """

    def __init__(self, grammar, table: dict):
        self.grammar = grammar
        self.table   = table
        self.first   = compute_first(grammar)
        self.follow  = compute_follow(grammar, self.first)
        self.actions: List[LL1RecoveryAction] = []

    def handle(self,
               top_sym: str,
               tokens: list,
               pos: int) -> Tuple[bool, int, Optional[list]]:
        """
        Intenta recuperarse de un error en M[top_sym, tokens[pos]].

        Devuelve:
          (recuperado, nueva_pos, produccion_a_usar_o_None)
          - recuperado=True  -> continuar el parsing
          - recuperado=False -> error fatal
        """
        if pos >= len(tokens):
            return False, pos, None

        cur_type, cur_lex = tokens[pos]

        # ── Caso 1: top es NT y 'a' esta en FOLLOW(top) ──────────
        # Aplicar epsilon: saltar el NT sin consumir token
        if top_sym in self.grammar.nonterminals:
            follow_set = self.follow.get(top_sym, set())
            if cur_type in follow_set or cur_lex in follow_set:
                self.actions.append(LL1RecoveryAction(
                    "skip_nt",
                    f"{top_sym} saltado ('{cur_type}' in FOLLOW({top_sym})={follow_set})",
                    pos, tokens[pos]
                ))
                return True, pos, []   # produccion epsilon

        # ── Caso 2: top es NT y 'a' NO esta en FOLLOW(top) ───────
        # Descartar el token actual y continuar
        if top_sym in self.grammar.nonterminals:
            self.actions.append(LL1RecoveryAction(
                "skip_token",
                f"token '{cur_lex}' descartado (no esta en FOLLOW({top_sym}))",
                pos, tokens[pos]
            ))
            return True, pos + 1, None   # None = no cambiar tope, solo avanzar

        # ── Caso 3: top es terminal != token actual ───────────────
        # Sacar el terminal de la pila (insercion ficticia)
        self.actions.append(LL1RecoveryAction(
            "pop_terminal",
            f"terminal '{top_sym}' en pila descartado (se encontro '{cur_lex}')",
            pos, tokens[pos]
        ))
        return True, pos, "pop"   # "pop" = sacar tope sin consumir token

    def report(self) -> str:
        if not self.actions:
            return "  Sin errores LL(1) durante el parsing."
        lines = [f"  {len(self.actions)} accion(es) de recuperacion LL(1):"]
        for a in self.actions:
            lines.append(str(a))
        return "\n".join(lines)
