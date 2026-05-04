"""
syntax_parser.py  -  Parser DESCENDENTE (top-down) con retroceso y recuperacion.

Teoria (diapositiva 7):
  Tipos de analizadores sintacticos:
    - DESCENDENTE (top-down): construye el arbol de la RAIZ a las HOJAS.
                              Lee la entrada de izquierda a derecha.
                              Produce derivaciones por la izquierda.
                              <-- ESTE parser
    - Ascendente  (bottom-up): construye de HOJAS a la RAIZ (LR, SLR, LALR)
    - Universal   (CYK):       cualquier CFG, pero mas costoso

Recuperacion de errores (PDF pagina 1):
  - panic-mode   : descarta tokens hasta token de sincronizacion (; {)
  - phrase-level : inserta o elimina el token esperado
"""

from __future__ import annotations
from typing import List, Optional, Tuple

from src.cfg_grammar    import Grammar
from src.parse_tree     import ParseNode
from src.error_recovery import (panic_mode_recovery, phrase_level_recovery,
                                 SyntaxError_, format_errors,
                                 DEFAULT_SYNC_TOKENS)


class ParseError(Exception):
    """Error sintactico fatal (sin recuperacion posible)."""


class SyntaxParser:
    """
    Parser DESCENDENTE recursivo con retroceso y recuperacion de errores.
    Tipo: top-down / LL (diapositiva 7)
    """

    PARSER_TYPE = "Descendente (top-down) - LL con retroceso"

    def __init__(self, grammar: Grammar,
                 tokens: List[Tuple[str, str]],
                 recovery: str = "panic") -> None:
        """
        recovery: modo de recuperacion de errores
          'panic'  -> panic-mode (PDF: descartar hasta ; o {)
          'phrase' -> phrase-level (PDF: insertar/eliminar token)
          'none'   -> sin recuperacion, lanza excepcion al primer error
        """
        self.grammar  = grammar
        self.tokens   = [(t, l) for t, l in tokens
                         if t not in ("WS", "WHITESPACE", "NEWLINE")]
        self.pos      = 0
        self.recovery = recovery
        self.errors: List[SyntaxError_] = []
        self._call_depth = 0
        self._MAX_DEPTH  = 500

    # ------------------------------------------------------------------
    # API publica
    # ------------------------------------------------------------------
    def parse(self) -> ParseNode:
        """Parsea y devuelve la raiz del arbol."""
        self.pos    = 0
        self.errors = []
        tree = self._parse_nt(self.grammar.start)

        if tree is None:
            tok = self.tokens[self.pos] if self.pos < len(self.tokens) else ("EOF", "")
            raise ParseError(
                f"No se pudo derivar '{self.grammar.start}'.\n"
                f"Token inesperado en posicion {self.pos}: {tok}\n"
                f"Tip: verifica que la gramatica cubra este tipo de entrada."
            )
        if self.pos < len(self.tokens):
            remaining = self.tokens[self.pos:]
            raise ParseError(
                f"Entrada no consumida desde posicion {self.pos}: {remaining}\n"
                f"Tip: puede ser un error de ambiguedad o gramatica incompleta."
            )
        return tree

    def parse_with_recovery(self) -> Tuple[Optional[ParseNode], List[SyntaxError_]]:
        """
        Parsea con recuperacion de errores activa.
        Devuelve (arbol, lista_de_errores).
        El arbol puede ser parcial si hubo errores recuperados.
        """
        try:
            tree = self.parse()
            return tree, self.errors
        except ParseError as e:
            # Intentar recuperar
            if self.recovery == "panic" and self.pos < len(self.tokens):
                new_pos, skipped, err = panic_mode_recovery(
                    self.tokens, self.pos
                )
                self.errors.append(err)
                self.pos = new_pos
                # Reintentar desde el nuevo punto
                try:
                    self.pos = 0
                    tree = self._parse_nt(self.grammar.start)
                    if tree and self.pos == len(self.tokens):
                        return tree, self.errors
                except Exception:
                    pass
            return None, self.errors + [SyntaxError_(
                self.pos,
                self.tokens[self.pos] if self.pos < len(self.tokens) else ("EOF",""),
                self.grammar.start,
                recovery="ninguna - error fatal"
            )]

    # ------------------------------------------------------------------
    # Motor interno
    # ------------------------------------------------------------------
    def _parse_nt(self, symbol: str) -> Optional[ParseNode]:
        self._call_depth += 1
        if self._call_depth > self._MAX_DEPTH:
            self._call_depth -= 1
            return None

        productions = self.grammar.productions.get(symbol, [])
        # Probar producciones no-vacias primero, epsilon al final
        ordered = [p for p in productions if p] + [p for p in productions if not p]
        for production in ordered:
            saved_pos = self.pos
            children  = self._try_production(production)
            if children is not None:
                self._call_depth -= 1
                return ParseNode(symbol, children=children)
            self.pos = saved_pos

        self._call_depth -= 1
        return None

    def _try_production(self, production: List[str]) -> Optional[List[ParseNode]]:
        children: List[ParseNode] = []
        if not production:
            return children

        for sym in production:
            if sym in self.grammar.nonterminals:
                child = self._parse_nt(sym)
                if child is None:
                    return None
                children.append(child)
            else:
                if self.pos >= len(self.tokens):
                    return None
                tok_type, tok_lexeme = self.tokens[self.pos]
                if self._match_terminal(sym, tok_type, tok_lexeme):
                    children.append(ParseNode(sym, lexeme=tok_lexeme))
                    self.pos += 1
                else:
                    return None
        return children

    @staticmethod
    def _match_terminal(expected: str, tok_type: str, tok_lexeme: str) -> bool:
        return expected == tok_type or expected == tok_lexeme

    def remaining_tokens(self) -> List[Tuple[str, str]]:
        return self.tokens[self.pos:]

    def error_report(self) -> str:
        return format_errors(self.errors)
