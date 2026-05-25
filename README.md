# Generador de Analizadores Sintácticos

Proyecto de la fase 2 del curso de Compiladores (UVG). Toma como entrada un archivo `.yal` (especificación léxica) y un archivo `.yapar` (gramática libre de contexto) y construye un analizador sintáctico completo con interfaz gráfica.

## Integrantes

- Erick Guerra
- José Fernando

---

## Descripción

El sistema integra el generador de lexers de la fase 1 con tres tipos de parsers:

- **LL(1)** — parser predictivo descendente con tabla M[NT, terminal]. Aplica eliminación de recursividad izquierda y factorización izquierda automáticamente si la gramática lo requiere.
- **SLR(1)** — parser ascendente basado en el autómata LR(0) y conjuntos FOLLOW.
- **LALR** — parser ascendente con ítems LR(1) fusionados por núcleo, más potente que SLR(1).

Todo se ejecuta desde una GUI con tema oscuro construida en tkinter.

---

## Requisitos

- Python 3.9 o superior
- Librería estándar de Python (no requiere dependencias externas)
- `graphviz` solo si se quieren visualizar los autómatas del lexer con `--viz`

---

## Cómo correr la GUI

```bash
python gui_main.py
```

La ventana pide tres cosas:
1. Archivo `.yal` — define los tokens con expresiones regulares
2. Archivo `.yapar` — define la gramática libre de contexto
3. Archivo de entrada — el código o texto que se quiere analizar
4. Tipo de parser — LL(1), SLR(1) o LALR

Al presionar **Analizar** muestra seis pestañas:

| Pestaña | Contenido |
|---|---|
| Tokens | Lista de tokens reconocidos por el lexer |
| Gramática | Producciones (con transformaciones aplicadas en LL(1)) |
| Estados | Autómata LR(0)/LR(1) o mensaje de tabla predictiva |
| Tabla | Tabla ACTION/GOTO o tabla LL(1) con anchos dinámicos |
| Simulación | Traza paso a paso del parsing |
| Árbol | Árbol de derivación en ASCII |

---

## Estructura del proyecto

```
proyecto/
├── gui_main.py              # entrada principal de la GUI
├── parser_main.py           # entrada por línea de comandos
├── src/
│   ├── cfg_grammar.py       # clase Grammar (producciones, terminales, no terminales)
│   ├── yapar_parser.py      # lee archivos .yapar
│   ├── first_follow.py      # cálculo de FIRST y FOLLOW
│   ├── ambiguity.py         # detección y corrección de ambigüedad
│   ├── error_recovery.py    # recuperación de errores (panic mode, phrase level)
│   ├── parse_tree.py        # árbol de derivación con render ASCII
│   ├── ll1/
│   │   ├── left_recursion.py    # eliminación de recursividad izquierda
│   │   ├── factorization.py     # factorización izquierda
│   │   └── ll1_table.py         # tabla LL(1) y parser
│   ├── lr/
│   │   ├── lr0.py               # autómata LR(0), closure, goto
│   │   └── lr_table.py          # tabla ACTION/GOTO compartida
│   ├── slr1/
│   │   └── slr1.py              # construcción SLR(1) y parser
│   ├── lalr/
│   │   └── lalr.py              # ítems LR(1), fusión de estados, parser LALR
│   ├── lexer/                   # generador de lexers (fase 1)
│   │   ├── generator.py
│   │   ├── yal_parser.py
│   │   ├── regex_parser.py
│   │   ├── nfa.py
│   │   ├── dfa.py
│   │   └── codegen.py
│   └── gui/
│       ├── app.py               # ventana principal tkinter
│       └── runner.py            # pipeline que conecta lexer + parser + GUI
└── examples/
    ├── expresiones.yal          # lexer para C (keywords, tipos, operadores)
    ├── lang.yalex               # lexer simplificado
    ├── lang.yapar               # gramática con clases y funciones (SLR/LALR)
    ├── lang_ll1.yapar           # misma gramática adaptada para LL(1)
    ├── lang_slr.yapar           # gramática para SLR(1)
    ├── grammar_expr.yapar       # gramática de expresiones aritméticas
    ├── grammar_simple.yapar     # gramática mínima de prueba
    ├── expr_ambig.yapar         # gramática ambigua (para probar detección)
    └── inputs/                  # entradas de prueba t01.txt … t20.txt
```

---

## Formato de los archivos

### `.yal` (especificación léxica)

```
let digit = ['0'-'9']
let letter = ['a'-'z''A'-'Z''_']

rule gettoken =
    digit+        { return NUM }
  | letter+       { return ID }
  | '+'           { return PLUS }
  | [' ''\t']     { return WS }
```

### `.yapar` (gramática)

```
%token ID NUM PLUS MINUS SEMI

IGNORE WS
IGNORE NEWLINE

%%

expr:
    expr PLUS term
    | term
    ;

term:
    NUM
    | ID
    ;
```

---

## Ejemplos de uso rápido

Para probar con la gramática de expresiones:

- `.yal` → `examples/expresiones.yal`
- `.yapar` → `examples/grammar_expr.yapar`
- Entrada → cualquier archivo de `examples/inputs/`
- Parser → SLR(1) o LALR

Para probar LL(1):

- `.yal` → `examples/lang.yalex`
- `.yapar` → `examples/lang_ll1.yapar`
- Entrada → `examples/lang_input.txt`
- Parser → LL(1)

---

## Uso por línea de comandos

```bash
python parser_main.py examples/lang.yalex examples/lang_slr.yapar examples/lang_input.txt --parser slr1
```

Opciones de `--parser`: `ll1`, `slr1`, `lalr`

---

## Transformaciones automáticas en LL(1)

Si la gramática tiene recursividad izquierda o prefijos comunes, el sistema las corrige antes de construir la tabla:

```
# original
expr -> expr PLUS term | term

# transformada
expr  -> term expr'
expr' -> PLUS term expr' | ε
```

La pestaña **Gramática** siempre muestra la gramática ya transformada.

---

## Detección de conflictos

- **LL(1)**: reporta conflictos en M[NT, terminal] y marca si la gramática es o no LL(1).
- **SLR(1) / LALR**: reporta conflictos shift-reduce y reduce-reduce. En shift-reduce el parser resuelve a favor del shift.
