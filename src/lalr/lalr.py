"""Construccion de tabla LALR via LR(1) con fusion de estados por core LR(0)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Set, Tuple, Optional
from src.cfg_grammar import Grammar
from src.first_follow import compute_first, first_of_string, EPSILON, EOF_SYM
from src.lr.lr0 import augment_grammar, LR0State
from src.lr.lr_table import LRTable, LRAction, SHIFT, REDUCE, ACCEPT
from src.error_recovery import panic_mode_recovery, SyntaxError_, format_errors
from src.parse_tree import ParseTree


@dataclass(frozen=True)
class LR1Item:
    """Item LR(1): produccion con punto y lookahead."""
    nt:        str
    prod:      Tuple[str, ...]
    dot:       int
    lookahead: str

    @property
    def core(self) -> Tuple:
        return (self.nt, self.prod, self.dot)

    @property
    def next_symbol(self) -> Optional[str]:
        return self.prod[self.dot] if self.dot < len(self.prod) else None

    @property
    def is_complete(self) -> bool:
        return self.dot >= len(self.prod)

    def advance(self) -> "LR1Item":
        return LR1Item(self.nt, self.prod, self.dot + 1, self.lookahead)

    def __str__(self) -> str:
        syms = list(self.prod)
        syms.insert(self.dot, "*")
        body = " ".join(syms) if syms else "*"
        return f"[{self.nt} -> {body}, {self.lookahead}]"


def _lr1_closure(items: FrozenSet[LR1Item], grammar: Grammar, first: dict) -> FrozenSet[LR1Item]:
    result  = set(items)
    changed = True
    while changed:
        changed = False
        for item in list(result):
            sym = item.next_symbol
            if not sym or sym not in grammar.nonterminals:
                continue
            beta = list(item.prod[item.dot + 1:]) + [item.lookahead]
            lookaheads = first_of_string(beta, first) - {EPSILON}
            for prod in grammar.productions.get(sym, []):
                for la in lookaheads:
                    new_item = LR1Item(sym, tuple(prod), 0, la)
                    if new_item not in result:
                        result.add(new_item)
                        changed = True
    return frozenset(result)


def _lr1_goto(items: FrozenSet[LR1Item], symbol: str,
              grammar: Grammar, first: dict) -> FrozenSet[LR1Item]:
    moved = {item.advance() for item in items if item.next_symbol == symbol}
    return _lr1_closure(moved, grammar, first) if moved else frozenset()


def _build_lr1_collection(grammar: Grammar) -> Tuple[List[FrozenSet[LR1Item]], Dict, str]:
    """Coleccion canonica LR(1)."""
    aug_grammar, aug_start = augment_grammar(grammar)
    first = compute_first(aug_grammar)
    first[EOF_SYM] = {EOF_SYM}  # asegurar que $ este en first

    start_prod = tuple(aug_grammar.productions[aug_start][0])
    start_set  = _lr1_closure(
        frozenset({LR1Item(aug_start, start_prod, 0, EOF_SYM)}),
        aug_grammar, first
    )

    collection:  List[FrozenSet[LR1Item]]    = [start_set]
    seen:        Dict[FrozenSet[LR1Item], int] = {start_set: 0}
    transitions: Dict[Tuple[int, str], int]   = {}
    queue = [start_set]

    while queue:
        current = queue.pop(0)
        cur_id  = seen[current]
        symbols = {item.next_symbol for item in current if item.next_symbol}

        for sym in symbols:
            nxt = _lr1_goto(current, sym, aug_grammar, first)
            if not nxt:
                continue
            if nxt not in seen:
                new_id = len(collection)
                seen[nxt] = new_id
                collection.append(nxt)
                queue.append(nxt)
            transitions[(cur_id, sym)] = seen[nxt]

    return collection, transitions, aug_start


def _merge_states(collection:   List[FrozenSet[LR1Item]],
                  transitions:  Dict[Tuple[int, str], int]
                  ) -> Tuple[List[FrozenSet[LR1Item]], Dict[Tuple[int, str], int], Dict[int, int]]:
    """Fusiona estados LR(1) con el mismo core LR(0)."""
    core_to_group: Dict[FrozenSet[Tuple], List[int]] = {}
    for i, state in enumerate(collection):
        core = frozenset(item.core for item in state)
        core_to_group.setdefault(core, []).append(i)

    old_to_new: Dict[int, int] = {}
    merged:     List[FrozenSet[LR1Item]] = []

    for core, group in core_to_group.items():
        new_id = len(merged)
        joined: Dict[Tuple, Set[str]] = {}
        for old_id in group:
            old_to_new[old_id] = new_id
            for item in collection[old_id]:
                joined.setdefault(item.core, set()).add(item.lookahead)
        merged_items = frozenset(
            LR1Item(c[0], c[1], c[2], la)
            for c, las in joined.items()
            for la in las
        )
        merged.append(merged_items)

    new_trans: Dict[Tuple[int, str], int] = {
        (old_to_new[sid], sym): old_to_new[tgt]
        for (sid, sym), tgt in transitions.items()
    }

    return merged, new_trans, old_to_new


def build_lalr_table(grammar: Grammar) -> Tuple[LRTable, List[LR0State], str]:
    """Construye la tabla LALR. Retorna (tabla, estados, aug_start)."""
    collection, transitions, aug_start = _build_lr1_collection(grammar)
    merged_states, new_trans, _        = _merge_states(collection, transitions)

    lr0_states = []
    for i, state in enumerate(merged_states):
        s = LR0State(id=i, items=state)
        s.transitions = {sym: tgt for (sid, sym), tgt in new_trans.items() if sid == i}
        lr0_states.append(s)

    table = LRTable(lr0_states)

    for i, state in enumerate(merged_states):
        trans_i = {sym: tgt for (sid, sym), tgt in new_trans.items() if sid == i}

        for item in state:
            sym = item.next_symbol

            if sym is not None and sym in grammar.terminals:
                target = trans_i.get(sym)
                if target is not None:
                    table.set_action(i, sym, LRAction(SHIFT, state=target))

            elif item.is_complete:
                if item.nt == aug_start:
                    table.set_action(i, EOF_SYM, LRAction(ACCEPT))
                else:
                    table.set_action(
                        i, item.lookahead,
                        LRAction(REDUCE, nt=item.nt, prod=item.prod)
                    )

        for sym, target in trans_i.items():
            if sym in grammar.nonterminals:
                table.set_goto(i, sym, target)

    return table, lr0_states, aug_start


class LALRParseError(Exception):
    pass


class LALRParser:
    """Parser LALR con pila de estados."""

    def __init__(self, grammar: Grammar, tokens: List[Tuple]) -> None:
        self.grammar    = grammar
        self.tokens     = [tok for tok in tokens
                           if tok[0] not in ("WS", "WHITESPACE", "NEWLINE")]
        self.table, self.states, self.aug_start = build_lalr_table(grammar)
        self.recovery_log: List[SyntaxError_] = []
        self.parse_tree = None

    def is_lalr(self) -> bool:
        return not self.table.has_conflicts()

    def parse(self) -> bool:
        """Ejecuta el parsing LALR. Retorna True si acepta. Construye self.parse_tree."""
        if not self.is_lalr():
            conflicts = "\n".join(str(c) for c in self.table.conflicts[:3])
            raise LALRParseError(
                f"La gramatica tiene {len(self.table.conflicts)} conflictos LALR.\n"
                + conflicts
            )

        input_tokens = self.tokens + [(EOF_SYM, EOF_SYM, None, None)]
        pos        = 0
        stack      = [0]
        tree_stack: List[ParseTree] = []
        self.recovery_log = []
        self.parse_tree   = None

        while True:
            state   = stack[-1]
            tok     = input_tokens[pos]
            cur_type, cur_lex = tok[0], tok[1]

            action = (self.table.get_action(state, cur_type) or
                      self.table.get_action(state, cur_lex))

            if action is None:
                new_pos, _, err = panic_mode_recovery(input_tokens, pos)
                self.recovery_log.append(err)
                pos = new_pos
                if pos >= len(input_tokens):
                    raise LALRParseError("Fin de entrada durante recuperacion.")
                continue

            if action.kind == SHIFT:
                stack.append(action.state)
                label = cur_lex if cur_lex and cur_lex != cur_type else cur_type
                tree_stack.append(ParseTree(label))
                pos += 1

            elif action.kind == REDUCE:
                children = []
                for _ in range(len(action.prod)):
                    stack.pop()
                    children.insert(0, tree_stack.pop())
                goto = self.table.get_goto(stack[-1], action.nt)
                if goto is None:
                    raise LALRParseError(
                        f"GOTO indefinido: estado {stack[-1]}, NT '{action.nt}'"
                    )
                stack.append(goto)
                node = ParseTree(action.nt, children) if children else ParseTree(action.nt, [ParseTree("e")])
                tree_stack.append(node)

            elif action.kind == ACCEPT:
                self.parse_tree = tree_stack[-1] if tree_stack else None
                return True

    def recovery_report(self) -> str:
        if not self.recovery_log:
            return "  Sin acciones de recuperacion LALR."
        return format_errors(self.recovery_log)


def report_lalr_states(states: list) -> str:
    """Reporte de estados LALR agrupando lookaheads por core de item."""
    lines = [f"Automata LALR: {len(states)} estado(s)"]
    for state in states:
        lines.append(f"Estado {state.id}:")
        core_to_las: dict = {}
        for item in state.items:
            core = (item.nt, item.prod, item.dot)
            core_to_las.setdefault(core, set()).add(item.lookahead)
        for (nt, prod, dot), las in sorted(core_to_las.items(),
                                           key=lambda x: (x[0][0], x[0][2])):
            syms = list(prod)
            syms.insert(dot, "•")
            body = " ".join(syms) if syms else "•"
            la_str = ", ".join(sorted(las))
            lines.append(f"  [{nt} -> {body}, {{{la_str}}}]")
        for sym, target in sorted(state.transitions.items()):
            lines.append(f"    GOTO({sym}) -> Estado {target}")
    return "\n".join(lines)
