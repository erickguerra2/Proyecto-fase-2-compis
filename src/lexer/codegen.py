"""
Generación de código Python del analizador léxico.
Produce un archivo .py que implementa la función yylex().
"""
from dfa import DFAState


def generate_lexer(
    dfa_start: DFAState,
    all_states: list,
    rules_actions: list,       # lista de pares token y acción
    header_code:   str = "",
    trailer_code:  str = "",
    output_path:   str = "lexer_generated.py"
):
    lines = []

    alphabet = set()
    for s in all_states:
        alphabet.update(s.transitions.keys())

    lines += [
        "# Transiciones del AFD",
        "",
        "TRANSITIONS: dict = {}",
        "",
    ]

    for s in sorted(all_states, key=lambda x: x.id):
        if not s.transitions:
            lines.append(f"TRANSITIONS[{s.id}] = {{}}")
            continue
        lines.append(f"TRANSITIONS[{s.id}] = {{")
        for sym, tgt in sorted(s.transitions.items(),
                                key=lambda kv: str(kv[0])):
            if isinstance(sym, frozenset):
                for c in sorted(sym):
                    safe = repr(c)
                    lines.append(f"    {safe}: {tgt.id},")
            else:
                lines.append(f"    {repr(sym)}: {tgt.id},")
        lines.append("}")
    lines.append("")

    accept_map = {}
    for s in all_states:
        if s.is_accept and s.token_name:
            accept_map[s.id] = s.token_name

    lines += [
        "# Estados de aceptación",
        f"ACCEPT: dict = {repr(accept_map)}",
        "",
        f"START_STATE: int = {dfa_start.id}",
        "",
    ]

    lines += [
        "",
        "class LexError(Exception): pass",
        "",
        "",
        "def yylex(text: str):",
        '    """',
        '    Tokeniza text y retorna lista de (token, lexema, linea, columna).',
        '    Lanza LexError si encuentra un caracter no reconocido.',
        '    """',
        "    pos  = 0",
        "    line = 1",
        "    col  = 1",
        "    tokens = []",
        "    while pos < len(text):",
        "        state     = START_STATE",
        "        last_acc  = None",
        "        i         = pos",
        "        tok_line, tok_col = line, col",
        "        while i < len(text):",
        "            ch = text[i]",
        "            nxt = TRANSITIONS.get(state, {}).get(ch, -1)",
        "            if nxt == -1:",
        "                break",
        "            state = nxt",
        "            i += 1",
        "            if state in ACCEPT:",
        "                last_acc = (ACCEPT[state], i)",
        "        if last_acc is None:",
        "            raise LexError(f'Error lexico en linea {line}, columna {col}: {repr(text[pos])}')",
        "        tok, end = last_acc",
        "        lexeme = text[pos:end]",
        "        tokens.append((tok, lexeme, tok_line, tok_col))",
        "        for ch in lexeme:",
        "            if ch == '\\n':",
        "                line += 1",
        "                col   = 1",
        "            else:",
        "                col  += 1",
        "        pos = end",
        "    return tokens",
        "",
        "",
        "",
        "def apply_actions(tokens: list):",
        '    """Aplica las acciones definidas en el .yal a cada token."""',
        "    results = []",
        "    for tok, lexeme in tokens:",
        "        lxm = lexeme",
        "        result = _dispatch(tok, lxm)",
        "        if result is not None:",
        "            results.append(result)",
        "    return results",
        "",
        "",
        "def _dispatch(tok: str, lxm: str):",
    ]

    for tok_name, action in rules_actions:
        safe_name = repr(tok_name)
        action_lines = action.strip().splitlines()
        lines.append(f"    if tok == {safe_name}:")
        for al in action_lines:
            lines.append(f"        {al.strip()}")
        lines.append(f"        return lxm")
    lines += [
        "    return (tok, lxm)",
        "",
    ]

    lines += [
        "",
        "if __name__ == '__main__':",
        "    import sys",
        "    if len(sys.argv) < 2:",
        "        print('Uso: python lexer_generated.py <archivo>')",
        "        sys.exit(1)",
        "    with open(sys.argv[1]) as f:",
        "        src = f.read()",
        "    try:",
        "        toks = yylex(src)",
        "        for t in toks:",
        "            print(t)",
        "    except LexError as e:",
        "        print('ERROR:', e)",
    ]

    if trailer_code:
        lines += ["", trailer_code]

    code = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)
    print(f"[codegen] Analizador léxico generado en: {output_path}")
    return code
