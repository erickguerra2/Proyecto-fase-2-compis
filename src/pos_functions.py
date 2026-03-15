"""
Calcula nullable, firstpos, lastpos y followpos para el árbol de expresión.
"""


class Node:
    def __init__(self, label, kind, sym_label=None):
        self.nid       = 0
        self.label     = label
        self.kind      = kind       
        self.sym_label = sym_label or label
        self.children  = []
        self.pos       = None        # solo hojas
        self.nullable  = False
        self.firstpos  = frozenset()
        self.lastpos   = frozenset()


def build_tree(postfix: list):
    # construye el árbol desde el postfix y agrega el #
    stack = []
    pos_counter = [0]

    def new_leaf(label):
        n = Node(label, 'leaf')
        pos_counter[0] += 1
        n.pos = pos_counter[0]
        return n

    def new_op(label, children):
        n = Node(label, 'op')
        n.children = children
        return n

    for tok in postfix:
        kind = tok[0]
        if kind == 'CHAR':
            c = tok[1]
            safe = c.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t')
            stack.append(new_leaf(safe))
        elif kind == 'SET':
            s = sorted(tok[1])
            lbl = f"{s[0]}-{s[-1]}" if len(s) > 6 else '[' + ''.join(s) + ']'
            stack.append(new_leaf(lbl))
        elif kind == 'ANY':
            stack.append(new_leaf('_'))
        elif kind == 'EOF':
            stack.append(new_leaf('eof'))
        elif kind == 'OP':
            op = tok[1]
            if op in ('*', '+', '?'):
                child = stack.pop() if stack else new_leaf('?')
                stack.append(new_op(op, [child]))
            else:
                right = stack.pop() if stack else new_leaf('?')
                left  = stack.pop() if stack else new_leaf('?')
                stack.append(new_op(op, [left, right]))

    root = stack.pop() if stack else Node('?', 'op')

    # concatena el # al final
    end = Node('#', 'leaf')
    pos_counter[0] += 1
    end.pos = pos_counter[0]
    root_with_end = new_op('·', [root, end])

    # asigna ids a todos los nodos
    _assign_ids(root_with_end, [0])
    return root_with_end, pos_counter[0]


def _assign_ids(node: Node, counter: list):
    counter[0] += 1
    node.nid = counter[0]
    for child in node.children:
        _assign_ids(child, counter)


def compute_nullable_first_last(node: Node):
    # sube de hojas a raíz viendo nullable, firstpos y lastpos
    for child in node.children:
        compute_nullable_first_last(child)

    if node.kind == 'leaf':
        if node.label == 'ε':
            node.nullable = True
            node.firstpos = frozenset()
            node.lastpos  = frozenset()
        else:
            node.nullable = False
            node.firstpos = frozenset({node.pos})
            node.lastpos  = frozenset({node.pos})

    elif node.label == '|':
        c1, c2 = node.children
        node.nullable = c1.nullable or c2.nullable
        node.firstpos = c1.firstpos | c2.firstpos
        node.lastpos  = c1.lastpos  | c2.lastpos

    elif node.label == '·':
        if len(node.children) == 2:
            c1, c2 = node.children
            node.nullable = c1.nullable and c2.nullable
            node.firstpos = c1.firstpos | c2.firstpos if c1.nullable else c1.firstpos
            node.lastpos  = c1.lastpos  | c2.lastpos  if c2.nullable else c2.lastpos

    elif node.label in ('*', '?'):
        if node.children:
            c = node.children[0]
            node.nullable = True
            node.firstpos = c.firstpos
            node.lastpos  = c.lastpos

    elif node.label == '+':
        if node.children:
            c = node.children[0]
            node.nullable = c.nullable
            node.firstpos = c.firstpos
            node.lastpos  = c.lastpos


def compute_followpos(node: Node, followpos: dict):
    # calcula followpos en nodos de concatenación y loops
    if node.label == '·' and len(node.children) == 2:
        c1, c2 = node.children
        for p in c1.lastpos:
            followpos[p] |= c2.firstpos

    elif node.label in ('*', '+') and node.children:
        c = node.children[0]
        for p in c.lastpos:
            followpos[p] |= c.firstpos

    for child in node.children:
        compute_followpos(child, followpos)


def collect_leaves(node: Node) -> list:
    # agarra todas las hojas en orden de izquierda a derecha
    if node.kind == 'leaf':
        return [node]
    result = []
    for child in node.children:
        result.extend(collect_leaves(child))
    return result


def analyze(postfix: list):
    # postfix a árbol a los pos
    root, total_pos = build_tree(postfix)
    compute_nullable_first_last(root)
    followpos = {i: set() for i in range(1, total_pos + 1)}
    compute_followpos(root, followpos)
    leaves = collect_leaves(root)
    return root, followpos, leaves