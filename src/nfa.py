"""
Construye el AFN por el método de Thompson.
"""
from dataclasses import dataclass, field
from typing import Optional

EPSILON = "ε"


@dataclass
class State:
    id:          int
    is_accept:   bool             = False
    token_name:  Optional[str]    = None
    transitions: dict             = field(default_factory=dict)

_state_counter = 0

def _new_state(accept=False, token=None) -> State:
    global _state_counter
    s = State(id=_state_counter, is_accept=accept, token_name=token)
    _state_counter += 1
    return s

def reset_counter():
    global _state_counter
    _state_counter = 0


def _add_transition(src: State, symbol, dst: State):
    src.transitions.setdefault(symbol, [])
    if dst not in src.transitions[symbol]:
        src.transitions[symbol].append(dst)


class Fragment:
    def __init__(self, start: State, ends: list):
        self.start = start
        self.ends  = ends

    def patch(self, state: State):
        for s in self.ends:
            _add_transition(s, EPSILON, state)


def _frag_symbol(sym) -> Fragment:
    s0 = _new_state()
    s1 = _new_state()
    _add_transition(s0, sym, s1)
    return Fragment(s0, [s1])


def _frag_concat(f1: Fragment, f2: Fragment) -> Fragment:
    f1.patch(f2.start)
    return Fragment(f1.start, f2.ends)


def _frag_union(f1: Fragment, f2: Fragment) -> Fragment:
    s0 = _new_state()
    _add_transition(s0, EPSILON, f1.start)
    _add_transition(s0, EPSILON, f2.start)
    return Fragment(s0, f1.ends + f2.ends)


def _frag_star(f: Fragment) -> Fragment:
    s0 = _new_state()
    s1 = _new_state()
    _add_transition(s0, EPSILON, f.start)
    _add_transition(s0, EPSILON, s1)
    f.patch(s0)
    return Fragment(s0, [s1])


def _frag_plus(f: Fragment) -> Fragment:
    s0 = _new_state()
    s1 = _new_state()
    _add_transition(s0, EPSILON, f.start)
    f.patch(s0)
    loop_start = _new_state()
    _add_transition(loop_start, EPSILON, f.start)
    _add_transition(loop_start, EPSILON, s1)
    f.patch(loop_start)
    return Fragment(s0, [s1])


def _frag_opt(f: Fragment) -> Fragment:
    s0 = _new_state()
    s1 = _new_state()
    _add_transition(s0, EPSILON, f.start)
    _add_transition(s0, EPSILON, s1)
    f.patch(s1)
    return Fragment(s0, [s1])


def build_nfa_from_postfix(postfix: list, token_name: str = None):
    stack = []

    for tok in postfix:
        kind = tok[0]

        if kind in ("CHAR", "EOF"):
            sym = tok[1] if kind == "CHAR" else "eof"
            stack.append(_frag_symbol(sym))

        elif kind == "SET":
            stack.append(_frag_symbol(tok[1]))

        elif kind == "ANY":
            # acepta cualquier carácter ASCII imprimible
            all_chars = frozenset(chr(k) for k in range(32, 127))
            stack.append(_frag_symbol(all_chars))

        elif kind == "OP":
            op = tok[1]
            if op == "·":
                f2 = stack.pop(); f1 = stack.pop()
                stack.append(_frag_concat(f1, f2))
            elif op == "|":
                f2 = stack.pop(); f1 = stack.pop()
                stack.append(_frag_union(f1, f2))
            elif op == "*":
                f = stack.pop()
                stack.append(_frag_star(f))
            elif op == "+":
                f = stack.pop()
                import copy
                f_star_end = _new_state()
                loop = _new_state()
                _add_transition(loop, EPSILON, f.start)
                _add_transition(loop, EPSILON, f_star_end)
                f.patch(loop)
                new_frag = Fragment(f.start, [f_star_end])
                stack.append(new_frag)
            elif op == "?":
                f = stack.pop()
                stack.append(_frag_opt(f))
            elif op == "#":
                _ = stack.pop()  # diferencia no implementada a nivel NFA
                stack.append(stack.pop() if stack else _)

    if not stack:
        raise ValueError("Expresión vacía")

    frag = stack.pop()
    accept = _new_state(accept=True, token=token_name)
    frag.patch(accept)
    return frag.start, accept


def build_global_nfa(nfa_list: list):
    global_start = _new_state()
    for (start, accept, _priority) in nfa_list:
        _add_transition(global_start, EPSILON, start)
    return global_start


def collect_states(start: State) -> list:
    """Recolecta todos los estados del AFN por BFS."""
    visited, queue = set(), [start]
    while queue:
        s = queue.pop(0)
        if s.id in visited: continue
        visited.add(s.id)
        for targets in s.transitions.values():
            for t in targets:
                if t.id not in visited:
                    queue.append(t)
    return sorted(visited)
