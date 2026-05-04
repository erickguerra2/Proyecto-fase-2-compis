# Transiciones del AFD

TRANSITIONS: dict = {}

TRANSITIONS[0] = {
    '\t': 1,
    ' ': 1,
    '+': 2,
    '0': 3,
    '1': 3,
    '2': 3,
    '3': 3,
    '4': 3,
    '5': 3,
    '6': 3,
    '7': 3,
    '8': 3,
    '9': 3,
    'A': 4,
    'B': 4,
    'C': 4,
    'D': 4,
    'E': 4,
    'F': 4,
    'G': 4,
    'H': 4,
    'I': 4,
    'J': 4,
    'K': 4,
    'L': 4,
    'M': 4,
    'N': 4,
    'O': 4,
    'P': 4,
    'Q': 4,
    'R': 4,
    'S': 4,
    'T': 4,
    'U': 4,
    'V': 4,
    'W': 4,
    'X': 4,
    'Y': 4,
    'Z': 4,
    'a': 4,
    'b': 4,
    'c': 4,
    'd': 4,
    'e': 4,
    'f': 4,
    'g': 4,
    'h': 4,
    'i': 4,
    'j': 4,
    'k': 4,
    'l': 4,
    'm': 4,
    'n': 4,
    'o': 4,
    'p': 4,
    'q': 4,
    'r': 4,
    's': 4,
    't': 4,
    'u': 4,
    'v': 4,
    'w': 4,
    'x': 4,
    'y': 4,
    'z': 4,
}
TRANSITIONS[1] = {
    '\t': 1,
    ' ': 1,
}
TRANSITIONS[2] = {}
TRANSITIONS[3] = {
    '0': 3,
    '1': 3,
    '2': 3,
    '3': 3,
    '4': 3,
    '5': 3,
    '6': 3,
    '7': 3,
    '8': 3,
    '9': 3,
}
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
    'A': 4,
    'B': 4,
    'C': 4,
    'D': 4,
    'E': 4,
    'F': 4,
    'G': 4,
    'H': 4,
    'I': 4,
    'J': 4,
    'K': 4,
    'L': 4,
    'M': 4,
    'N': 4,
    'O': 4,
    'P': 4,
    'Q': 4,
    'R': 4,
    'S': 4,
    'T': 4,
    'U': 4,
    'V': 4,
    'W': 4,
    'X': 4,
    'Y': 4,
    'Z': 4,
    'a': 4,
    'b': 4,
    'c': 4,
    'd': 4,
    'e': 4,
    'f': 4,
    'g': 4,
    'h': 4,
    'i': 4,
    'j': 4,
    'k': 4,
    'l': 4,
    'm': 4,
    'n': 4,
    'o': 4,
    'p': 4,
    'q': 4,
    'r': 4,
    's': 4,
    't': 4,
    'u': 4,
    'v': 4,
    'w': 4,
    'x': 4,
    'y': 4,
    'z': 4,
}

# Estados de aceptación
ACCEPT: dict = {1: 'WS', 2: 'PLUS', 3: 'NUM', 4: 'ID'}

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
    if tok == 'ID':
        return ID
        return lxm
    if tok == 'PLUS':
        return PLUS
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