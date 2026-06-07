"""forthvm offline compiler: tiny Forth source -> flat bytecode + typed pools.

Compile happens OUTSIDE the editor (it's the string-heavy part); the in-game
Blueprint VM only consumes the result. Supports: int/float/vector literals,
the primitive words in isa.PRIMITIVES, and colon definitions ( : NAME ... ; ).
Control flow (IF/THEN, loops) is intentionally not in v1 -- the opcodes exist
(BRANCH/ZBRANCH) so it slots in later without an ISA change.

    prog = compile_source(": square dup * ;  5.0 square .")
    prog.code        # list[int]   -- opcode/operand stream, HALT-terminated
    prog.floats      # list[float] -- LIT_FLOAT pool
    prog.vecs        # list[(x,y,z)]-- LIT_VEC pool
    prog.words       # {name: addr}
"""
import isa


class Program:
    def __init__(self):
        self.code = []
        self.floats = []
        self.vecs = []
        self.words = {}        # name -> code address (colon defs)

    def _pool(self, lst, val):
        for i, v in enumerate(lst):
            if v == val:
                return i
        lst.append(val)
        return len(lst) - 1

    def emit(self, *ints):
        self.code.extend(ints)

    def dump(self):
        out, i, C = [], 0, self.code
        while i < len(C):
            op = C[i]
            name = isa.OPNAME.get(op, "?%d" % op)
            if op in isa.HAS_OPERAND:
                out.append("%4d: %-9s %d" % (i, name, C[i + 1])); i += 2
            else:
                out.append("%4d: %s" % (i, name)); i += 1
        return "\n".join(out)


def _is_int(tok):
    try:
        int(tok); return "." not in tok
    except ValueError:
        return False


def _is_float(tok):
    try:
        float(tok); return "." in tok
    except ValueError:
        return False


def tokenize(src):
    return src.replace("\n", " ").split()


def compile_source(src):
    p = Program()
    toks = tokenize(src)
    i, n = 0, len(toks)

    def compile_token(tok):
        if _is_int(tok):
            p.emit(isa.LIT_INT, int(tok))
        elif _is_float(tok):
            p.emit(isa.LIT_FLOAT, p._pool(p.floats, float(tok)))
        elif tok in ("true", "false"):
            p.emit(isa.LIT_BOOL, 1 if tok == "true" else 0)
        elif tok in p.words:
            p.emit(isa.CALL, p.words[tok])
        elif tok in isa.PRIMITIVES:
            p.emit(isa.PRIMITIVES[tok])
        else:
            raise SyntaxError("unknown word: %r" % tok)

    # PASS: walk tokens; colon defs compile a body terminated by EXIT, recorded
    # in the dictionary; top-level tokens compile into the main stream. Colon
    # bodies are emitted inline and jumped over so they don't run at definition.
    while i < n:
        tok = toks[i]
        if tok == ":":
            name = toks[i + 1]
            j = toks.index(";", i)          # body = toks[i+2 : j]
            skip = len(p.code)
            p.emit(isa.BRANCH, 0)           # jump over the definition body
            p.words[name] = len(p.code)     # word entry point
            for bt in toks[i + 2:j]:
                compile_token(bt)
            p.emit(isa.EXIT)
            p.code[skip + 1] = len(p.code)  # patch BRANCH target = after body
            i = j + 1
        else:
            compile_token(tok)
            i += 1

    p.emit(isa.HALT)
    return p
