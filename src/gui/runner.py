"""Corre el pipeline completo y devuelve los resultados para la GUI."""

from __future__ import annotations
import os, sys, io, subprocess, importlib.util

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.cfg_grammar    import Grammar
from src.yapar_parser   import parse_yapar, YAParError
from src.error_recovery import report_fix_production_issues
from src.first_follow   import report_first_follow, compute_first, compute_follow, EOF_SYM, EPSILON
from src.ambiguity      import detect_ambiguity, full_chain_analysis

from src.lr.lr0      import build_lr0, report_lr0, report_augmented_grammar, report_gotos
from src.lr.lr_table import SHIFT, REDUCE, ACCEPT

from src.slr1.slr1  import build_slr1_table, SLR1Parser, SLR1ParseError
from src.lalr.lalr  import build_lalr_table, LALRParser, LALRParseError, report_lalr_states

from src.ll1.left_recursion import has_left_recursion, eliminate_left_recursion
from src.ll1.factorization  import needs_factorization, left_factor
from src.ll1.ll1_table      import build_ll1_table, LL1Parser, LL1ParseError


# helpers

def _capture(fn, *args, **kwargs) -> str:
    """Captura lo que imprime una funcion y lo devuelve como string."""
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*args, **kwargs)
    finally:
        sys.stdout = old
    return buf.getvalue()


def _table_str_lr(table, terminals, nonterminals) -> str:
    """Formatea la tabla ACTION/GOTO para mostrarla en la GUI."""
    terms = sorted(terminals)
    nts   = sorted(nonterminals)
    n     = table.n_states

    def col_w(sym, is_action: bool) -> int:
        if is_action:
            vals = [str(table.action.get((s, sym), '')) for s in range(n)]
        else:
            vals = [str(table.goto_t.get((s, sym), '')) for s in range(n)]
        return max(len(sym), max((len(v) for v in vals), default=0)) + 2

    tw = {t: col_w(t, True)  for t in terms}
    gw = {nt: col_w(nt, False) for nt in nts}
    sw = max(6, len(str(n))) + 2
    sep = "─"
    lines = []

    hdr = f"  {'Estado':<{sw}} │ "
    hdr += " │ ".join(f"{t:^{tw[t]}}" for t in terms)
    if nts:
        hdr += " ║ " + " │ ".join(f"{nt:^{gw[nt]}}" for nt in nts)
    lines.append(hdr)
    lines.append("  " + sep * len(hdr))

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


def _table_str_ll1(grammar: Grammar, table=None, conflicts=None) -> str:
    """Tabla M[NT, terminal] de LL(1) con anchos de columna dinamicos."""
    if table is None or conflicts is None:
        table, conflicts = build_ll1_table(grammar)
    all_terms = sorted({t for (_, t) in table})
    nts       = sorted(grammar.nonterminals)

    def cell(nt, t):
        prods = table.get((nt, t), [])
        if not prods:          return ""
        if len(prods) > 1:     return "!!CONFLICTO!!"
        body = " ".join(prods[0]) if prods[0] else "ε"
        return f"{nt}->{body}"

    # Anchos dinamicos
    tw = {}
    for t in all_terms:
        vals = [cell(nt, t) for nt in nts]
        tw[t] = max(len(t), max((len(v) for v in vals), default=0)) + 2
    nt_w = max((len(nt) for nt in nts), default=4) + 2

    sep   = "─"
    lines = []
    status = "Sin conflictos — ES LL(1)" if not conflicts else f"{len(conflicts)} conflicto(s) — NO es LL(1)"
    lines.append(f"Tabla de Parsing LL(1)  [{status}]")
    lines.append("")

    hdr = f"  {'NT':<{nt_w}} │ " + " │ ".join(f"{t:^{tw[t]}}" for t in all_terms)
    lines.append(hdr)
    lines.append("  " + sep * len(hdr))

    for nt in nts:
        row = f"  {nt:<{nt_w}} │ "
        row += " │ ".join(f"{cell(nt, t):<{tw[t]}}" for t in all_terms)
        lines.append(row)

    if conflicts:
        lines.append("\nConflictos:")
        for c in conflicts:
            lines.append(str(c))

    return "\n".join(lines)


def _build_lr_trace(table, tokens: list) -> list:
    """Simula parsing LR. Retorna pasos (pila_estados, pila_simbolos, entrada, accion)."""
    input_tokens = tokens + [(EOF_SYM, EOF_SYM, None, None)]
    pos       = 0
    stack     = [0]
    sym_stack = []      # pila de simbolos paralela, mismo tamaño que stack-1
    steps     = []

    def tok_label(t):
        return t[1] if t[1] and t[1] != t[0] else t[0]

    while True:
        state             = stack[-1]
        tok               = input_tokens[pos]
        cur_type, cur_lex = tok[0], tok[1]

        action = (table.get_action(state, cur_type) or
                  table.get_action(state, cur_lex))

        pila_str  = " ".join(str(s) for s in stack)
        simb_str  = " ".join(sym_stack) if sym_stack else "-"
        input_str = " ".join(tok_label(t) for t in input_tokens[pos:])

        if action is None:
            accion_str = f"ERROR: token inesperado '{cur_lex}'"
        elif action.kind == SHIFT:
            accion_str = f"S{action.state}"
        elif action.kind == REDUCE:
            body       = " ".join(action.prod) if action.prod else "ε"
            accion_str = f"r: {action.nt} -> {body}"
        else:
            accion_str = "accept"

        steps.append((pila_str, simb_str, input_str, accion_str))

        if action is None or action.kind == ACCEPT:
            break

        if action.kind == SHIFT:
            sym_stack.append(tok_label(tok))
            stack.append(action.state)
            pos += 1

        elif action.kind == REDUCE:
            n = len(action.prod)
            for _ in range(n):
                stack.pop()
                sym_stack.pop()
            goto = table.get_goto(stack[-1], action.nt)
            if goto is None:
                steps.append((
                    " ".join(str(s) for s in stack),
                    " ".join(sym_stack) or "-",
                    input_str,
                    f"ERROR: GOTO indefinido para ({stack[-1]}, {action.nt})"
                ))
                break
            sym_stack.append(action.nt)
            stack.append(goto)

    return steps


def _build_ll1_trace(grammar: Grammar, tokens: list) -> list:
    """Simula parsing LL(1). Retorna pasos (pila_simbolos, entrada, accion)."""
    from src.ll1.ll1_table import build_ll1_table
    table, _ = build_ll1_table(grammar)
    first     = compute_first(grammar)
    follow    = compute_follow(grammar, first)

    input_tokens = tokens + [(EOF_SYM, EOF_SYM, None, None)]
    pos   = 0
    stack = [EOF_SYM, grammar.start]
    steps = []
    MAX_STEPS = 1000

    def tok_label(t):
        return t[1] if t[1] and t[1] != t[0] else t[0]

    def match(sym, typ, lex):
        return sym == typ or sym == lex

    while stack and len(steps) < MAX_STEPS:
        top      = stack[-1]
        tok      = input_tokens[pos] if pos < len(input_tokens) else (EOF_SYM, EOF_SYM, None, None)
        cur_type = tok[0]
        cur_lex  = tok[1]

        pila_str  = " ".join(reversed(stack))   # muestra con el tope a la derecha
        input_str = " ".join(tok_label(t) for t in input_tokens[pos:])

        if top == EOF_SYM:
            if cur_type == EOF_SYM:
                steps.append((pila_str, input_str, "accept"))
            else:
                steps.append((pila_str, input_str, f"ERROR: entrada no consumida '{cur_lex}'"))
            break

        if top in grammar.terminals or top not in grammar.productions:
            if match(top, cur_type, cur_lex):
                steps.append((pila_str, input_str, f"match '{cur_lex}'"))
                stack.pop()
                pos += 1
            else:
                steps.append((pila_str, input_str, f"ERROR: esperaba '{top}', encontro '{cur_lex}'"))
                stack.pop()   # recovery: descartar el tope
            continue

        prod_list = table.get((top, cur_type)) or table.get((top, cur_lex))
        if not prod_list:
            # recovery: si cur esta en FOLLOW(top), expandir epsilon
            if cur_type in follow.get(top, set()) or cur_lex in follow.get(top, set()):
                steps.append((pila_str, input_str, f"expandir {top} -> ε  (recovery por FOLLOW)"))
                stack.pop()
            else:
                steps.append((pila_str, input_str, f"ERROR: no hay produccion M[{top}, '{cur_lex}']"))
                if pos < len(input_tokens) - 1:  # no avanzar mas alla del EOF
                    pos += 1
                else:
                    break
            continue

        prod = prod_list[0]
        body = " ".join(prod) if prod else "ε"
        steps.append((pila_str, input_str, f"expandir {top} -> {body}"))
        stack.pop()
        for sym in reversed(prod):
            stack.append(sym)

    return steps


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
    res = dict(
        error=None, tokens=[], grammar_text="",
        productions_count=0, nonterminals_count=0,
        first_follow="", states_text="", gotos_text="",
        table_text="", conflicts=[], ambiguity_warnings=[],
        ambiguity_text="", parse_tree=None,
        recovery_log=[], accepted=False, trace=[],
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

    res['ambiguity_warnings'] = detect_ambiguity(grammar)

    # 4. Preprocesar gramatica (limpiar producciones duplicadas, etc.)
    grammar, _, _ = report_fix_production_issues(grammar)

    # 5. Info de la gramatica
    lines = []
    for nt, prods in grammar.productions.items():
        for p in prods:
            body = " ".join(p) if p else "ε"
            lines.append(f"  {nt} -> {body}")
    res['grammar_text']       = "\n".join(lines)
    res['productions_count']  = sum(len(v) for v in grammar.productions.values())
    res['nonterminals_count'] = len(grammar.nonterminals)

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
    if n_orig > 0:
        grammar, pre_text, _ = full_chain_analysis(
            grammar, tokens, None, "LL(1)", fix=True, pre_parse=True)
    else:
        pre_text = ""

    if has_left_recursion(grammar):
        grammar = eliminate_left_recursion(grammar)
    if needs_factorization(grammar):
        grammar = left_factor(grammar)

    # FIX H1: actualizar grammar_text con la gramatica ya transformada
    lines_t = []
    for nt, prods in grammar.productions.items():
        for p in prods:
            body = " ".join(p) if p else "ε"
            lines_t.append(f"  {nt} -> {body}")
    res['grammar_text']       = "\n".join(lines_t)
    res['productions_count']  = sum(len(v) for v in grammar.productions.values())
    res['nonterminals_count'] = len(grammar.nonterminals)

    res['first_follow'] = report_first_follow(grammar)
    res['states_text']  = "(LL(1) no construye automata LR — usa tabla predictiva)"
    res['gotos_text']   = ""

    # FIX H4: construir la tabla una sola vez y reutilizarla
    ll1_table, conflicts = build_ll1_table(grammar)
    res['conflicts']  = conflicts
    res['table_text'] = _table_str_ll1(grammar, ll1_table, conflicts)

    if conflicts:
        res['error'] = f"La gramatica no es LL(1): {len(conflicts)} conflicto(s)"
        res['ambiguity_text'] = pre_text
        return

    # Traza LL(1)
    res['trace'] = _build_ll1_trace(grammar, tokens)

    try:
        parser = LL1Parser(grammar, tokens)
        parser.parse()
        res['accepted']     = True
        res['parse_tree']   = getattr(parser, 'parse_tree', None)
        res['recovery_log'] = getattr(parser, 'recovery_log', [])
    except LL1ParseError as e:
        res['error'] = str(e)
        res['ambiguity_text'] = pre_text
        return   # FIX H4: no llamar full_chain_analysis si el parse fallo

    # Post-analisis solo si el parse fue exitoso
    _, post_text, _ = full_chain_analysis(
        grammar, tokens, res['parse_tree'], "LL(1)", fix=False)
    res['ambiguity_text'] = (pre_text + "\n\n---\n\n" + post_text) if pre_text else post_text


def _run_slr1(grammar: Grammar, tokens: list, res: dict):
    res['first_follow'] = report_first_follow(grammar)

    # FIX C4: construir LR(0) una sola vez
    lr0_states, _ = build_lr0(grammar)
    res['states_text'] = report_augmented_grammar(grammar) + "\n\n" + report_lr0(lr0_states)
    res['gotos_text']  = report_gotos(lr0_states)

    table, _, _ = build_slr1_table(grammar)
    res['conflicts']  = table.conflicts
    res['table_text'] = _table_str_lr(table, grammar.terminals | {"$"}, grammar.nonterminals)
    res['trace']      = _build_lr_trace(table, tokens)

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

    # FIX C4: build_lalr_table una sola vez; pasar tabla al parser evita segunda construccion
    table, states, _ = build_lalr_table(grammar)
    res['states_text'] = report_augmented_grammar(grammar) + "\n\n" + report_lalr_states(states)
    res['gotos_text']  = report_gotos(states)
    res['conflicts']   = table.conflicts
    res['table_text']  = _table_str_lr(table, grammar.terminals | {"$"}, grammar.nonterminals)
    res['trace']       = _build_lr_trace(table, tokens)

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
