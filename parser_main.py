#!/usr/bin/env python3
"""Pipeline principal: .yal + .yapar -> tokens -> tabla LL(1) -> arbol."""

import sys, os, argparse, importlib.util
sys.path.insert(0, os.path.dirname(__file__))

from src.cfg_grammar    import Grammar
from src.left_recursion import has_left_recursion, eliminate_left_recursion, report_left_recursion
from src.factorization  import needs_factorization, left_factor
from src.ambiguity      import is_ambiguous
from src.first_follow   import report_first_follow
from src.ll1_table      import build_ll1_table, print_ll1_table, report_ll1, LL1Parser, LL1ParseError
from src.tree_viz       import print_ascii_tree, render_graphviz, print_derivation
from src.afd_to_cfg     import print_afd_cfg_conversion, load_afd_from_lexer
from src.yapar_parser   import parse_yapar, report_yapar, YAParError


def generate_lexer_from_yal(yal_path: str) -> str:
    import subprocess
    out_path = os.path.join("output", os.path.basename(yal_path).replace(".yal", "_generated.py"))
    os.makedirs("output", exist_ok=True)
    r = subprocess.run([sys.executable, "src/generator.py", yal_path, "-o", out_path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    print(f"Lexer generado: {out_path}")
    return out_path


def load_lexer(lexer_path: str):
    abs_path = os.path.abspath(lexer_path)
    if not os.path.exists(abs_path):
        print(f"[ERROR] Lexer no encontrado: {abs_path}"); sys.exit(1)
    spec = importlib.util.spec_from_file_location("_lexer_mod", abs_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tokenize_source(text: str, lexer_mod) -> list:
    try:
        return lexer_mod.yylex(text)
    except Exception as e:
        print(f"[ERROR LEXICO] {e}"); sys.exit(1)


def require_ll1(grammar: Grammar) -> None:
    _, conflicts = build_ll1_table(grammar)
    if not conflicts:
        return
    print(f"[ERROR] La gramatica no es LL(1): {len(conflicts)} conflicto(s)")
    for c in conflicts:
        print(f"  {c}")
    sys.exit(1)


def print_grammar(grammar: Grammar) -> None:
    _, conflicts = build_ll1_table(grammar)
    print(f"  Simbolo inicial : {grammar.start}")
    print(f"  No-terminales   : {', '.join(sorted(grammar.nonterminals))}")
    print(f"  Terminales      : {', '.join(sorted(grammar.terminals))}")
    print(f"  LL(1)           : {'Si' if not conflicts else 'No (' + str(len(conflicts)) + ' conflictos)'}")
    for nt, prods in grammar.productions.items():
        for p in prods:
            print(f"  {nt:<26} -> {' '.join(p) if p else 'epsilon'}")


def main():
    ap = argparse.ArgumentParser(description="Proyecto 2 - Parser LL(1)")
    grm_group = ap.add_mutually_exclusive_group(required=True)
    grm_group.add_argument("grammar", nargs="?", help="Archivo .grm")
    grm_group.add_argument("--yapar", "-p",      help="Archivo .yapar")

    lex_group = ap.add_mutually_exclusive_group(required=True)
    lex_group.add_argument("--yal",   "-y")
    lex_group.add_argument("--lexer", "-l")

    txt_group = ap.add_mutually_exclusive_group(required=True)
    txt_group.add_argument("--text", "-t")
    txt_group.add_argument("--file", "-f")

    ap.add_argument("--viz",          action="store_true")
    ap.add_argument("--out",          default="output/parse_tree")
    ap.add_argument("--derivation",   "-d", action="store_true")
    ap.add_argument("--show-grammar", action="store_true")
    ap.add_argument("--show-table",   action="store_true")
    ap.add_argument("--afd-to-cfg",   action="store_true")
    args = ap.parse_args()

    # Generar y cargar lexer desde .yal
    lexer_path = generate_lexer_from_yal(args.yal) if args.yal else args.lexer
    lexer_mod  = load_lexer(lexer_path)

    if args.afd_to_cfg:
        trans, acc, start = load_afd_from_lexer(lexer_mod)
        print_afd_cfg_conversion(trans, acc, start)

    # Cargar gramatica
    ignored_tokens = set()
    if args.yapar:
        if not os.path.exists(args.yapar):
            print(f"[ERROR] No encontrado: {args.yapar}"); sys.exit(1)
        try:
            grammar, ignored_tokens = parse_yapar(args.yapar)
            print(f"Gramatica cargada: {args.yapar}")
            print(f"Tokens ignorados : {', '.join(sorted(ignored_tokens)) if ignored_tokens else 'ninguno'}")
        except YAParError as e:
            print(f"[ERROR YAPAR] {e}"); sys.exit(1)
    else:
        if not os.path.exists(args.grammar):
            print(f"[ERROR] No encontrado: {args.grammar}"); sys.exit(1)
        grammar = Grammar.from_file(args.grammar)
        print(f"Gramatica cargada: {args.grammar}")

    # Transformaciones para hacer la gramatica LL(1)
    print(report_left_recursion(grammar))
    if has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
        print("Recursividad izquierda eliminada")

    if needs_factorization(grammar):
        grammar = left_factor(grammar)
        print("Factorizacion aplicada")

    require_ll1(grammar)
    print("Gramatica LL(1) verificada")

    if args.show_grammar:
        print_grammar(grammar)

    print_ll1_table(grammar)

    if args.show_grammar:
        print(report_first_follow(grammar))

    # Tokenizar entrada
    source = args.text if args.text else open(args.file, encoding="utf-8").read()
    raw_tokens = tokenize_source(source, lexer_mod)
    skip   = {"WS", "WHITESPACE", "NEWLINE"} | ignored_tokens
    tokens = [(t, l) for t, l in raw_tokens if t not in skip]
    print(f"Tokens reconocidos: {len(tokens)}")
    for tok, lex in tokens:
        print(f"  {tok:<20} '{lex}'")

    # Parsear con LL(1)
    try:
        ll1  = LL1Parser(grammar, tokens)
        tree = ll1.parse()
    except LL1ParseError as e:
        print(f"[ERROR SINTACTICO] {e}")
        sys.exit(1)

    if ll1.recovery_log:
        print(f"Recuperaciones aplicadas: {len(ll1.recovery_log)}")
        print(ll1.recovery_report())

    print("Cadena aceptada")

    print_ascii_tree(tree, title="Arbol de Derivacion")

    if args.derivation:
        print_derivation(tree)

    if args.viz:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        render_graphviz(tree, output_path=args.out, fmt="png")


if __name__ == "__main__":
    main()
