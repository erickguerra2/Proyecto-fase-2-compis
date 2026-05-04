# Transiciones del AFD

TRANSITIONS: dict = {}

TRANSITIONS[0] = {
    '\t': 1,
    ' ': 1,
    '+': 2,
    '-': 3,
    '0': 4,
    '1': 4,
    '2': 4,
    '3': 4,
    '4': 4,
    '5': 4,
    '6': 4,
    '7': 4,
    '8': 4,
    '9': 4,
}
TRANSITIONS[1] = {
    '\t': 1,
    ' ': 1,
}
TRANSITIONS[2] = {}
TRANSITIONS[3] = {}
TRANSITIONS[4] = {
    '0': 4,
    '1': 4,
    '2': 4,
    '3': 4,
    '4': 4,
    '5': 4,
    '6': 4,
    '7': 4,
    '8': 4,
    '9': 4,
}

# Estados de aceptación
ACCEPT: dict = {1: 'WS', 2: 'PLUS', 3: 'MINUS', 4: 'NUM'}

START_STATE: int = 0


class LexError(Exception): pass


def yylex(text: str):
    """
    Tokeniza 'text' y genera tuplas token y lexema.
    Lanza LexError si encuentra un carácter no reconocido.
    """
    pos = 0
    tokens = []
    while pos < len(text):
        state     = START_STATE
        last_acc  = None     # token y posición final
        i         = pos
        while i < len(text):
            ch = text[i]
            nxt = TRANSITIONS.get(state, {}).get(ch, -1)
            if nxt == -1:
                break
            state = nxt
            i += 1
            if state in ACCEPT:
                last_acc = (ACCEPT[state], i)
        if last_acc is None:
            raise LexError(f'Error léxico en posición {pos}: '
                           f'{repr(text[pos])}')
        tok, end = last_acc
        lexeme = text[pos:end]
        tokens.append((tok, lexeme))
        pos = end
    return tokens



def apply_actions(tokens: list):
    """Aplica las acciones definidas en el .yal a cada token."""
    results = []
    for tok, lexeme in tokens:
        lxm = lexeme   # variable disponible en acciones
        result = _dispatch(tok, lxm)
        if result is not None:
            results.append(result)
    return results


def _dispatch(tok: str, lxm: str):
    if tok == 'NUM':
        return NUM
        return lxm
    if tok == 'PLUS':
        return PLUS
        return lxm
    if tok == 'MINUS':
        return MINUS
        return lxm
    if tok == 'WS':
        return WS
        return lxm
    return (tok, lxm)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Uso: python lexer_generated.py <archivo>')
        sys.exit(1)
    with open(sys.argv[1]) as f:
        src = f.read()
    try:
        toks = yylex(src)
        for t in toks:
            print(t)
    except LexError as e:
        print('ERROR:', e)