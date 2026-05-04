"""
tree_viz.py  –  Visualización del árbol de derivación sintáctica.

Modos:
  • ASCII   → imprime en consola (siempre disponible)
  • Graphviz → genera imagen PNG/SVG (requiere graphviz instalado)
"""

from __future__ import annotations
import os
from typing import Optional

from src.parse_tree import ParseNode


# ──────────────────────────────────────────────────────────────
# ASCII (consola)
# ──────────────────────────────────────────────────────────────

def print_ascii_tree(root: ParseNode, title: str = "Árbol de Derivación") -> None:
    """Imprime el árbol en la consola usando caracteres ASCII."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    # Raíz sin conector
    _print_node(root, prefix="", is_last=True)
    print()


def _print_node(node: ParseNode, prefix: str, is_last: bool) -> None:
    connector = "└── " if is_last else "├── "
    label = _short_label(node)
    print(prefix + connector + label)
    child_prefix = prefix + ("    " if is_last else "│   ")
    for i, child in enumerate(node.children):
        _print_node(child, child_prefix, i == len(node.children) - 1)


def _short_label(node: ParseNode) -> str:
    if node.is_terminal and node.lexeme is not None:
        return f"[{node.symbol}: '{node.lexeme}']"
    return f"<{node.symbol}>"


# ──────────────────────────────────────────────────────────────
# Graphviz
# ──────────────────────────────────────────────────────────────

def render_graphviz(root: ParseNode,
                    output_path: str = "parse_tree",
                    fmt: str = "png",
                    view: bool = False) -> Optional[str]:
    """
    Genera un PNG/SVG del árbol usando graphviz.
    Devuelve la ruta del archivo generado, o None si graphviz no está disponible.
    """
    try:
        import graphviz
    except ImportError:
        print("[tree_viz] graphviz no instalado: sólo se muestra árbol ASCII.")
        return None

    dot = graphviz.Digraph(
        name="ParseTree",
        comment="Árbol de Derivación Sintáctica",
        graph_attr={
            "rankdir": "TB",
            "splines": "polyline",
            "bgcolor": "white",
            "fontname": "Helvetica",
            "nodesep": "0.4",
            "ranksep": "0.6",
        },
        node_attr={
            "fontname": "Helvetica",
            "fontsize": "12",
            "width": "0.5",
            "height": "0.4",
        },
        edge_attr={"arrowhead": "none", "color": "#555555"},
    )

    counter = [0]

    def add_node(node: ParseNode, parent_id: Optional[str] = None) -> str:
        node_id = f"n{counter[0]}"
        counter[0] += 1

        if node.is_terminal:
            label = f"{node.symbol}\\n{node.lexeme or ''}"
            dot.node(node_id, label=label,
                     shape="rectangle",
                     style="filled",
                     fillcolor="#d0e8ff",
                     color="#4a90d9")
        else:
            dot.node(node_id, label=f"<{node.symbol}>",
                     shape="ellipse",
                     style="filled",
                     fillcolor="#fff4d0",
                     color="#c89010")

        if parent_id:
            dot.edge(parent_id, node_id)

        for child in node.children:
            add_node(child, node_id)

        return node_id

    add_node(root)

    # Asegurar directorio de salida
    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    rendered = dot.render(output_path, format=fmt,
                          cleanup=True, view=view)
    print(f"[tree_viz] Árbol guardado en: {rendered}")
    return rendered


# ──────────────────────────────────────────────────────────────
# Derivación paso a paso (texto)
# ──────────────────────────────────────────────────────────────

def print_derivation(root: ParseNode) -> None:
    """
    Muestra la derivación por la izquierda (leftmost derivation).
    Ejemplo:
        Program
        => StmtList
        => Stmt
        => ID ASSIGN Expr
        => x ASSIGN Expr
        ...
    """
    print("\n" + "="*60)
    print("  Derivación por la Izquierda")
    print("="*60)
    sentential_forms = []
    _leftmost(root, sentential_forms, [])
    prev = None
    for form in sentential_forms:
        text = "  ".join(form)
        if text != prev:
            print(f"  ⇒  {text}")
            prev = text
    print()


def _leftmost(node: ParseNode, forms: list, current: list) -> None:
    """Recorre el árbol en orden y registra las formas sentenciales."""
    if node.is_terminal:
        current.append(node.lexeme or node.symbol)
        return
    # Reemplazar este NT por sus hijos en la forma sentencial actual
    idx = len(current)
    for child in node.children:
        if child.is_terminal:
            current.append(child.lexeme or child.symbol)
        else:
            current.append(f"<{child.symbol}>")
    forms.append(list(current))
    # Ahora expandir cada hijo no-terminal en orden
    offset = 0
    for child in node.children:
        if not child.is_terminal:
            pos = idx + offset
            current[pos] = child.symbol
            _leftmost(child, forms, current)
            offset += len(child.children) - 1 if child.children else 0
        offset += 1
