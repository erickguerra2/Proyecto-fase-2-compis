#!/usr/bin/env python3
"""Pipeline principal: .yal + .yapar -> tokens -> LL(1) | SLR(1) | LALR."""

import sys, os, argparse, importlib.util
sys.path.insert(0, os.path.dirname(__file__))

from src.cfg_grammar         import Grammar
from src.ambiguity           import report_fix_ambiguity
from src.error_recovery      import report_fix_production_issues
from src.first_follow        import report_first_follow
from src.yapar_parser        import parse_yapar, YAParError

from src.ll1.left_recursion  import has_left_recursion, eliminate_left_recursion, report_left_recursion
from src.ll1.factorization   import needs_factorization, left_factor
from src.ll1.ll1_table       import build_ll1_table, print_ll1_table, LL1Parser, LL1ParseError

from src.lr.lr0              import build_lr0, report_lr0, report_augmented_grammar, report_gotos
from src.slr1.slr1           import build_slr1_table, SLR1Parser, SLR1ParseError, report_slr1
from src.lalr.lalr           import build_lalr_table, LALRParser, LALRParseError, report_lalr


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
        # Normaliza a (token, lexema, linea, col); lexers antiguos devuelven 2-tuplas
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


def print_grammar_productions(grammar: Grammar) -> None:
    """Muestra la gramatica con todas sus producciones."""
    print("\nGramatica:")
    for prod in grammar.productions.get(grammar.start, []):
        body = " ".join(prod) if prod else "ε"
        print(f"  {grammar.start} -> {body}")
    for nt, prods in grammar.productions.items():
        if nt == grammar.start:
            continue
        for prod in prods:
            body = " ".join(prod) if prod else "ε"
            print(f"  {nt} -> {body}")


def preprocess(grammar: Grammar) -> tuple:
    """Limpieza estructural comun a todos los parsers (unitarias, epsilon, duplicados)."""
    grammar, prod_report, prod_applied = report_fix_production_issues(grammar)
    print(prod_report)
    return grammar, prod_applied

def run_ll1(grammar: Grammar, tokens: list, applied: set) -> None:
    grammar, amb_report, amb_applied = report_fix_ambiguity(grammar)
    print(amb_report)
    applied = applied | amb_applied

    print(report_left_recursion(grammar))
    if "left_recursion_eliminated" not in applied and has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
        print("Recursividad izquierda eliminada")

    if "factorized" not in applied and needs_factorization(grammar):
        grammar = left_factor(grammar)
        print("Factorizacion aplicada")

    print_grammar_productions(grammar)

    _, conflicts = build_ll1_table(grammar)
    if conflicts:
        print(f"[ERROR] La gramatica no es LL(1): {len(conflicts)} conflicto(s)")
        for c in conflicts: print(f"  {c}")
        sys.exit(1)
    print("Gramatica LL(1) verificada")

    print(report_first_follow(grammar))
    print_ll1_table(grammar)

    try:
        parser = LL1Parser(grammar, tokens)
        parser.parse()
    except LL1ParseError as e:
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())
    print("Cadena aceptada (LL(1))")


def run_slr1(grammar: Grammar, tokens: list) -> None:
    print(report_augmented_grammar(grammar))
    states, aug_start = build_lr0(grammar)
    print(report_lr0(states))
    print(report_gotos(states))

    table, _, _ = build_slr1_table(grammar)
    print(table.report())
    if table.has_conflicts():
        print(f"[ADVERTENCIA] {len(table.conflicts)} conflicto(s) SLR(1):")
        for c in table.conflicts: print(str(c))

    table.print_table(
        terminals=sorted(grammar.terminals | {"$"}),
        nonterminals=sorted(grammar.nonterminals)
    )

    try:
        parser = SLR1Parser(grammar, tokens)
        parser.parse()
    except SLR1ParseError as e:
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())
    print("Cadena aceptada (SLR(1))")


def run_lalr(grammar: Grammar, tokens: list) -> None:
    print(report_augmented_grammar(grammar))

    table, states, _ = build_lalr_table(grammar)
    print(report_lr0(states))
    print(report_gotos(states))

    print(table.report())
    if table.has_conflicts():
        print(f"[ADVERTENCIA] {len(table.conflicts)} conflicto(s) LALR:")
        for c in table.conflicts: print(str(c))

    table.print_table(
        terminals=sorted(grammar.terminals | {"$"}),
        nonterminals=sorted(grammar.nonterminals)
    )

    try:
        parser = LALRParser(grammar, tokens)
        parser.parse()
    except LALRParseError as e:
        print(f"[ERROR SINTACTICO] {e}"); sys.exit(1)

    if parser.recovery_log:
        print(parser.recovery_report())
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

    ap.add_argument("--parser",     "-m", choices=["ll1", "slr1", "lalr"], default="slr1")
    ap.add_argument("--afd-to-cfg", action="store_true")
    args = ap.parse_args()

    lexer_path = generate_lexer_from_yal(args.yal) if args.yal else args.lexer
    lexer_mod  = load_lexer(lexer_path)

    grammar, ignored_tokens = load_grammar(args.yapar)
    grammar, applied        = preprocess(grammar)
    print_grammar_productions(grammar)

    source     = args.text if args.text else open(args.file, encoding="utf-8").read()
    raw_tokens = tokenize_source(source, lexer_mod)
    skip       = {"WS", "WHITESPACE", "NEWLINE"} | ignored_tokens
    tokens     = [tok for tok in raw_tokens if tok[0] not in skip]
    print(f"Tokens reconocidos: {len(tokens)}")
    for tok, lex, ln, col in tokens:
        pos = f" [{ln}:{col}]" if ln is not None else ""
        print(f"  {tok:<20} '{lex}'{pos}")

    if args.parser == "ll1":
        run_ll1(grammar, tokens, applied)
    elif args.parser == "slr1":
        run_slr1(grammar, tokens)
    elif args.parser == "lalr":
        run_lalr(grammar, tokens)


if __name__ == "__main__":
    main()
