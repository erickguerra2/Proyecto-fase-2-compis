"""Ventana principal — tema oscuro neutro con acentos teal."""

from __future__ import annotations
import os, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from src.gui.runner import run_pipeline

# ── Paleta ───────────────────────────────────────────────────────────────────
BG      = "#0f0f1a"   # fondo base
BG2     = "#1a1a2e"   # paneles / frames
BG3     = "#252540"   # inputs / cards
FG      = "#e2e8f0"   # texto principal
FG2     = "#7c8db5"   # texto secundario
ACCENT  = "#00b4d8"   # teal
ACCENT2 = "#0284c7"   # azul (hover)
OK_C    = "#10b981"   # verde esmeralda
ERROR_C = "#ef4444"   # rojo
WARN_C  = "#f59e0b"   # ambar
SEP_C   = "#2e2e50"   # separadores

MONO    = ("Consolas", 10)
MONO_LG = ("Consolas", 11)
UI      = ("Segoe UI", 10)
UI_B    = ("Segoe UI", 10, "bold")
UI_LG   = ("Segoe UI", 11)
UI_LG_B = ("Segoe UI", 11, "bold")
UI_H    = ("Segoe UI", 13, "bold")

MAX_TOKENS_SHOW = 30
MAX_PRODS_SHOW  = 30

TAB_ICONS = {
    "Tokens":     "🔤",
    "Gramatica":  "📖",
    "Estados":    "🔵",
    "Tabla":      "📊",
    "Simulacion": "▶",
    "Arbol":      "🌳",
}


# ── Utilidades ────────────────────────────────────────────────────────────────

def _scrolled_text(parent) -> tk.Text:
    """Text con scrollbars vertical y horizontal."""
    parent.rowconfigure(0, weight=1)
    parent.columnconfigure(0, weight=1)
    txt = tk.Text(parent, bg=BG, fg=FG, font=MONO_LG,
                  insertbackground=FG, wrap="none",
                  relief="flat", borderwidth=0,
                  padx=10, pady=8,
                  selectbackground=ACCENT2, selectforeground=FG)
    vsb = tk.Scrollbar(parent, orient="vertical",   command=txt.yview,
                       bg=BG2, troughcolor=BG2, activebackground=ACCENT)
    hsb = tk.Scrollbar(parent, orient="horizontal", command=txt.xview,
                       bg=BG2, troughcolor=BG2, activebackground=ACCENT)
    txt.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    txt.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    txt.tag_config("ok",      foreground=OK_C)
    txt.tag_config("error",   foreground=ERROR_C)
    txt.tag_config("warn",    foreground=WARN_C)
    txt.tag_config("accent",  foreground=ACCENT)
    txt.tag_config("fg2",     foreground=FG2)
    txt.tag_config("bold",    font=("Consolas", 11, "bold"))
    txt.tag_config("heading", font=("Consolas", 11, "bold"), foreground=ACCENT)
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


def _hover(btn: tk.Button, normal_bg: str, hover_bg: str,
           normal_fg: str = FG, hover_fg: str = FG) -> None:
    btn.bind("<Enter>", lambda _: btn.config(bg=hover_bg, fg=hover_fg))
    btn.bind("<Leave>", lambda _: btn.config(bg=normal_bg, fg=normal_fg))


# ── App ───────────────────────────────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Generador de Analizadores Sintacticos")
        self.geometry("1200x840")
        self.minsize(900, 640)
        self.configure(bg=BG)
        self._build_ui()

    # ── Construccion UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_controls()
        self._build_banner()
        self._build_notebook()
        self._build_statusbar()

    def _build_header(self):
        tk.Frame(self, bg=ACCENT, height=3).pack(fill="x")
        hdr = tk.Frame(self, bg=BG2, pady=6)
        hdr.pack(fill="x")
        tk.Label(hdr,
                 text="  ⚙  Generador de Analizadores Sintácticos",
                 bg=BG2, fg=FG, font=UI_H, anchor="w"
                 ).pack(side="left", padx=14)
        tk.Label(hdr,
                 text="UVG · Compiladores 2025  ",
                 bg=BG2, fg=FG2, font=UI, anchor="e"
                 ).pack(side="right", padx=14)

    def _build_controls(self):
        """Panel de controles compacto — una sola franja horizontal."""
        bar = tk.Frame(self, bg=BG2, padx=12, pady=6)
        bar.pack(fill="x")
        # 3 columnas: archivos | cadena | parser+boton
        bar.columnconfigure(1, weight=1)

        rb_kw = dict(bg=BG2, fg=FG, selectcolor=BG3,
                     activebackground=BG2, font=UI,
                     relief="flat", bd=0)
        entry_kw = dict(bg=BG3, fg=FG, insertbackground=FG,
                        font=MONO, relief="flat", bd=0,
                        highlightthickness=1,
                        highlightbackground=SEP_C,
                        highlightcolor=ACCENT)

        # ── Columna 0: archivos ─────────────────────────────────────────────
        ff = tk.Frame(bar, bg=BG2)
        ff.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        ff.columnconfigure(1, weight=1)

        self.yal_var   = tk.StringVar()
        self.yapar_var = tk.StringVar()

        for r, lbl, var, types in [
            (0, "YAL:", self.yal_var,
             [("YAL files", "*.yal *.yalex"), ("All", "*.*")]),
            (1, "YAPar:", self.yapar_var,
             [("YAPar files", "*.yapar"), ("All", "*.*")]),
        ]:
            tk.Label(ff, text=lbl, bg=BG2, fg=FG2, font=UI,
                     width=6, anchor="w").grid(row=r, column=0,
                                               sticky="w", pady=2)
            tk.Entry(ff, textvariable=var, width=28,
                     **entry_kw).grid(row=r, column=1,
                                      sticky="ew", padx=(4, 4), pady=2)
            btn = tk.Button(ff, text="…",
                            command=lambda t=types, v=var: self._browse(v, t),
                            bg=BG3, fg=FG2, font=UI_B,
                            relief="flat", bd=0, padx=6, pady=1,
                            cursor="hand2")
            btn.grid(row=r, column=2, pady=2)
            _hover(btn, BG3, SEP_C, FG2, FG)

        # separador vertical
        tk.Frame(bar, bg=SEP_C, width=1).grid(
            row=0, column=0, sticky="ns", padx=(0, 0))

        # ── Columna 1: cadena de entrada ────────────────────────────────────
        sf = tk.Frame(bar, bg=BG2)
        sf.grid(row=0, column=1, sticky="ew", padx=10)
        sf.columnconfigure(1, weight=1)

        self.src_mode = tk.StringVar(value="text")

        tk.Radiobutton(sf, text="Texto:", variable=self.src_mode,
                       value="text", command=self._toggle_src,
                       **rb_kw).grid(row=0, column=0, sticky="w")
        self.text_entry = tk.Entry(sf, **entry_kw)
        self.text_entry.grid(row=0, column=1, sticky="ew",
                             padx=(6, 0), pady=2)

        tk.Radiobutton(sf, text="Archivo:", variable=self.src_mode,
                       value="file", command=self._toggle_src,
                       **rb_kw).grid(row=1, column=0, sticky="w")
        self.src_file_var = tk.StringVar()
        self.file_entry = tk.Entry(sf, textvariable=self.src_file_var,
                                   state="disabled", **entry_kw)
        self.file_entry.grid(row=1, column=1, sticky="ew",
                             padx=(6, 6), pady=2)
        self.file_btn = tk.Button(sf, text="…",
                                  command=self._browse_src,
                                  bg=BG3, fg=FG2, font=UI_B,
                                  relief="flat", bd=0, padx=6, pady=1,
                                  state="disabled", cursor="hand2")
        self.file_btn.grid(row=1, column=2, pady=2)
        _hover(self.file_btn, BG3, SEP_C, FG2, FG)

        # separador vertical
        tk.Frame(bar, bg=SEP_C, width=1).grid(
            row=0, column=1, sticky="nse", padx=(10, 0))

        # ── Columna 2: parser + botón ───────────────────────────────────────
        pf = tk.Frame(bar, bg=BG2, padx=10)
        pf.grid(row=0, column=2, sticky="ns")

        self.parser_var = tk.StringVar(value="slr1")
        rb2 = dict(bg=BG2, fg=FG, selectcolor=BG3,
                   activebackground=BG2, font=UI,
                   relief="flat", bd=0)
        rbf = tk.Frame(pf, bg=BG2)
        rbf.pack(side="left", padx=(0, 10))
        for val, lbl in [("ll1", "LL(1)"), ("slr1", "SLR(1)"), ("lalr", "LALR")]:
            tk.Radiobutton(rbf, text=lbl, variable=self.parser_var,
                           value=val, **rb2).pack(anchor="w")

        self.run_btn = tk.Button(pf, text="▶  Analizar",
                                 command=self._run,
                                 bg=ACCENT, fg=BG,
                                 font=UI_LG_B,
                                 relief="flat", bd=0,
                                 padx=16, pady=10,
                                 cursor="hand2",
                                 activebackground=ACCENT2,
                                 activeforeground=FG)
        self.run_btn.pack(side="left", fill="y")
        _hover(self.run_btn, ACCENT, ACCENT2, BG, FG)

    def _build_banner(self):
        self.result_banner = tk.Label(self, text="", font=UI_LG_B,
                                      bg=BG, pady=0)
        self.result_banner.pack(fill="x", padx=14, pady=(4, 0))

    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Dark.TNotebook",
                         background=BG, borderwidth=0, tabmargins=[2, 4, 0, 0])
        style.configure("Dark.TNotebook.Tab",
                         background=BG2, foreground=FG2,
                         font=("Segoe UI", 10, "bold"),
                         padding=[14, 6],
                         borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", BG3)],
                  foreground=[("selected", ACCENT)])

        self.nb = ttk.Notebook(self, style="Dark.TNotebook")
        self.nb.pack(fill="both", expand=True, padx=14, pady=(6, 0))

        self.tab_tokens  = self._add_tab("🔤  Tokens")
        self.tab_grammar = self._add_tab("📖  Gramática")
        self.tab_states  = self._add_tab("🔵  Estados")
        self.tab_table   = self._add_tab("📊  Tabla")
        self.tab_sim     = self._add_tab("▶  Simulación")
        self.tab_tree    = self._add_tab("🌳  Árbol")

    def _add_tab(self, title: str) -> tk.Text:
        frame = tk.Frame(self.nb, bg=BG3)
        self.nb.add(frame, text=title)
        # borde interno sutil
        inner = tk.Frame(frame, bg=BG3)
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        return _scrolled_text(inner)

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=BG2, pady=4)
        bar.pack(fill="x", side="bottom")
        tk.Frame(bar, bg=SEP_C, height=1).pack(fill="x")
        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(bar, textvariable=self.status_var,
                 bg=BG2, fg=FG2, font=UI,
                 anchor="w", padx=14).pack(fill="x")

    # ── Interaccion ──────────────────────────────────────────────────────────

    def _file_row(self, parent, label, var, row, types):
        """Fila de archivo compacta (helper interno)."""
        tk.Label(parent, text=label, bg=BG2, fg=FG2,
                 font=UI, anchor="w"
                 ).grid(row=row, column=0, sticky="w", pady=2)
        tk.Entry(parent, textvariable=var, bg=BG3, fg=FG,
                 insertbackground=FG, font=MONO,
                 relief="flat", bd=0,
                 highlightthickness=1,
                 highlightbackground=SEP_C,
                 highlightcolor=ACCENT
                 ).grid(row=row, column=1, sticky="ew", padx=(6, 6), pady=2)
        btn = tk.Button(parent, text="…",
                        command=lambda t=types, v=var: self._browse(v, t),
                        bg=BG3, fg=FG2, font=UI_B,
                        relief="flat", bd=0, padx=6, pady=1,
                        cursor="hand2")
        btn.grid(row=row, column=2, pady=2)
        _hover(btn, BG3, SEP_C, FG2, FG)

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

        self.run_btn.config(state="disabled", text="⏳  Analizando...")
        self.result_banner.config(text="", bg=BG)
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
        error    = res.get('error')
        tokens   = res.get('tokens', [])
        warnings = res.get('ambiguity_warnings', [])
        mode     = self.parser_var.get().upper()

        # ── Tokens ──
        _write(self.tab_tokens, "")
        self.tab_tokens.config(state="normal")
        hdr = f"  {'#':<5} {'Tipo':<24} {'Lexema':<24} {'Línea':<7} Col\n"
        hdr += "  " + "─" * 66 + "\n"
        self.tab_tokens.insert("end", hdr, "heading")
        for i, tok in enumerate(tokens[:MAX_TOKENS_SHOW], 1):
            typ, lex = tok[0], tok[1]
            ln, col  = tok[2], tok[3]
            self.tab_tokens.insert(
                "end",
                f"  {i:<5} {typ:<24} {lex:<24} {str(ln or ''):<7} {str(col or '')}\n"
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

        # ── Gramática ──
        _write(self.tab_grammar, "")
        self.tab_grammar.config(state="normal")
        n_prod = res.get('productions_count', 0)
        n_nt   = res.get('nonterminals_count', 0)
        self.tab_grammar.insert(
            "end",
            f"  Producciones: {n_prod}   |   No-terminales: {n_nt}\n\n",
            "fg2"
        )
        if n_prod <= MAX_PRODS_SHOW:
            gram = res.get('grammar_text', '')
            if gram:
                self.tab_grammar.insert("end", "  Producciones:\n", "heading")
                self.tab_grammar.insert("end", gram + "\n\n")
        else:
            self.tab_grammar.insert(
                "end", "  (gramática grande — producciones omitidas)\n\n", "warn"
            )
        ff = res.get('first_follow', '')
        if ff:
            self.tab_grammar.insert("end", "\n" + ff + "\n")
        self.tab_grammar.config(state="disabled")

        # ── Estados ──
        states = res.get('states_text', '')
        gotos  = res.get('gotos_text', '')
        _write(self.tab_states, (states + "\n\n" + gotos).strip())

        # ── Tabla ──
        _write(self.tab_table, "")
        self.tab_table.config(state="normal")
        conflicts = res.get('conflicts', [])
        if conflicts:
            self.tab_table.insert(
                "end",
                f"  ⚠  {len(conflicts)} conflicto(s) detectado(s):\n",
                "warn"
            )
            for c in conflicts[:5]:
                self.tab_table.insert("end", f"    {c}\n", "warn")
            self.tab_table.insert("end", "\n")
        else:
            self.tab_table.insert("end", "  ✓  Sin conflictos.\n\n", "ok")
        tbl = res.get('table_text', '')
        if tbl:
            self.tab_table.insert("end", tbl)
        self.tab_table.config(state="disabled")

        # ── Simulación ──
        _write(self.tab_sim, "")
        self.tab_sim.config(state="normal")
        trace  = res.get('trace', [])
        is_ll1 = self.parser_var.get() == "ll1"
        if trace:
            if is_ll1:
                pw  = max(len(str(len(trace))), 4)
                stw = max(max((len(s) for s, _, _ in trace), default=5), 5)
                iw  = max(max((len(i) for _, i, _ in trace), default=7), 7)
                sep_w = pw + stw + iw + 36
                hdr = (f"  {'Paso':<{pw+2}}  {'Pila':<{stw+2}}  "
                       f"{'Entrada':<{iw+2}}  Acción\n")
                hdr += "  " + "─" * sep_w + "\n"
                self.tab_sim.insert("end", hdr, "heading")
                for i, (pila, entrada, accion) in enumerate(trace, 1):
                    is_acc = "accept" in accion.lower()
                    is_err = "error"  in accion.lower()
                    tag  = "ok" if is_acc else ("error" if is_err else "")
                    line = (f"  {i:<{pw+2}}  {pila:<{stw+2}}  "
                            f"{entrada:<{iw+2}}  {accion}\n")
                    self.tab_sim.insert("end", line, tag)
            else:
                pw  = max(len(str(len(trace))), 4)
                stw = max(max((len(s) for s, _, _, _ in trace), default=5), 5)
                smw = max(max((len(m) for _, m, _, _ in trace), default=7), 7)
                iw  = max(max((len(i) for _, _, i, _ in trace), default=7), 7)
                sep_w = pw + stw + smw + iw + 46
                hdr = (f"  {'Paso':<{pw+2}}  {'Pila':<{stw+2}}  "
                       f"{'Símbolos':<{smw+2}}  {'Entrada':<{iw+2}}  Acción\n")
                hdr += "  " + "─" * sep_w + "\n"
                self.tab_sim.insert("end", hdr, "heading")
                for i, (pila, simbolo, entrada, accion) in enumerate(trace, 1):
                    is_acc = "accept" in accion.lower()
                    is_err = "error"  in accion.lower()
                    tag  = "ok" if is_acc else ("error" if is_err else "")
                    line = (f"  {i:<{pw+2}}  {pila:<{stw+2}}  "
                            f"{simbolo:<{smw+2}}  {entrada:<{iw+2}}  {accion}\n")
                    self.tab_sim.insert("end", line, tag)
        elif not trace and not error:
            self.tab_sim.insert("end",
                "  (sin simulación disponible para esta gramática)\n", "fg2")
        self.tab_sim.config(state="disabled")

        # ── Árbol / Ambigüedad ──
        _write(self.tab_tree, "")
        self.tab_tree.config(state="normal")
        if warnings:
            self.tab_tree.insert(
                "end",
                f"  ⚠  GRAMÁTICA AMBIGUA — {len(warnings)} indicador(es)\n",
                "warn"
            )
            for w in warnings:
                self.tab_tree.insert("end", f"    {w}\n", "warn")
            self.tab_tree.insert("end", "\n")
        else:
            self.tab_tree.insert(
                "end", "  ✓  Gramática sin indicadores de ambigüedad.\n\n", "ok"
            )
        amb = res.get('ambiguity_text', '')
        if amb:
            self.tab_tree.insert("end", amb + "\n")
        elif res.get('accepted') and not warnings:
            self.tab_tree.insert(
                "end",
                "  Cadena aceptada. Cada cadena tiene exactamente un árbol.\n",
                "ok"
            )
        self.tab_tree.config(state="disabled")

        # ── Banner de resultado ──
        if error:
            self.result_banner.config(
                text=f"  ✗   CADENA RECHAZADA",
                bg=ERROR_C, fg="white",
                font=("Segoe UI", 12, "bold"), pady=6
            )
        elif res.get('accepted'):
            extra = "  ⚠  gramática ambigua" if warnings else ""
            self.result_banner.config(
                text=f"  ✓   CADENA ACEPTADA  ({mode}){extra}",
                bg=OK_C, fg="white",
                font=("Segoe UI", 12, "bold"), pady=6
            )
            self.nb.select(4)
        else:
            self.result_banner.config(text="", bg=BG, pady=0)

        # ── Status bar ──
        if error:
            self.status_var.set(f"✗  {error[:120]}")
            for tab in (self.tab_tokens, self.tab_grammar, self.tab_states,
                        self.tab_table, self.tab_sim, self.tab_tree):
                tab.config(state="normal")
                tab.insert("1.0", f"[ERROR] {error}\n\n", "error")
                tab.config(state="disabled")
        elif res.get('accepted'):
            n = len(tokens)
            self.status_var.set(
                f"✓  Cadena aceptada ({mode})  |  {n} token(s)"
                + ("  |  ⚠ gramática ambigua" if warnings else "")
            )
        else:
            self.status_var.set("✗  Cadena rechazada o error en el pipeline.")
