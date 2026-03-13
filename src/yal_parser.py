"""
Lee y parsea archivos .yal para extraer definiciones y reglas.
"""
import re


class YalRule:
    def __init__(self, pattern: str, action: str):
        self.pattern = pattern
        self.action  = action
    def __repr__(self):
        return f"YalRule(pattern={self.pattern!r}, action={self.action!r})"


class YalSpec:
    def __init__(self):
        self.header:      str  = ""
        self.definitions: dict = {}
        self.entrypoint:  str  = ""
        self.rules:       list = []
        self.trailer:     str  = ""
    def __repr__(self):
        return (f"YalSpec(header={self.header!r}, defs={self.definitions}, "
                f"entrypoint={self.entrypoint!r}, rules={self.rules})")


# funciones internas para leer y limpiar el texto del .yal

def _remove_comments(text: str) -> str:
    # elimina los comentarios (* ... *) del texto
    result, i = [], 0
    while i < len(text):
        if text[i:i+2] == "(*":
            end = text.find("*)", i + 2)
            if end == -1:
                raise SyntaxError("Comentario no cerrado: falta *)")
            i = end + 2
        else:
            result.append(text[i]); i += 1
    return "".join(result)


def _extract_braces(text: str, start: int):
    # extrae el contenido de un bloque con soporte de anidamiento
    assert text[start] == "{"
    depth, content, i = 0, [], start
    while i < len(text):
        ch = text[i]
        if   ch == "{": depth += 1; (content.append(ch) if depth > 1 else None)
        elif ch == "}":
            depth -= 1
            if depth == 0: return "".join(content).strip(), i + 1
            content.append(ch)
        else: content.append(ch)
        i += 1
    raise SyntaxError("Bloque { } no cerrado")


def _find_action_brace(text: str, start: int) -> int:
    # busca la llave de acción saltando cadenas, chars y conjuntos
    i = start
    while i < len(text):
        ch = text[i]

        # cadena entre comillas dobles, hay que saltarla completa
        if ch == '"':
            i += 1
            while i < len(text) and text[i] != '"':
                if text[i] == '\\': i += 1   # saltar escape
                i += 1
            i += 1  # cierra "
            continue

        # carácter entre comillas simples, puede tener escape
        if ch == "'":
            i += 1
            if i < len(text) and text[i] == '\\':
                i += 2   # saltar escape + char
            elif i < len(text):
                i += 1   # saltar char
            if i < len(text) and text[i] == "'":
                i += 1   # cierra '
            continue

        # conjunto, puede tener chars con comillas adentro
        if ch == '[':
            i += 1
            if i < len(text) and text[i] == '^': i += 1
            while i < len(text) and text[i] != ']':
                if text[i] == "'":
                    i += 1
                    if i < len(text) and text[i] == '\\': i += 2
                    elif i < len(text): i += 1
                    if i < len(text) and text[i] == "'": i += 1
                else:
                    i += 1
            i += 1  # cierra ]
            continue

        # esta es la llave de acción que buscamos
        if ch == '{':
            return i

        i += 1
    return -1


# lee cada alternativa del bloque rule y la convierte en un YalRule

def _parse_alternatives(text: str) -> list:
    rules = []
    i     = 0
    text  = text.strip()

    while i < len(text):
        # salta espacios y el separador entre alternativas
        while i < len(text) and text[i] in " \t\n\r": i += 1
        if i >= len(text): break
        if text[i] == "|": i += 1; continue

        # busca la llave que abre la acción sin confundirse con las del patrón
        brace_pos = _find_action_brace(text, i)
        if brace_pos == -1: break

        pattern = text[i:brace_pos].strip()
        action, end_pos = _extract_braces(text, brace_pos)

        if pattern:
            rules.append(YalRule(pattern, action))

        i = end_pos

    return rules


# parser principal del archivo .yal

def parse_yal(source: str) -> YalSpec:
    spec = YalSpec()
    text = _remove_comments(source).lstrip()

    # si hay un bloque al inicio es el header de código
    if text.startswith("{"):
        spec.header, pos = _extract_braces(text, 0)
        text = text[pos:].lstrip()

    # separa las definiciones let de las reglas
    remaining, in_rule = [], False
    for line in text.splitlines(keepends=True):
        s = line.strip()
        if re.match(r'^rule\b', s, re.IGNORECASE): in_rule = True
        if in_rule:
            remaining.append(line); continue
        m = re.match(r'^let\s+([A-Za-z_]\w*)\s*=\s*(.+)', s)
        if m:
            spec.definitions[m.group(1)] = m.group(2).strip()
        else:
            remaining.append(line)

    rule_text = "".join(remaining).strip()
    if not rule_text: return spec

    # busca la línea rule entrypoint para saber dónde empiezan las reglas
    m = re.match(r'rule\s+([A-Za-z_]\w*)(\s+\w+)?\s*=', rule_text, re.IGNORECASE)
    if not m: raise SyntaxError("No se encontró 'rule entrypoint ='")
    spec.entrypoint = m.group(1)
    rest = rule_text[m.end():].lstrip()
    if rest.startswith("|"): rest = rest[1:].lstrip()

    spec.rules = _parse_alternatives(rest)
    return spec


def parse_yal_file(filepath: str) -> YalSpec:
    # lee el archivo y lo parsea
    with open(filepath, "r", encoding="utf-8") as f:
        return parse_yal(f.read())
