# Generador de Analizadores Léxicos

Recibe un archivo `.yal` y genera un lexer en Python que puede tokenizar texto o código.

## Cómo usarlo

Generar el lexer:
```bash
python src/generator.py examples/expresiones.yal -o mi_lexer.py
```

Con diagramas de autómatas y árboles de expresión:
```bash
python src/generator.py examples/expresiones.yal -o mi_lexer.py --viz
```

Correr el lexer sobre un archivo:
```bash
python mi_lexer.py archivo.txt
```

## Qué hace `--viz`

Genera imágenes PNG de:
- El AFN construido con Thompson
- El AFD con el algoritmo de subconjuntos
- El AFD minimizado con Hopcroft
- Árbol de expresión por token con firstpos, lastpos y followpos

## Archivos de ejemplo

- `examples/expresiones.yal` — reconoce expresiones aritméticas y relacionales
- `archivo.txt` — archivo de prueba con expresiones
- `test.c` — archivo de prueba con código C