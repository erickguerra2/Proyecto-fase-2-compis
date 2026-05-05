"""Conversion AFN -> AFD (subconjuntos) y minimizacion de Hopcroft."""
from nfa import State, EPSILON

def epsilon_closure(state_list) -> frozenset:
    """Devuelve frozenset de ids de estados."""
    stack   = list(state_list)
    closure = {s.id: s for s in state_list}
    while stack:
        s = stack.pop()
        for target in s.transitions.get(EPSILON, []):
            if target.id not in closure:
                closure[target.id] = target
                stack.append(target)
    return frozenset(closure.keys()), closure  # ids y mapa id a State


def move(state_map: dict, symbol) -> dict:
    """Devuelve los estados alcanzables desde state_map consumiendo symbol."""
    result = {}
    for s in state_map.values():
        for t in s.transitions.get(symbol, []):
            result[t.id] = t
        for sym, targets in s.transitions.items():
            if isinstance(sym, frozenset) and symbol in sym:
                for t in targets:
                    result[t.id] = t
    return result


class DFAState:
    _id_counter = 0

    def __init__(self, nfa_id_set: frozenset):
        self.id          = DFAState._id_counter
        DFAState._id_counter += 1
        self.nfa_ids     = nfa_id_set
        self.transitions = {}
        self.is_accept   = False
        self.token_name  = None

    def __repr__(self):
        t = f"[{self.token_name}]" if self.is_accept else ""
        return f"D{self.id}{t}"


def _get_alphabet_from_nfa(start: State) -> set:
    alphabet, visited = set(), set()
    queue = [start]
    while queue:
        s = queue.pop()
        if s.id in visited: continue
        visited.add(s.id)
        for sym, targets in s.transitions.items():
            if sym != EPSILON:
                if isinstance(sym, frozenset):
                    alphabet.update(sym)
                else:
                    alphabet.add(sym)
            for t in targets:
                if t.id not in visited:
                    queue.append(t)
    return alphabet


def nfa_to_dfa(nfa_start: State, nfa_accept_list: list) -> tuple:
    """
    nfa_accept_list: [(State, priority, token_name), ...]
    Devuelve (dfa_start, list_of_DFAState).
    """
    DFAState._id_counter = 0
    alphabet = _get_alphabet_from_nfa(nfa_start)
    accept_map = {s.id: (prio, tok) for s, prio, tok in nfa_accept_list}

    ids0, map0 = epsilon_closure([nfa_start])
    dfa_start  = DFAState(ids0)
    _mark_accept(dfa_start, accept_map)

    unmarked   = [dfa_start]
    dfa_by_ids = {ids0: dfa_start}
    nfa_map_store = {ids0: map0}

    while unmarked:
        dfa_s   = unmarked.pop(0)
        cur_map = nfa_map_store[dfa_s.nfa_ids]

        for sym in sorted(alphabet, key=str):
            reached = move(cur_map, sym)
            if not reached: continue
            cls_ids, cls_map = epsilon_closure(list(reached.values()))
            if cls_ids not in dfa_by_ids:
                new_s = DFAState(cls_ids)
                _mark_accept(new_s, accept_map)
                dfa_by_ids[cls_ids]    = new_s
                nfa_map_store[cls_ids] = cls_map
                unmarked.append(new_s)
            dfa_s.transitions[sym] = dfa_by_ids[cls_ids]

    return dfa_start, list(dfa_by_ids.values())


def _mark_accept(dfa_s: DFAState, accept_map: dict):
    best = None
    for nid in dfa_s.nfa_ids:
        if nid in accept_map:
            prio, tok = accept_map[nid]
            if best is None or prio < best:
                best = prio
                dfa_s.is_accept  = True
                dfa_s.token_name = tok


def minimize_dfa(dfa_start: DFAState, all_states: list) -> tuple:
    DFAState._id_counter = 0

    groups = {}
    for s in all_states:
        key = s.token_name if s.is_accept else "__reject__"
        groups.setdefault(key, set()).add(s.id)

    partitions = [frozenset(g) for g in groups.values()]
    id_to_state = {s.id: s for s in all_states}

    def get_part(sid):
        for i, p in enumerate(partitions):
            if sid in p: return i
        return -1

    changed = True
    while changed:
        changed = False
        new_parts = []
        for group in partitions:
            split = _split(group, id_to_state, get_part)
            if len(split) > 1: changed = True
            new_parts.extend(split)
        partitions = new_parts
        _part_map = {}
        for i, p in enumerate(partitions):
            for sid in p: _part_map[sid] = i
        def get_part(sid, pm=_part_map): return pm.get(sid, -1)

    min_states = []
    part_id_map = {}
    for i, group in enumerate(partitions):
        rep = id_to_state[next(iter(group))]
        ms  = DFAState(rep.nfa_ids)
        ms.id         = i
        ms.is_accept  = rep.is_accept
        ms.token_name = rep.token_name
        min_states.append(ms)
        for sid in group: part_id_map[sid] = i

    for i, group in enumerate(partitions):
        rep = id_to_state[next(iter(group))]
        for sym, tgt in rep.transitions.items():
            j = part_id_map[tgt.id]
            min_states[i].transitions[sym] = min_states[j]

    start_part = part_id_map[dfa_start.id]
    return min_states[start_part], min_states


def _split(group: frozenset, id_to_state: dict, get_part) -> list:
    if len(group) == 1:
        return [group]
    sig_map = {}
    for sid in group:
        s   = id_to_state[sid]
        sig = tuple(sorted((sym, get_part(tgt.id)) for sym, tgt in s.transitions.items()))
        sig_map.setdefault(sig, set()).add(sid)
    return [frozenset(v) for v in sig_map.values()]
