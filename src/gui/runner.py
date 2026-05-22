"""Ejecuta el pipeline completo y retorna resultados estructurados para la GUI."""

from __future__ import annotations
import os, sys, io, subprocess, importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.cfg_grammar    import Grammar
from src.yapar_parser   import parse_yapar, YAParError
from src.error_recovery import report_fix_production_issues
from src.first_follow   import report_first_follow
from src.ambiguity      import detect_ambiguity, full_chain_analysis, fix_ambiguity

from src.lr.lr0   import build_lr0, report_lr0, report_augmented_grammar, report_gotos
from src.lr.lr_table import LRTable

from src.slr1.slr1  import build_slr1_table, SLR1Parser, SLR1ParseError
from src.lalr.lalr  import build_lalr_table, LALRParser, LALRParseError, report_lalr_states

from src.ll1.left_recursion import has_left_recursion, eliminate_left_recursion
from src.ll1.factorization  import needs_factorization, left_factor
from src.ll1.ll1_table      import build_ll1_table, print_ll1_table, LL1Parser, LL1ParseError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture(fn, *args, **kwargs) -> str:
    """Captura stdout de una funcion en un string."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _table_str(table, terminals, nonterminals) -> str:
    """Tabla ACTION/GOTO con anchos de columna dinamicos."""
    terms = sorted(terminals)
    nts   = sorted(nonterminals)
    n     = table.n_states

    # Ancho minimo = largo del header, maximo = largo del contenido mas largo
    def col_w(sym, is_action: bool) -> int:
        if is_action:
            vals = [str(table.action.get((s, sym), '')) for s in range(n)]
        else:
            vals = [str(table.goto_t.get((s, sym), '')) for s in range(n)]
        return max(len(sym), max((len(v) for v in vals), default=0)) + 2

    tw = {t: col_w(t, True)  for t in terms}
    gw = {nt: col_w(nt, False) for nt in nts}
    sw = max(6, len(str(n))) + 2

    sep   = "─"
    lines = []

    # Header
    hdr = f"  {'Estado':<{sw}} │ "
    hdr += " │ ".join(f"{t:^{tw[t]}}" for t in terms)
    if nts:
        hdr += " ║ " + " │ ".join(f"{nt:^{gw[nt]}}" for nt in nts)
    lines.append(hdr)
    lines.append("  " + sep * len(hdr))

    # Filas
    for s in range(n):
        row = f"  {s:<{sw}} │ "
        row += " │ ".join(
            f"{str(table.action.get((s, t), '')):<{tw[t]}}" for t in terms
        )
        if nts:
            row += " ║ " + " │ ".join(
                f"{str(table.goto_t.get((s, nt), '')):<{gw[nt]}}" for nt in nts
            )
        lines.append(row)

    return "\n".join(lines)


def _generate_lexer(yal_path: str):
    """Genera lexer desde .yal. Retorna (path, error)."""
    base = os.path.basename(yal_path)
    for ext in (".yalex", ".yal"):
        base = base.replace(ext, "")
    out_path = os.path.join("output", base + "_generated.py")
    os.makedirs("output", exist_ok=True)
    r = subprocess.run(
        [sys.executable, "src/lexer/generator.py", yal_path, "-o", out_path],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        return None, r.stderr.strip()
    return out_path, None


def _load_lexer(path: str):
    abs_path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location("_lexer_gui", abs_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(yal_path: str, yapar_path: str, source: str,
                 parser_mode: str) -> dict:
    """
    Ejecuta el pipeline y retorna un dict con:
      error, tokens, grammar_text, productions_count, nonterminals_count,
      first_follow, states_text, gotos_text, table_text, conflicts,
      ambiguity_warnings, ambiguity_text, parse_tree, recovery_log, accepted
    """
    res = dict(
        error=None, tokens=[], grammar_text="",
        productions_count=0, nonterminals_count=0,
        first_follow="", states_text="", gotos_text="",
        table_text="", conflicts=[], ambiguity_warnings=[],
        ambiguity_text="", parse_tree=None,
        recovery_log=[], accepted=False,
    )

    # 1. Lexer
    lexer_path, err = _generate_lexer(yal_path)
    if err:
        res['error'] = f"Error generando lexer:\n{err}"; return res
    try:
        lexer_mod = _load_lexer(lexer_path)
    except Exception as e:
        res['error'] = f"Error cargando lexer: {e}"; return res

    # 2. Gramatica
    try:
        grammar, ignored = parse_yapar(yapar_path)
    except YAParError as e:
        res['error'] = f"Error en .yapar: {e}"; return res

    # 3. Tokenizar
    try:
        raw = lexer_mod.yylex(source)
        tokens_raw = [(t[0], t[1], t[2] if len(t) > 2 else None,
                       t[3] if len(t) > 3 else None) for t in raw]
    except Exception as e:
        res['error'] = f"Error lexico: {e}"; return res

    skip   = {"WS", "WHITESPACE", "NEWLINE"} | ignored
    tokens = [t for t in tokens_raw if t[0] not in skip]
    res['tokens'] = tokens

    # Detectar ambiguedad en gramatica original antes del preprocesado
    res['ambiguity_warnings'] = detect_ambiguity(grammar)

    # 4. Preprocesar gramatica — SLR1 y LALR solamente, LL1 lo maneja internamente
    if parser_mode != "ll1":
        try:
            grammar, _, _ = report_fix_production_issues(grammar)
        except TypeError:
            grammar, _ = report_fix_production_issues(grammar)

    # 5. Info de la gramatica
    lines = []
    for nt, prods in grammar.productions.items():
        for p in prods:
            body = " ".join(p) if p else "ε"
            lines.append(f"  {nt} -> {body}")
    res['grammar_text']       = "\n".join(lines)
    res['productions_count']  = sum(len(v) for v in grammar.productions.values())
    res['nonterminals_count'] = len(grammar.nonterminals)

    # 7. Parser especifico
    if parser_mode == "ll1":
        _run_ll1(grammar, tokens, res)
    elif parser_mode == "slr1":
        _run_slr1(grammar, tokens, res)
    else:
        _run_lalr(grammar, tokens, res)

    return res


# ---------------------------------------------------------------------------
# Runners por modo
# ---------------------------------------------------------------------------

def _run_ll1(grammar: Grammar, tokens: list, res: dict):
    n_orig = len(res.get('ambiguity_warnings', []))

    # 1. Pre-analisis: mostrar los dos arboles de ambiguedad y corregir gramatica
    if n_orig > 0:
        grammar, pre_text, _ = full_chain_analysis(
            grammar, tokens, None, "LL(1)", fix=True, pre_parse=True)
    else:
        pre_text = ""

    # 2. Transformaciones especificas LL1 sobre gramatica ya corregida
    if has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
    if needs_factorization(grammar):
        grammar = left_factor(grammar)

    res['first_follow'] = report_first_follow(grammar)
    res['states_text']  = "(LL(1) no construye automata LR)"
    res['gotos_text']   = ""

    _, conflicts = build_ll1_table(grammar)
    res['conflicts'] = conflicts
    if conflicts:
        res['error'] = f"La gramatica no es LL(1): {len(conflicts)} conflicto(s)"
        res['ambiguity_text'] = pre_text
        return

    res['table_text'] = _capture(print_ll1_table, grammar)

    try:
        parser = LL1Parser(grammar, tokens)
        parser.parse()
        res['accepted']     = True
        res['parse_tree']   = getattr(parser, 'parse_tree', None)
        res['recovery_log'] = getattr(parser, 'recovery_log', [])
    except LL1ParseError as e:
        res['error'] = str(e)

    # 3. Post-analisis: arbol final con gramatica corregida
    _, post_text, _ = full_chain_analysis(
        grammar, tokens, res['parse_tree'], "LL(1)", fix=False)

    res['ambiguity_text'] = (pre_text + "\n\n---\n\n" + post_text) if pre_text else post_text


def _run_slr1(grammar: Grammar, tokens: list, res: dict):
    res['first_follow'] = report_first_follow(grammar)
    res['states_text']  = (report_augmented_grammar(grammar)
                           + "\n\n" + report_lr0(build_lr0(grammar)[0]))
    res['gotos_text']   = report_gotos(build_lr0(grammar)[0])

    table, _, _ = build_slr1_table(grammar)
    res['conflicts']  = table.conflicts
    res['table_text'] = _table_str(table,
                                   grammar.terminals | {"$"},
                                   grammar.nonterminals)

    try:
        parser = SLR1Parser(grammar, tokens)
        parser.parse()
        res['accepted']     = True
        res['parse_tree']   = getattr(parser, 'parse_tree', None)
        res['recovery_log'] = getattr(parser, 'recovery_log', [])
    except SLR1ParseError as e:
        res['error'] = str(e)

    _, amb, _ = full_chain_analysis(
        grammar, tokens, res['parse_tree'], "SLR(1)", fix=False)
    res['ambiguity_text'] = amb


def _run_lalr(grammar: Grammar, tokens: list, res: dict):
    res['first_follow'] = report_first_follow(grammar)

    table, states, _ = build_lalr_table(grammar)
    res['states_text'] = (report_augmented_grammar(grammar)
                          + "\n\n" + report_lalr_states(states))
    res['gotos_text']  = report_gotos(states)
    res['conflicts']   = table.conflicts
    res['table_text']  = _table_str(table,
                                    grammar.terminals | {"$"},
                                    grammar.nonterminals)

    try:
        parser = LALRParser(grammar, tokens)
        parser.parse()
        res['accepted']     = True
        res['parse_tree']   = getattr(parser, 'parse_tree', None)
        res['recovery_log'] = getattr(parser, 'recovery_log', [])
    except LALRParseError as e:
        res['error'] = str(e)

    _, amb, _ = full_chain_analysis(
        grammar, tokens, res['parse_tree'], "LALR", fix=False)
    res['ambiguity_text'] = amb
