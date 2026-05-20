#!/usr/bin/env python3
"""Pipeline principal: .yal + .yapar -> tokens -> LL(1) | SLR(1) | LALR."""

import sys, os, argparse, importlib.util
sys.path.insert(0, os.path.dirname(__file__))

from src.cfg_grammar         import Grammar
from src.ambiguity           import (detect_ll1_problems, full_chain_analysis)
from src.error_recovery      import report_fix_production_issues
from src.first_follow        import report_first_follow
from src.yapar_parser        import parse_yapar, YAParError

from src.ll1.left_recursion  import has_left_recursion, eliminate_left_recursion, report_left_recursion
from src.ll1.factorization   import needs_factorization, left_factor
from src.ll1.ll1_table       import build_ll1_table, print_ll1_table, LL1Parser, LL1ParseError

from src.lr.lr0              import build_lr0, report_lr0, report_augmented_grammar, report_gotos
from src.slr1.slr1           import build_slr1_table, SLR1Parser, SLR1ParseError
from src.lalr.lalr           import build_lalr_table, LALRParser, LALRParseError


def generate_lexer_from_yal(yal_path: str) -> str:
    import subprocess
    base = os.path.basename(yal_path)
    for ext in (".yalex", ".yal"):
        base = base.replace(ext, "")
    out_path = os.path.join("output", base + "_generated.py")
    os.makedirs("output", exist_ok=True)
    r = subprocess.run([sys.executable, "src/lexer/generator.py", yal_path, "-o", out_path],
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
        raw = lexer_mod.yylex(text)
        # Normaliza a token, lexema, linea, col; lexers antiguos devuelven 2-tuplas
        result = []
        for tok in raw:
            if len(tok) >= 4:
                result.append((tok[0], tok[1], tok[2], tok[3]))
            else:
                result.append((tok[0], tok[1], None, None))
        return result
    except Exception as e:
        print(f"[ERROR LEXICO] {e}"); sys.exit(1)


def load_grammar(yapar_path: str) -> tuple:
    if not os.path.exists(yapar_path):
        print(f"[ERROR] No encontrado: {yapar_path}"); sys.exit(1)
    try:
        grammar, ignored_tokens = parse_yapar(yapar_path)
        print(f"Gramatica cargada: {yapar_path}")
        print(f"Tokens ignorados : {', '.join(sorted(ignored_tokens)) or 'ninguno'}")
        return grammar, ignored_tokens
    except YAParError as e:
        print(f"[ERROR YAPAR] {e}"); sys.exit(1)



def run_ll1(grammar: Grammar, tokens: list) -> None:
    grammar, prod_report, _ = report_fix_production_issues(grammar)
    print(prod_report)

    # Detectar ambiguedad con la gramatica original, mostrar arboles y corregir
    grammar, amb_report, _ = full_chain_analysis(grammar, tokens, None, "LL(1)", fix=True, pre_parse=True)
    print(amb_report)

    # Preparacion LL(1): eliminar recursividad izquierda y factorizar
    ll1_problems = detect_ll1_problems(grammar)
    if ll1_problems:
        print(f"Problemas LL(1), no ambiguedad: {len(ll1_problems)} prefijos comunes -> se aplica factorizacion")

    print(report_left_recursion(grammar))
    if has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
        print("Recursividad izquierda eliminada")

    if needs_factorization(grammar):
        grammar = left_factor(grammar)
        print("Factorizacion aplicada")

    _, conflicts = build_ll1_table(grammar)
    if conflicts:
        print(f"[ERROR] La gramatica no es LL(1): {len(conflicts)} conflictos")
        for c in conflicts: print(f"  {c}")
        sys.exit(1)
    print("Gramatica LL(1) verificada")

    print(report_first_follow(grammar))
    print_ll1_table(grammar)

    # Parse con la gramatica ya corregida
    try:
        parser = LL1Parser(grammar, tokens)
        parser.parse()
    except LL1ParseError as e:
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())

    # Arbol final + confirmar que la gramatica corregida no tiene ambiguedad
    _, reporte, _ = full_chain_analysis(grammar, tokens, parser.parse_tree, "LL(1)", fix=True)
    print(reporte)
    print("Cadena aceptada (LL(1))")


def run_slr1(grammar: Grammar, tokens: list) -> None:
    print(report_augmented_grammar(grammar))
    states, aug_start = build_lr0(grammar)
    print(report_lr0(states))
    print(report_gotos(states))

    table, _, _ = build_slr1_table(grammar)
    print(table.report())

    table.print_table(
        terminals=sorted(grammar.terminals | {"$"}),
        nonterminals=sorted(grammar.nonterminals)
    )

    # --- Parse ---
    try:
        parser = SLR1Parser(grammar, tokens)
        parser.parse()
    except SLR1ParseError as e:
        _, reporte, _ = full_chain_analysis(grammar, tokens, None, "SLR(1)", fix=False)
        print(reporte)
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())

    # Arbol de la cadena + verificacion de ambiguedad, sin correccion automatica para LR
    _, reporte, _ = full_chain_analysis(grammar, tokens, parser.parse_tree, "SLR(1)", fix=False)
    print(reporte)

    print("Cadena aceptada (SLR(1))")


def run_lalr(grammar: Grammar, tokens: list) -> None:
    print(report_augmented_grammar(grammar))

    table, states, _ = build_lalr_table(grammar)
    print(report_lr0(states))
    print(report_gotos(states))

    print(table.report())

    table.print_table(
        terminals=sorted(grammar.terminals | {"$"}),
        nonterminals=sorted(grammar.nonterminals)
    )

    # --- Parse ---
    try:
        parser = LALRParser(grammar, tokens)
        parser.parse()
    except LALRParseError as e:
        _, reporte, _ = full_chain_analysis(grammar, tokens, None, "LALR", fix=False)
        print(reporte)
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())

    # Arbol de la cadena + verificacion de ambiguedad, sin correccion automatica para LR
    _, reporte, _ = full_chain_analysis(grammar, tokens, parser.parse_tree, "LALR", fix=False)
    print(reporte)

    print("Cadena aceptada (LALR)")


def main():
    ap = argparse.ArgumentParser(description="Proyecto 2 - Generador de Analizadores Sintacticos")
    ap.add_argument("--yapar",  "-p", required=True, help="Archivo .yapar")

    lex_group = ap.add_mutually_exclusive_group(required=True)
    lex_group.add_argument("--yal",   "-y", help="Archivo .yalex / .yal (genera lexer)")
    lex_group.add_argument("--lexer", "-l", help="Lexer ya generado (.py)")

    txt_group = ap.add_mutually_exclusive_group(required=True)
    txt_group.add_argument("--text", "-t")
    txt_group.add_argument("--file", "-f")

    ap.add_argument("--parser", "-m", choices=["ll1", "slr1", "lalr"], default="slr1")
    args = ap.parse_args()

    lexer_path = generate_lexer_from_yal(args.yal) if args.yal else args.lexer
    lexer_mod  = load_lexer(lexer_path)

    grammar, ignored_tokens = load_grammar(args.yapar)

    if args.text:
        source = args.text
    else:
        with open(args.file, encoding="utf-8") as fh:
            source = fh.read()
    raw_tokens = tokenize_source(source, lexer_mod)
    skip       = {"WS", "WHITESPACE", "NEWLINE"} | ignored_tokens
    tokens     = [tok for tok in raw_tokens if tok[0] not in skip]
    print(f"Tokens reconocidos: {len(tokens)}")

    if args.parser == "ll1":
        run_ll1(grammar, tokens)
    elif args.parser == "slr1":
        run_slr1(grammar, tokens)
    elif args.parser == "lalr":
        run_lalr(grammar, tokens)


if __name__ == "__main__":
    main()
