"""Nodo del arbol de derivacion sintactica."""

from __future__ import annotations
from typing import List, Optional


class ParseNode:
    """Nodo del árbol sintáctico de derivación."""

    def __init__(self,
                 symbol: str,
                 lexeme: Optional[str] = None,
                 children: Optional[List["ParseNode"]] = None) -> None:
        self.symbol = symbol          # Nombre del no-terminal o tipo de terminal
        self.lexeme = lexeme          # Valor léxico (solo terminales)
        self.children: List["ParseNode"] = children if children is not None else []

    @property
    def is_terminal(self) -> bool:
        return len(self.children) == 0

    @property
    def label(self) -> str:
        """Etiqueta legible para visualizar."""
        if self.is_terminal and self.lexeme is not None:
            return f"{self.symbol}\n({self.lexeme})"
        return self.symbol

    def to_ascii(self, prefix: str = "", is_last: bool = True) -> str:
        connector = "└── " if is_last else "├── "
        lines = [prefix + connector + self.label.replace("\n", " ")]
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            last = (i == len(self.children) - 1)
            lines.append(child.to_ascii(child_prefix, last))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ParseNode({self.symbol!r}, lexeme={self.lexeme!r}, children={len(self.children)})"
