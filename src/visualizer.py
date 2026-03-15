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


# construye el árbol de expresión a partir del postfix y genera su DOT
def expr_tree_to_dot(postfix: list, token_name: str = "", title: str = "ExprTree") -> str:
    # cada nodo tiene id, label e hijos
    nodes = []
    stack = []
    counter = [0]

    def new_node(label):
        nid = counter[0]
        counter[0] += 1
        nodes.append((nid, label, []))
        return nid

    def add_child(parent, child):
        nodes[parent][2].append(child)

    # reconstruye el árbol desde el postfix usando una pila de nodos
    node_stack = []
    for tok in postfix:
        kind = tok[0]
        if kind == "CHAR":
            sym = tok[1]
            label = sym.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t")
            node_stack.append(new_node(label))
        elif kind == "SET":
            s = sorted(tok[1])
            if len(s) > 6:
                label = f"{s[0]}-{s[-1]}"
            else:
                label = "[" + "".join(s).replace("\\", "\\\\").replace('"', '\\"') + "]"
            node_stack.append(new_node(label))
        elif kind == "ANY":
            node_stack.append(new_node("_"))
        elif kind == "EOF":
            node_stack.append(new_node("eof"))
        elif kind == "OP":
            op = tok[1]
            if op in ("*", "+", "?"):
                # operador unario, un solo hijo
                nid = new_node(op)
                if node_stack:
                    child = node_stack.pop()
                    add_child(nid, child)
                node_stack.append(nid)
            else:
                # operador binario, dos hijos
                nid = new_node(op)
                right = node_stack.pop() if node_stack else new_node("?")
                left  = node_stack.pop() if node_stack else new_node("?")
                add_child(nid, left)
                add_child(nid, right)
                node_stack.append(nid)

    safe_title = title.replace(" ", "_")
    lines = [f'digraph {safe_title} {{', '  node [fontname="Helvetica"];']
    if token_name:
        lines.append(f'  label="{token_name}"; labelloc=t;')

    for nid, label, children in nodes:
        # operadores van en elipse, hojas en rectángulo
        if label in ("·", "|", "*", "+", "?", "#"):
            lines.append(f'  n{nid} [shape=ellipse, label="{label}"];')
        else:
            lines.append(f'  n{nid} [shape=box, label="{label}"];')
        for child in children:
            lines.append(f'  n{nid} -> n{child};')

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
