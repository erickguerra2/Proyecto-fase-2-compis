#!/usr/bin/env python3
"""
parser_main.py  -  Proyecto 2: Parser Sintactico LL(1)
=======================================================

Parser PURO LL(1).  Si la gramatica no puede convertirse a LL(1)
despues de eliminar recursividad izquierda y factorizar, el programa
reporta el conflicto y termina con error.  No hay fallback.

Pipeline:
  .yal -> generator.py -> lexer.py -> tokens -> LL(1) table -> arbol

USO:
  python parser_main.py examples/grammar_ejemplo2.grm \\
         --yal examples/ejemplo2.yal --file test.txt

  python parser_main.py examples/grammar_c.grm \\
         --yal examples/expresiones.yal --file test.c

  python parser_main.py examples/grammar_ejemplo2.grm \\
         --yal examples/ejemplo2.yal --file test.txt --show-grammar --viz
"""

import sys, os, argparse, importlib.util
sys.path.insert(0, os.path.dirname(__file__))

from src.cfg_grammar    import Grammar
from src.left_recursion import has_left_recursion, eliminate_left_recursion
from src.right_recursion import report_recursion
from src.factorization  import needs_factorization, left_factor
from src.chomsky        import to_cnf, is_cnf
from src.ambiguity      import report_ambiguity, is_ambiguous
from src.precedence     import analyze_precedence
from src.first_follow   import report_first_follow
from src.ll1_table      import (build_ll1_table, print_ll1_table,
                                 report_ll1, is_ll1,
                                 LL1Parser, LL1ParseError)
from src.error_recovery import (production_level_report,
                                 global_min_edit_distance)
from src.tree_viz       import print_ascii_tree, render_graphviz, print_derivation
from src.afd_to_cfg     import print_afd_cfg_conversion, load_afd_from_lexer


# ─────────────────────────────────────────────────────────────
# Pipeline: .yal -> lexer
# ─────────────────────────────────────────────────────────────

def generate_lexer_from_yal(yal_path: str) -> str:
    import subprocess
    out_path = os.path.join("output",
               os.path.basename(yal_path).replace(".yal", "_generated.py"))
    os.makedirs("output", exist_ok=True)
    print(f"\n[PIPELINE] Proyecto 1: {yal_path}")
    r = subprocess.run(
        [sys.executable, "src/generator.py", yal_path, "-o", out_path],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    for line in r.stdout.splitlines():
        if any(k in line for k in ["Reglas:", "estados", "Listo", "Generando"]):
            print(f"  {line.strip()}")
    print(f"[PIPELINE] Lexer listo: {out_path}")
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


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def print_grammar(grammar: Grammar, title: str) -> None:
    _, conflicts = build_ll1_table(grammar)
    print(f"\n{'='*64}")
    print(f"  {title}")
    print(f"{'='*64}")
    print(f"  Simbolo inicial : {grammar.start}")
    print(f"  No-terminales   : {', '.join(sorted(grammar.nonterminals))}")
    print(f"  Terminales      : {', '.join(sorted(grammar.terminals))}")
    print(f"  CNF             : {'Si' if is_cnf(grammar) else 'No'}")
    print(f"  LL(1)           : {'Si' if not conflicts else 'No (' + str(len(conflicts)) + ' conflictos)'}")
    print()
    for nt, prods in grammar.productions.items():
        for p in prods:
            body = " ".join(p) if p else "epsilon"
            print(f"  {nt:<26} -> {body}")


def print_tokens(tokens: list) -> None:
    visible = [(t, l) for t, l in tokens
               if t not in ("WS", "WHITESPACE", "NEWLINE")]
    skipped = len(tokens) - len(visible)
    print(f"\n{'='*64}")
    print(f"  Tokens del Proyecto 1  ({len(tokens)} total, {skipped} omitidos)")
    print(f"{'='*64}")
    for i, (tok, lex) in enumerate(visible):
        print(f"  [{i:3d}]  {tok:<26}  '{lex}'")


def require_ll1(grammar: Grammar) -> None:
    """
    Verifica que la gramatica sea LL(1).
    Si hay conflictos, los reporta y termina el programa.
    No hay fallback: si no es LL(1), es un error de la gramatica.
    """
    _, conflicts = build_ll1_table(grammar)
    if not conflicts:
        return

    print(f"\n{'='*64}")
    print("  ERROR: La gramatica NO es LL(1)")
    print(f"{'='*64}")
    print(f"  Se encontraron {len(conflicts)} conflicto(s) en la tabla M[NT, terminal].")
    print()
    for c in conflicts:
        print(str(c))
    print()
    print("  Causas comunes:")
    print("    - Recursividad izquierda no eliminada")
    print("    - Prefijos comunes no factorizados")
    print("    - Gramatica inherentemente ambigua")
    print()
    print("  Solucion: reescribir la gramatica .grm para que sea LL(1).")
    print("  Referencia: diapositivas 22 (recursividad) y 24-25 (factorizacion).")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Proyecto 2 - Parser Sintactico LL(1) puro",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("grammar")

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
    ap.add_argument("--cnf",          action="store_true")
    ap.add_argument("--afd-to-cfg",   action="store_true")
    args = ap.parse_args()

    # ── Header ───────────────────────────────────────────────
    print("\n" + "="*64)
    print("  PROYECTO 2 - Parser Sintactico LL(1)")
    print("  Jerarquia Chomsky: Tipo 2 - Lenguajes libres de contexto")
    print("  Parser           : Predictivo LL(1) O(n) - tabla M[NT,a]")
    print("="*64)

    # ── Lexer ────────────────────────────────────────────────
    lexer_path = generate_lexer_from_yal(args.yal) if args.yal else args.lexer
    lexer_mod  = load_lexer(lexer_path)
    tok_types  = sorted(set(getattr(lexer_mod, "ACCEPT", {}).values()))
    print(f"\n[LEXER] Tokens reconocidos:")
    for i in range(0, len(tok_types), 6):
        print("  " + "  ".join(tok_types[i:i+6]))

    # ── AFD -> CFG (diap. 26-29) ─────────────────────────────
    if args.afd_to_cfg:
        trans, acc, start = load_afd_from_lexer(lexer_mod)
        print_afd_cfg_conversion(trans, acc, start)

    # ── Gramatica ────────────────────────────────────────────
    if not os.path.exists(args.grammar):
        print(f"[ERROR] Gramatica no encontrada: {args.grammar}"); sys.exit(1)
    grammar = Grammar.from_file(args.grammar)

    if args.show_grammar:
        print_grammar(grammar, "Gramatica original G = (Sigma, N, P, S)")

    # ── Informacion teorica ───────────────────────────────────
    print(f"\n{'='*64}")
    print("  Tipos de Errores (PDF p.1)")
    print(f"{'='*64}")
    print("  Lexical  : tokens mal formados  (Proyecto 1)")
    print("  Syntax   : oracion mal formada  (ESTE modulo)")
    print("  Semantic : errores de tipos     (fuera de alcance)")
    print("  Logic    : errores de logica    (fuera de alcance)")

    print("\n" + report_ambiguity(grammar))
    print("\n" + analyze_precedence(grammar))
    print("\n" + report_recursion(grammar))

    # ── Transformaciones para obtener LL(1) ───────────────────

    # Paso 1: eliminar recursividad izquierda (diap. 22)
    if has_left_recursion(grammar):
        print("\n[TRANSF] Paso 1: Eliminar recursividad izquierda (diap. 22)...")
        grammar = eliminate_left_recursion(grammar)
        if args.show_grammar:
            print_grammar(grammar, "Despues: sin recursividad izquierda")

    # Paso 2: factorizar (diap. 24-25)
    if needs_factorization(grammar):
        print("\n[TRANSF] Paso 2: Factorizacion por la izquierda (diap. 24-25)...")
        grammar = left_factor(grammar)
        if args.show_grammar:
            print_grammar(grammar, "Despues: factorizada")

    # CNF opcional
    if args.cnf:
        if not is_cnf(grammar):
            print("\n[TRANSF] Convirtiendo a CNF (START->DEL->UNIT->TERM->BIN)...")
            grammar = to_cnf(grammar, verbose=args.show_grammar)

    # ── Verificar que sea LL(1) — SIN FALLBACK ────────────────
    # Si no es LL(1) despues de las transformaciones, error.
    require_ll1(grammar)

    # ── FIRST / FOLLOW + Tabla LL(1) ──────────────────────────
    print("\n" + report_first_follow(grammar))
    print("\n" + report_ll1(grammar))

    if args.show_grammar:
        print_ll1_table(grammar)

    print("\n" + production_level_report(grammar))
    print_grammar(grammar, "Gramatica LL(1) lista para parsear")

    # ── Tokenizar ────────────────────────────────────────────
    source = args.text if args.text else open(args.file, encoding="utf-8").read()
    print(f"\n[INPUT] {repr(source[:100])}{'...' if len(source)>100 else ''}")
    raw_tokens = tokenize_source(source, lexer_mod)
    print_tokens(raw_tokens)

    print("\n" + global_min_edit_distance(raw_tokens, grammar.terminals))

    # ── Parser LL(1) puro ─────────────────────────────────────
    print(f"\n[PARSER] LL(1) predictivo - tabla M[NT, terminal]")
    print(f"[PARSER] Sin backtracking. Recuperacion: FOLLOW sets.")

    try:
        ll1 = LL1Parser(grammar, raw_tokens)
        tree = ll1.parse()
    except LL1ParseError as e:
        print(f"\n[ERROR SINTACTICO] {e}")
        sys.exit(1)

    if ll1.recovery_log:
        print(f"\n{'='*64}")
        print("  Recuperacion LL(1) con FOLLOW sets (PDF p.1)")
        print(f"{'='*64}")
        print(ll1.recovery_report())

    # ── Arbol ────────────────────────────────────────────────
    print_ascii_tree(tree, title="Arbol de Derivacion Sintactica (diap. 14-17)")

    if args.derivation:
        print_derivation(tree)

    if args.viz:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        render_graphviz(tree, output_path=args.out, fmt="png")
        print(f"\n[OUTPUT] Imagen: {args.out}.png")

    # ── Resumen ──────────────────────────────────────────────
    visible = [t for t in raw_tokens
               if t[0] not in ("WS", "WHITESPACE", "NEWLINE")]
    print(f"\n{'='*64}")
    print("  Resumen")
    print(f"{'='*64}")
    print(f"  Parser           : LL(1) predictivo puro")
    print(f"  Tokens procesados: {len(visible)}")
    print(f"  Recuperaciones   : {len(ll1.recovery_log)}")
    print(f"  Arbol generado   : {'Si' if tree else 'No'}")
    print(f"  Gramatica LL(1)  : Si")
    print(f"  Gramatica CNF    : {'Si' if is_cnf(grammar) else 'No'}")
    print(f"  Ambigua          : {'Si' if is_ambiguous(grammar) else 'No detectada'}")


if __name__ == "__main__":
    main()
