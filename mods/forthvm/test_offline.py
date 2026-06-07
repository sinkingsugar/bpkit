"""Offline proof of the forthvm ISA + compiler + reference VM -- no editor.

    & $py mods/forthvm/test_offline.py

This is the executable spec: every case here is exactly what the bpkit-generated
Blueprint VM must reproduce. Run it before/after touching isa/compiler/vm_ref.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import isa, compiler, vm_ref

_res = []


def expect(name, ok, detail=""):
    _res.append((name, bool(ok), detail))


def near(a, b, eps=1e-6):
    return abs(a - b) <= eps


def vecnear(a, b, eps=1e-6):
    return all(near(x, y, eps) for x, y in zip(a, b))


def out(src):
    return vm_ref.run_source(src).output


# 1. colon def + float arithmetic: 5.0 square -> 25.0 (float)
o = out(": square dup * ;  5.0 square .")
expect("square 5.0 -> one output", len(o) == 1, repr(o))
expect("square 5.0 -> CT_FLOAT", o and o[0][0] == isa.CT_FLOAT)
expect("square 5.0 -> 25.0", o and near(o[0][1], 25.0), repr(o))

# 2. vector add: (1,0,0)+(0,1,0) -> (1,1,0)
o = out("1.0 0.0 0.0 vec3  0.0 1.0 0.0 vec3  + .")
expect("vec add -> CT_VEC", o and o[0][0] == isa.CT_VEC, repr(o))
expect("vec add -> (1,1,0)", o and vecnear(o[0][1], (1.0, 1.0, 0.0)), repr(o))

# 3. scalar * vector: 2.0 * (1,2,3) -> (2,4,6)
o = out("2.0  1.0 2.0 3.0 vec3  * .")
expect("scale vec -> CT_VEC", o and o[0][0] == isa.CT_VEC, repr(o))
expect("scale vec -> (2,4,6)", o and vecnear(o[0][1], (2.0, 4.0, 6.0)), repr(o))

# 4. pure int arithmetic stays int: 3 4 + -> 7 (int)
o = out("3 4 + .")
expect("int add stays CT_INT", o and o[0][0] == isa.CT_INT, repr(o))
expect("3 4 + -> 7", o and o[0][1] == 7, repr(o))

# 5. int->float promotion: 2 1.5 + -> 3.5 (float)
o = out("2 1.5 + .")
expect("mixed add promotes to CT_FLOAT", o and o[0][0] == isa.CT_FLOAT, repr(o))
expect("2 1.5 + -> 3.5", o and near(o[0][1], 3.5), repr(o))

# 6. swap changes operand order of a non-commutative op:
#    5 3 - -> 2   but   5 3 swap - -> 3-5 = -2
expect("5 3 - -> 2", out("5 3 - .")[0][1] == 2, repr(out("5 3 - .")))
o = out("5 3 swap - .")
expect("5 3 swap - -> -2", o and o[0][1] == -2, repr(o))

# 7. step-budget coroutine: a long-ish program completes across small budgets
prog = compiler.compile_source(": sq dup * ;  10.0 sq sq .")   # ((10^2)^2)=10000
vm = vm_ref.VM(prog)
ticks = 0
while vm.step(3):       # 3 instructions per "tick"
    ticks += 1
    if ticks > 10000:
        break
expect("budgeted run completes", not vm.running)
expect("budgeted run -> 10000.0", vm.output and near(vm.output[0][1], 10000.0), repr(vm.output))
expect("budgeted run took multiple ticks", ticks > 1, "ticks=%d" % ticks)

print("=== forthvm offline spec ===")
ok = sum(1 for _, k, _ in _res if k)
for name, k, detail in _res:
    print("  [%s] %s%s" % ("PASS" if k else "FAIL", name, ("  -- " + detail) if detail and not k else ""))
print("=== %d/%d passed ===" % (ok, len(_res)))
print("\nbytecode for ': square dup * ;  5.0 square .':")
print(compiler.compile_source(": square dup * ;  5.0 square .").dump())
sys.exit(0 if ok == len(_res) else 1)
