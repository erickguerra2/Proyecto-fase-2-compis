"""
Convierte expresiones regulares a postfix para el AFN.
"""

CHAR   = "CHAR"
CONCAT = "·"
UNION  = "|"
DIFF   = "#"
STAR   = "*"
PLUS   = "+"
OPT    = "?"
LPAREN = "("
RPAREN = ")"
ANY    = "."

PREC = {"|": 1, "·": 2, "#": 3, "*": 4, "+": 4, "?": 4}
UNARY_POSTFIX = {"*", "+", "?"}
BINARY_OPS    = {"|", "·", "#"}


def tokenize(expr: str) -> list:
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]

        if ch in " \t\n\r":
            i += 1; continue

        if ch == "[":
            charset, i = _parse_charset(expr, i)
            tokens.append(("SET", charset))
            continue

        if ch == '"':
            s, i = _parse_string(expr, i)
            for c in s:
                tokens.append(("CHAR", c))
            continue

        if ch == "'":
            c, i = _parse_char(expr, i)
            tokens.append(("CHAR", c))
            continue

        if expr[i:i+3] == "eof":
            tokens.append(("EOF",))
            i += 3; continue

        if ch == "_":
            tokens.append(("ANY",))
            i += 1; continue

        if ch in "|()*+?#":
            tokens.append(("OP", ch))
            i += 1; continue

        tokens.append(("CHAR", ch))
        i += 1

    return tokens


def _parse_charset(expr: str, start: int):
    i = start + 1
    negate = False
    chars  = set()

    if i < len(expr) and expr[i] == "^":
        negate = True; i += 1

    while i < len(expr) and expr[i] != "]":
        if expr[i] == "'":
            c, i = _parse_char(expr, i)
        else:
            c = expr[i]; i += 1

        if i < len(expr) - 1 and expr[i] == "-" and expr[i+1] != "]":
            i += 1  # salta el '-'
            if expr[i] == "'":
                c2, i = _parse_char(expr, i)
            else:
                c2 = expr[i]; i += 1
            for code in range(ord(c), ord(c2) + 1):
                chars.add(chr(code))
        else:
            chars.add(c)

    i += 1  # consume ']'

    if negate:
        all_chars = {chr(k) for k in range(32, 127)}
        chars = all_chars - chars

    return frozenset(chars), i


def _parse_char(expr: str, start: int):
    i = start + 1  # salta la comilla de apertura
    if i >= len(expr):
        raise SyntaxError("Carácter sin cerrar")
    if expr[i] == "\\":
        i += 1
        escape = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'"}
        c = escape.get(expr[i], expr[i])
        i += 1
    else:
        c = expr[i]; i += 1
    if i < len(expr) and expr[i] == "'":
        i += 1
    return c, i


def _parse_string(expr: str, start: int):
    i = start + 1
    chars = []
    while i < len(expr) and expr[i] != '"':
        if expr[i] == "\\":
            i += 1
            escape = {"n": "\n", "t": "\t", "r": "\r"}
            chars.append(escape.get(expr[i], expr[i]))
        else:
            chars.append(expr[i])
        i += 1
    i += 1
    return "".join(chars), i


def insert_concat(tokens: list) -> list:
    result = []
    atom_or_close = {CHAR, "SET", "ANY", "EOF"}

    def is_left(tok):
        t = tok[0]
        return t in atom_or_close or (t == "OP" and tok[1] in UNARY_POSTFIX | {")"})

    def is_right(tok):
        t = tok[0]
        return t in atom_or_close or (t == "OP" and tok[1] == "(")

    for i, tok in enumerate(tokens):
        result.append(tok)
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if is_left(tok) and is_right(nxt):
                result.append(("OP", "·"))

    return result


def to_postfix(tokens: list) -> list:
    output = []
    stack  = []

    for tok in tokens:
        kind = tok[0]

        if kind in ("CHAR", "SET", "ANY", "EOF"):
            output.append(tok)

        elif kind == "OP":
            op = tok[1]
            if op == "(":
                stack.append(tok)
            elif op == ")":
                while stack and stack[-1] != ("OP", "("):
                    output.append(stack.pop())
                if not stack:
                    raise SyntaxError("Paréntesis no balanceados")
                stack.pop()
            elif op in UNARY_POSTFIX:
                while (stack and stack[-1] != ("OP", "(") and
                       stack[-1][0] == "OP" and
                       PREC.get(stack[-1][1], 0) >= PREC[op]):
                    output.append(stack.pop())
                stack.append(tok)
            elif op in BINARY_OPS:
                while (stack and stack[-1] != ("OP", "(") and
                       stack[-1][0] == "OP" and
                       PREC.get(stack[-1][1], 0) >= PREC[op]):
                    output.append(stack.pop())
                stack.append(tok)

    while stack:
        top = stack.pop()
        if top == ("OP", "("):
            raise SyntaxError("Paréntesis no balanceados")
        output.append(top)

    return output


def regexp_to_postfix(expr: str) -> list:
    tokens   = tokenize(expr)
    tokens   = insert_concat(tokens)
    postfix  = to_postfix(tokens)
    return postfix
