"""
Conecta todos los módulos y corre el pipeline de generación.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from yal_parser    import parse_yal_file, YalSpec
from macro_expander import expand_macros
from regex_parser  import regexp_to_postfix
from nfa           import build_nfa_from_postfix, build_global_nfa, reset_counter
from dfa           import nfa_to_dfa, minimize_dfa
from codegen       import generate_lexer
from visualizer    import nfa_to_dot, dfa_to_dot, render_dot, expr_tree_to_dot


def run(yal_path: str, output: str = "lexer_generated.py", visualize: bool = False):
    print(f"\nEntrada : {yal_path}")
    print(f"Salida  : {output}\n")

    # lee y parsea el archivo .yal
    print("Leyendo el .yal")
    spec: YalSpec = parse_yal_file(yal_path)
    print(f"Definiciones: {list(spec.definitions.keys())}")
    print(f"Reglas: {len(spec.rules)}")

    if not spec.rules:
        print("No se encontraron reglas")
        sys.exit(1)

    # sustituye las macros en cada patrón
    print("Expandiendo macros")
    patterns = [r.pattern for r in spec.rules]
    expanded = expand_macros(spec.definitions, patterns)
    for i, (orig, exp) in enumerate(zip(patterns, expanded)):
        print(f"Regla {i}: {orig!r:40} -> {exp!r}")

    # infix a postfix
    print("Infix a postfix")
    postfixes = []
    for i, expr in enumerate(expanded):
        pf = regexp_to_postfix(expr)
        postfixes.append(pf)
        print(f"      Regla {i}: {len(pf)} tokens")

    # genera el árbol de expresión por cada regla
    if visualize:
        for i, (pf, rule) in enumerate(zip(postfixes, spec.rules)):
            token_name = _extract_token_name(rule.action)
            dot = expr_tree_to_dot(pf, token_name=token_name, title=f"Tree_{token_name}")
            render_dot(dot, output.replace(".py", f"_tree_{token_name}.png"))

    # construye el AFN global
    print("Construyendo el AFN")
    reset_counter()
    nfa_list = []
    accept_list = []
    for i, (pf, rule) in enumerate(zip(postfixes, spec.rules)):
        token_name = _extract_token_name(rule.action)
        start, accept = build_nfa_from_postfix(pf, token_name=token_name)
        nfa_list.append((start, accept, i))   # el orden define la prioridad del token
        accept_list.append((accept, i, token_name))
        print(f"      {token_name}: listo (prioridad {i})")

    global_start = build_global_nfa(nfa_list)
    print(f"Estado inicial: s{global_start.id}")

    if visualize:
        dot = nfa_to_dot(global_start, "NFA")
        render_dot(dot, output.replace(".py", "_nfa.png"))

    # AFN a AFD
    print("AFN a AFD")
    dfa_start, all_dfa = nfa_to_dfa(global_start, accept_list)
    print(f"      {len(all_dfa)} estados")

    if visualize:
        dot = dfa_to_dot(dfa_start, all_dfa, "DFA")
        render_dot(dot, output.replace(".py", "_dfa.png"))

    # minimiza el AFD con Hopcroft
    print("Minimizando el AFD")
    min_start, min_states = minimize_dfa(dfa_start, all_dfa)
    print(f"      {len(min_states)} estados")

    if visualize:
        dot = dfa_to_dot(min_start, min_states, "DFA_min")
        render_dot(dot, output.replace(".py", "_dfa_min.png"))

    # genera el archivo .py del lexer
    print(f"Generando {output}")
    rules_actions = [(_extract_token_name(r.action), r.action) for r in spec.rules]
    generate_lexer(
        dfa_start    = min_start,
        all_states   = min_states,
        rules_actions= rules_actions,
        header_code  = spec.header,
        trailer_code = spec.trailer,
        output_path  = output,
    )

    print("\nListo\n")


def _extract_token_name(action_code: str) -> str:
    # saca el nombre del token del bloque de acción
    import re
    m = re.search(r'return\s+([A-Za-z_]\w*)', action_code)
    if m: return m.group(1)
    m = re.search(r'return\s+(\w+)\s*\(', action_code)
    if m: return m.group(1)
    return action_code.strip()[:20]


# lee los argumentos de la terminal

def main():
    parser = argparse.ArgumentParser(description="YALex Generator")
    parser.add_argument("input",  help="archivo .yal")
    parser.add_argument("-o", "--output", default="lexer_generated.py",
                        help="archivo de salida")
    parser.add_argument("--viz", action="store_true",
                        help="genera los diagramas de los automatas")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"No se encontró el archivo '{args.input}'")
        sys.exit(1)

    run(args.input, args.output, visualize=args.viz)


if __name__ == "__main__":
    main()
