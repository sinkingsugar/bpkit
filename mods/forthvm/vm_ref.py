"""forthvm reference VM -- the executable spec / oracle.

A pure-Python interpreter of the isa bytecode with the EXACT typed-cell semantics
the generated Blueprint must reproduce: polymorphic + - * with int->float
promotion, scalar*vec scaling, vec component ops. It's step-budgeted like the
in-game VM (Step(budget)) so the cooperative-coroutine design is validated here
first. A cell is (tag, value): value is int / float / bool / (x,y,z) tuple.
"""
import isa

NUM = (isa.CT_INT, isa.CT_FLOAT)


def _vec(t):
    return (float(t[0]), float(t[1]), float(t[2]))


class VM:
    def __init__(self, prog):
        self.code = prog.code
        self.floats = prog.floats
        self.vecs = prog.vecs
        self.data = []          # data stack of cells
        self.ret = []           # return stack of code addresses
        self.ip = 0
        self.running = True
        self.output = []        # cells printed by '.'

    # -- stack helpers
    def push(self, tag, val): self.data.append((tag, val))
    def pop(self): return self.data.pop()

    def _binnum(self, a, b, fi, ff):
        """apply integer op fi or float op ff with int->float promotion."""
        (ta, va), (tb, vb) = a, b
        if ta == isa.CT_INT and tb == isa.CT_INT:
            return (isa.CT_INT, fi(va, vb))
        return (isa.CT_FLOAT, ff(float(va), float(vb)))

    def _add(self, a, b):
        if a[0] == isa.CT_VEC and b[0] == isa.CT_VEC:
            return (isa.CT_VEC, tuple(x + y for x, y in zip(a[1], b[1])))
        if a[0] in NUM and b[0] in NUM:
            return self._binnum(a, b, lambda x, y: x + y, lambda x, y: x + y)
        raise TypeError("+ : %s %s" % (isa.CT_NAME[a[0]], isa.CT_NAME[b[0]]))

    def _sub(self, a, b):
        if a[0] == isa.CT_VEC and b[0] == isa.CT_VEC:
            return (isa.CT_VEC, tuple(x - y for x, y in zip(a[1], b[1])))
        if a[0] in NUM and b[0] in NUM:
            return self._binnum(a, b, lambda x, y: x - y, lambda x, y: x - y)
        raise TypeError("- : %s %s" % (isa.CT_NAME[a[0]], isa.CT_NAME[b[0]]))

    def _mul(self, a, b):
        # scalar * vec (either order) -> scaled vec
        if a[0] == isa.CT_VEC and b[0] in NUM:
            s = float(b[1]); return (isa.CT_VEC, tuple(x * s for x in a[1]))
        if b[0] == isa.CT_VEC and a[0] in NUM:
            s = float(a[1]); return (isa.CT_VEC, tuple(x * s for x in b[1]))
        if a[0] == isa.CT_VEC and b[0] == isa.CT_VEC:
            return (isa.CT_VEC, tuple(x * y for x, y in zip(a[1], b[1])))
        if a[0] in NUM and b[0] in NUM:
            return self._binnum(a, b, lambda x, y: x * y, lambda x, y: x * y)
        raise TypeError("* : %s %s" % (isa.CT_NAME[a[0]], isa.CT_NAME[b[0]]))

    def step(self, budget=100000):
        C = self.code
        while self.running and budget > 0:
            budget -= 1
            op = C[self.ip]; self.ip += 1
            if op == isa.HALT:
                self.running = False
            elif op == isa.LIT_INT:
                self.push(isa.CT_INT, C[self.ip]); self.ip += 1
            elif op == isa.LIT_FLOAT:
                self.push(isa.CT_FLOAT, self.floats[C[self.ip]]); self.ip += 1
            elif op == isa.LIT_VEC:
                self.push(isa.CT_VEC, _vec(self.vecs[C[self.ip]])); self.ip += 1
            elif op == isa.LIT_BOOL:
                self.push(isa.CT_BOOL, bool(C[self.ip])); self.ip += 1
            elif op == isa.DUP:
                self.data.append(self.data[-1])
            elif op == isa.DROP:
                self.pop()
            elif op == isa.SWAP:
                self.data[-1], self.data[-2] = self.data[-2], self.data[-1]
            elif op == isa.ADD:
                b = self.pop(); a = self.pop(); self.data.append(self._add(a, b))
            elif op == isa.SUB:
                b = self.pop(); a = self.pop(); self.data.append(self._sub(a, b))
            elif op == isa.MUL:
                b = self.pop(); a = self.pop(); self.data.append(self._mul(a, b))
            elif op == isa.MK_VEC:
                z = self.pop()[1]; y = self.pop()[1]; x = self.pop()[1]
                self.push(isa.CT_VEC, (float(x), float(y), float(z)))
            elif op == isa.VEC_XYZ:
                x, y, z = self.pop()[1]
                self.push(isa.CT_FLOAT, x); self.push(isa.CT_FLOAT, y); self.push(isa.CT_FLOAT, z)
            elif op == isa.PRINT:
                self.output.append(self.pop())
            elif op == isa.CALL:
                self.ret.append(self.ip + 1); self.ip = C[self.ip]
            elif op == isa.EXIT:
                self.ip = self.ret.pop()
            elif op == isa.BRANCH:
                self.ip = C[self.ip]
            elif op == isa.ZBRANCH:
                flag = self.pop()[1]; tgt = C[self.ip]; self.ip += 1
                if not flag:
                    self.ip = tgt
            else:
                raise RuntimeError("bad opcode %d @ %d" % (op, self.ip - 1))
        return self.running

    def run(self, max_steps=1000000):
        self.step(max_steps)
        return self


def run_source(src):
    import compiler
    return VM(compiler.compile_source(src)).run()
