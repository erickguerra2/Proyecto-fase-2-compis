"""
Genera los diagramas de los autómatas y el árbol de expresión con graphviz.
"""
import subprocess
import os
from nfa import State, EPSILON
from dfa import DFAState


# convierte un símbolo a texto legible para las etiquetas del diagrama
def _safe_label(sym) -> str:
    if sym == EPSILON:  return "ε"
    if sym == "eof":    return "eof"
    if isinstance(sym, frozenset):
        s = sorted(sym)
        if len(s) > 6:
            # conjunto grande, muestra solo el rango
            return f"{s[0]}-{s[-1]}"
        return "".join(s).replace('"', '\\"')
    c = str(sym)
    return c.replace("\\", "\\\\").replace('"', '\\"').replace("\n","\\n").replace("\t","\\t")


# recorre el AFN y genera el código DOT para graficarlo
def nfa_to_dot(start: State, title="NFA") -> str:
    lines = [f'digraph {title} {{', '  rankdir=LR;']
    visited, queue = set(), [start]
    while queue:
        s = queue.pop(0)
        if s.id in visited: continue
        visited.add(s.id)
        # los estados de aceptación van con doble círculo
        shape = "doublecircle" if s.is_accept else "circle"
        label = f"s{s.id}"
        if s.token_name: label += f"\\n{s.token_name}"
        lines.append(f'  {s.id} [shape={shape}, label="{label}"];')
        for sym, targets in s.transitions.items():
            lbl = _safe_label(sym)
            for t in targets:
                lines.append(f'  {s.id} -> {t.id} [label="{lbl}"];')
                if t.id not in visited: queue.append(t)
    lines.append(f'  __start [shape=none, label=""];')
    lines.append(f'  __start -> {start.id};')
    lines.append("}")
    return "\n".join(lines)


# genera el código DOT del AFD
def dfa_to_dot(start: DFAState, all_states: list, title="DFA") -> str:
    lines = [f'digraph {title} {{', '  rankdir=LR;']
    for s in all_states:
        # los estados de aceptación van con doble círculo
        shape = "doublecircle" if s.is_accept else "circle"
        label = f"D{s.id}"
        if s.token_name: label += f"\\n{s.token_name}"
        lines.append(f'  {s.id} [shape={shape}, label="{label}"];')
        for sym, tgt in s.transitions.items():
            lbl = _safe_label(sym)
            lines.append(f'  {s.id} -> {tgt.id} [label="{lbl}"];')
    lines.append(f'  __start [shape=none, label=""];')
    lines.append(f'  __start -> {start.id};')
    lines.append("}")
    return "\n".join(lines)


# genera los nodos del árbol recursivamente
def _dot_nodes(node, lines):
    fp = "{" + ",".join(str(p) for p in sorted(node.firstpos)) + "}"
    lp = "{" + ",".join(str(p) for p in sorted(node.lastpos)) + "}"
    nl = "true" if node.nullable else "false"

    if node.kind == 'leaf':
        label = f"{node.label}\\npos={node.pos}\\nfp={fp} lp={lp}"
        lines.append(f'  n{node.nid} [shape=box, label="{label}"];')
    else:
        label = f"{node.label}\\nnullable={nl}\\nfp={fp}\\nlp={lp}"
        lines.append(f'  n{node.nid} [shape=ellipse, label="{label}"];')

    for child in node.children:
        lines.append(f'  n{node.nid} -> n{child.nid};')
        _dot_nodes(child, lines)


# genera la tabla de followpos
def _dot_followpos_table(leaves, followpos, lines):
    rows = []
    for leaf in leaves:
        fp_str = "{" + ",".join(str(p) for p in sorted(followpos.get(leaf.pos, set()))) + "}"
        sym = leaf.label.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        rows.append(f'<TR><TD>{leaf.pos}</TD><TD>{sym}</TD><TD ALIGN="LEFT">{fp_str}</TD></TR>')

    header = '<TR><TD><B>pos</B></TD><TD><B>símbolo</B></TD><TD><B>followpos</B></TD></TR>'
    table = (
        '  followpos_table [shape=none, margin=0, label=<'
        '<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        + header + "".join(rows) +
        '</TABLE>>];'
    )
    lines.append(table)


# construye el árbol con todos los pos
def expr_tree_to_dot(postfix: list, token_name: str = "", title: str = "ExprTree") -> str:
    from pos_functions import analyze

    if not postfix:
        return f'digraph {title} {{ label="{token_name}"; }}'

    root, followpos, leaves = analyze(postfix)

    safe_title = title.replace(" ", "_")
    lines = [
        f'digraph {safe_title} {{',
        '  node [fontname="Helvetica"];',
        '  rankdir=TB;',
        '  ranksep=0.5;',
    ]
    if token_name:
        lines.append(f'  label="{token_name}"; labelloc=t; fontsize=16;')

    # nodos del árbol
    _dot_nodes(root, lines)

    # tabla de followpos
    _dot_followpos_table(leaves, followpos, lines)

    # conecta la raíz a la tabla
    lines.append(f'  n{root.nid} -> followpos_table [style=invis];')

    lines.append("}")
    return "\n".join(lines)


# guarda el DOT en disco e intenta renderizarlo con graphviz
def render_dot(dot_src: str, out_path: str, fmt="png"):
    dot_file = out_path + ".dot"
    with open(dot_file, "w", encoding="utf-8") as f:
        f.write(dot_src)
    try:
        subprocess.run(["dot", f"-T{fmt}", dot_file, "-o", out_path],
                       check=True, capture_output=True)
        print(f"Imagen generada: {out_path}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        # si graphviz no está instalado queda el archivo .dot
        print(f"graphviz no disponible, archivo DOT en: {dot_file}")
    return dot_file