"""Ventana principal: tabs Tokens / Gramatica / Estados / Tabla / Arbol."""

from __future__ import annotations
import os, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from src.gui.runner import run_pipeline

# ── Paleta de colores ────────────────────────────────────────────────────────
BG       = "#1e1e2e"
FG       = "#cdd6f4"
ENTRY_BG = "#313244"
ACCENT   = "#89b4fa"
OK_C     = "#a6e3a1"
ERROR_C  = "#f38ba8"
WARN_C   = "#fab387"
MONO     = ("Courier New", 10)
UI       = ("Segoe UI", 10)
UI_B     = ("Segoe UI", 10, "bold")

MAX_TOKENS_SHOW = 30
MAX_PRODS_SHOW  = 30


# ── Utilidades de widget ─────────────────────────────────────────────────────

def _scrolled_text(parent) -> tk.Text:
    """Text con scrollbars vertical y horizontal sobre un frame grid."""
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    txt = tk.Text(parent, bg=BG, fg=FG, font=MONO,
                  insertbackground=FG, wrap="none",
                  relief="flat", borderwidth=0)
    vsb = tk.Scrollbar(parent, orient="vertical",   command=txt.yview)
    hsb = tk.Scrollbar(parent, orient="horizontal", command=txt.xview)
    txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    txt.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    # Tags de color
    txt.tag_config("ok",     foreground=OK_C)
    txt.tag_config("error",  foreground=ERROR_C)
    txt.tag_config("warn",   foreground=WARN_C)
    txt.tag_config("accent", foreground=ACCENT)
    txt.tag_config("bold",   font=("Courier New", 10, "bold"))
    return txt


def _write(txt: tk.Text, content: str, tag: str = "") -> None:
    txt.config(state="normal")
    txt.delete("1.0", "end")
    if tag:
        txt.insert("end", content, tag)
    else:
        txt.insert("end", content)
    txt.config(state="disabled")


def _append(txt: tk.Text, content: str, tag: str = "") -> None:
    txt.config(state="normal")
    if tag:
        txt.insert("end", content, tag)
    else:
        txt.insert("end", content)
    txt.config(state="disabled")


# ── App principal ────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Generador de Analizadores Sintacticos")
        self.geometry("1150x800")
        self.minsize(860, 600)
        self.configure(bg=BG)
        self._build_ui()

    # ── Construccion de la UI ────────────────────────────────────────────────

    def _build_ui(self):
        self._build_controls()
        self._build_notebook()
        self._build_statusbar()

    def _build_controls(self):
        ctrl = tk.Frame(self, bg=BG, padx=10, pady=6)
        ctrl.pack(fill="x")

        # Archivos
        lf = tk.LabelFrame(ctrl, text=" Archivos ", bg=BG, fg=ACCENT,
                            font=UI, padx=8, pady=4)
        lf.pack(fill="x", pady=(0, 4))

        self.yal_var   = tk.StringVar()
        self.yapar_var = tk.StringVar()
        self._file_row(lf, "YAL / YALex:", self.yal_var,   0,
                       [("YAL files", "*.yal *.yalex"), ("All", "*.*")])
        self._file_row(lf, "YAPar:      ", self.yapar_var, 1,
                       [("YAPar files", "*.yapar"),     ("All", "*.*")])

        # Cadena de entrada
        sf = tk.LabelFrame(ctrl, text=" Cadena de entrada ", bg=BG, fg=ACCENT,
                           font=UI, padx=8, pady=4)
        sf.pack(fill="x", pady=(0, 4))
        sf.columnconfigure(1, weight=1)

        self.src_mode = tk.StringVar(value="text")

        tk.Radiobutton(sf, text="Texto:", variable=self.src_mode, value="text",
                       bg=BG, fg=FG, selectcolor=BG, activebackground=BG,
                       font=UI, command=self._toggle_src
                       ).grid(row=0, column=0, sticky="w")
        self.text_entry = tk.Entry(sf, bg=ENTRY_BG, fg=FG,
                                   insertbackground=FG, font=MONO)
        self.text_entry.grid(row=0, column=1, columnspan=2,
                             sticky="ew", padx=(4, 0), pady=2)

        tk.Radiobutton(sf, text="Archivo:", variable=self.src_mode, value="file",
                       bg=BG, fg=FG, selectcolor=BG, activebackground=BG,
                       font=UI, command=self._toggle_src
                       ).grid(row=1, column=0, sticky="w")
        self.src_file_var = tk.StringVar()
        self.file_entry = tk.Entry(sf, textvariable=self.src_file_var,
                                   bg=ENTRY_BG, fg=FG, insertbackground=FG,
                                   font=MONO, state="disabled")
        self.file_entry.grid(row=1, column=1, sticky="ew",
                             padx=(4, 4), pady=2)
        self.file_btn = tk.Button(sf, text="Examinar",
                                  command=self._browse_src,
                                  bg=ACCENT, fg=BG, font=UI, state="disabled")
        self.file_btn.grid(row=1, column=2, pady=2)

        # Parser + boton
        rf = tk.Frame(ctrl, bg=BG)
        rf.pack(fill="x")

        tk.Label(rf, text="Parser:", bg=BG, fg=FG, font=UI).pack(side="left")
        self.parser_var = tk.StringVar(value="slr1")
        for val, lbl in [("ll1", "LL(1)"), ("slr1", "SLR(1)"), ("lalr", "LALR")]:
            tk.Radiobutton(rf, text=lbl, variable=self.parser_var, value=val,
                           bg=BG, fg=FG, selectcolor=BG, activebackground=BG,
                           font=UI).pack(side="left", padx=8)

        self.run_btn = tk.Button(rf, text="▶  Analizar",
                                 command=self._run,
                                 bg=OK_C, fg=BG, font=("Segoe UI", 11, "bold"),
                                 padx=14, pady=3)
        self.run_btn.pack(side="right")

    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook",     background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=ENTRY_BG, foreground=FG,
                        font=UI, padding=[12, 4])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", BG)])

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self.tab_tokens  = self._add_tab("  Tokens  ")
        self.tab_grammar = self._add_tab("  Gramatica  ")
        self.tab_states  = self._add_tab("  Estados  ")
        self.tab_table   = self._add_tab("  Tabla  ")
        self.tab_tree    = self._add_tab("  Arbol  ")

    def _add_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self.nb, bg=BG)
        self.nb.add(frame, text=title)
        return _scrolled_text(frame)

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(self, textvariable=self.status_var,
                 bg=ENTRY_BG, fg=FG, font=UI,
                 anchor="w", padx=10).pack(fill="x", side="bottom")

    # ── Interaccion ──────────────────────────────────────────────────────────

    def _file_row(self, parent, label, var, row, types):
        tk.Label(parent, text=label, bg=BG, fg=FG, font=UI,
                 width=13, anchor="w").grid(row=row, column=0, sticky="w")
        tk.Entry(parent, textvariable=var, bg=ENTRY_BG, fg=FG,
                 insertbackground=FG, font=MONO
                 ).grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=2)
        tk.Button(parent, text="Examinar",
                  command=lambda t=types, v=var: self._browse(v, t),
                  bg=ACCENT, fg=BG, font=UI
                  ).grid(row=row, column=2, pady=2)
        parent.columnconfigure(1, weight=1)

    def _browse(self, var: tk.StringVar, types):
        path = filedialog.askopenfilename(filetypes=types)
        if path:
            var.set(path)

    def _browse_src(self):
        path = filedialog.askopenfilename(
            filetypes=[("Archivos fuente", "*.c *.txt *.py *.java *.cs"),
                       ("All", "*.*")])
        if path:
            self.src_file_var.set(path)

    def _toggle_src(self):
        if self.src_mode.get() == "text":
            self.text_entry.config(state="normal")
            self.file_entry.config(state="disabled")
            self.file_btn.config(state="disabled")
        else:
            self.text_entry.config(state="disabled")
            self.file_entry.config(state="normal")
            self.file_btn.config(state="normal")

    def _run(self):
        yal   = self.yal_var.get().strip()
        yapar = self.yapar_var.get().strip()
        if not yal or not yapar:
            messagebox.showerror("Faltan archivos",
                                 "Selecciona el archivo .yal y .yapar.")
            return

        if self.src_mode.get() == "text":
            source = self.text_entry.get().strip()
            if not source:
                messagebox.showerror("Sin cadena",
                                     "Escribe la cadena a analizar.")
                return
        else:
            src_file = self.src_file_var.get().strip()
            if not src_file or not os.path.exists(src_file):
                messagebox.showerror("Archivo no encontrado",
                                     f"No existe:\n{src_file}")
                return
            with open(src_file, encoding="utf-8") as f:
                source = f.read()

        self.run_btn.config(state="disabled", text="Analizando...")
        self.status_var.set("Ejecutando pipeline...")
        self.update()

        try:
            res = run_pipeline(yal, yapar, source, self.parser_var.get())
        except Exception as e:
            res = {'error': f"Error inesperado: {e}"}
        finally:
            self.run_btn.config(state="normal", text="▶  Analizar")

        self._populate(res)

    # ── Relleno de tabs ──────────────────────────────────────────────────────

    def _populate(self, res: dict):
        error = res.get('error')

        # ── Tab Tokens ──
        tokens = res.get('tokens', [])
        _write(self.tab_tokens, "")
        self.tab_tokens.config(state="normal")
        header = f"{'#':<5} {'Tipo':<22} {'Lexema':<22} {'Linea':<7} Col\n"
        header += "─" * 64 + "\n"
        self.tab_tokens.insert("end", header, "accent")
        shown = tokens[:MAX_TOKENS_SHOW]
        for i, tok in enumerate(shown, 1):
            typ, lex = tok[0], tok[1]
            ln, col  = tok[2], tok[3]
            self.tab_tokens.insert(
                "end",
                f"{i:<5} {typ:<22} {lex:<22} {str(ln):<7} {str(col)}\n"
            )
        if len(tokens) > MAX_TOKENS_SHOW:
            self.tab_tokens.insert(
                "end",
                f"\n  ... mostrando {MAX_TOKENS_SHOW} de {len(tokens)} tokens\n",
                "warn"
            )
        if not tokens and not error:
            self.tab_tokens.insert("end", "  (sin tokens reconocidos)\n", "warn")
        self.tab_tokens.config(state="disabled")

        # ── Tab Gramatica ──
        _write(self.tab_grammar, "")
        self.tab_grammar.config(state="normal")
        n_prod = res.get('productions_count', 0)
        n_nt   = res.get('nonterminals_count', 0)
        if n_prod > MAX_PRODS_SHOW:
            self.tab_grammar.insert(
                "end",
                f"Gramatica: {n_prod} producciones, {n_nt} no-terminales\n"
                f"(gramatica grande — se omiten las producciones)\n\n",
                "warn"
            )
        else:
            gram = res.get('grammar_text', '')
            if gram:
                self.tab_grammar.insert("end", "Producciones:\n", "accent")
                self.tab_grammar.insert("end", gram + "\n\n")
        ff = res.get('first_follow', '')
        if ff:
            self.tab_grammar.insert("end", ff + "\n")
        self.tab_grammar.config(state="disabled")

        # ── Tab Estados ──
        states = res.get('states_text', '')
        gotos  = res.get('gotos_text', '')
        _write(self.tab_states, (states + "\n\n" + gotos).strip())

        # ── Tab Tabla ──
        _write(self.tab_table, "")
        self.tab_table.config(state="normal")
        conflicts = res.get('conflicts', [])
        if conflicts:
            self.tab_table.insert(
                "end",
                f"⚠  {len(conflicts)} conflicto(s) detectado(s):\n",
                "warn"
            )
            for c in conflicts[:5]:
                self.tab_table.insert("end", f"  {c}\n", "warn")
            self.tab_table.insert("end", "\n")
        else:
            self.tab_table.insert("end", "Sin conflictos.\n\n", "ok")
        tbl = res.get('table_text', '')
        if tbl:
            self.tab_table.insert("end", tbl)
        self.tab_table.config(state="disabled")

        # ── Tab Arbol ──
        _write(self.tab_tree, "")
        self.tab_tree.config(state="normal")
        warnings = res.get('ambiguity_warnings', [])
        if warnings:
            self.tab_tree.insert(
                "end",
                f"⚠  GRAMATICA AMBIGUA — {len(warnings)} indicador(es):\n",
                "warn"
            )
            for w in warnings:
                self.tab_tree.insert("end", f"  {w}\n", "warn")
            self.tab_tree.insert("end", "\n")
        else:
            self.tab_tree.insert("end", "Gramatica sin indicadores de ambiguedad.\n\n", "ok")

        amb = res.get('ambiguity_text', '')
        if amb:
            self.tab_tree.insert("end", amb + "\n")
        elif res.get('accepted') and not warnings:
            self.tab_tree.insert(
                "end",
                "Cadena aceptada. Cada cadena tiene exactamente un arbol.\n",
                "ok"
            )
        self.tab_tree.config(state="disabled")

        # ── Status bar ──
        if error:
            self.status_var.set(f"✗  {error[:120]}")
            # Mostrar error en tab activo tambien
            for tab in (self.tab_tokens, self.tab_grammar,
                        self.tab_states,  self.tab_table, self.tab_tree):
                tab.config(state="normal")
                tab.insert("1.0", f"[ERROR] {error}\n\n", "error")
                tab.config(state="disabled")
        elif res.get('accepted'):
            mode = self.parser_var.get().upper()
            n    = len(tokens)
            self.status_var.set(
                f"✓  Cadena aceptada ({mode})  |  {n} token(s)"
                + ("  |  ⚠ gramatica ambigua" if warnings else "")
            )
            self.nb.select(4)   # ir directo al arbol
        else:
            self.status_var.set("✗  Cadena rechazada o error en pipeline.")
