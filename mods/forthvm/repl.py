"""forthvm REPL (eval core): compile a Forth line, run it on the deployed BP_ForthVM,
print the result. This is the "type a line, run it now" loop bpkit-authored Blueprints
can't give you -- no editor, no recompile, just data. Each eval spawns a fresh VM
instance (empty stack).

    & $py ue_run.py mods/forthvm/repl.py "16.0 sqrt ."
    & $py ue_run.py mods/forthvm/repl.py "5.0 dup * ."
    & $py ue_run.py mods/forthvm/repl.py "1.0 2.0 3.0 vec3 ."

(A true in-game player REPL also needs the string->bytecode compiler IN Blueprint;
this host REPL proves the eval loop using the offline compiler + the deployed VM.)
"""
import sys, os
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "forthvm"))
for _m in ("config", "isa", "compiler"):
    sys.modules.pop(_m, None)
import config as MOD, compiler, isa

EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
src = " ".join(_cfg.argv()) or "16.0 sqrt ."
print("forth>", src)

prog = compiler.compile_source(src)
clsobj = MOD.OUTPUT_PKG + "/" + MOD.VM + "." + MOD.VM + "_C"
gc = unreal.load_object(None, clsobj)
if not gc:
    print("ABORT: %s not found -- run build_vm.py first" % clsobj); raise SystemExit
inst = EAS.spawn_actor_from_class(gc, unreal.Vector(0, 0, 0))
inst.set_editor_property("Code", prog.code)
inst.set_editor_property("Floats", prog.floats)
inst.set_editor_property("IP", 0)
inst.set_editor_property("Running", True)
steps = 0
while inst.get_editor_property("Running") and steps < 100000:   # the per-frame budget, here unbounded
    inst.call_method("Step")
    steps += 1
out, outv = inst.get_editor_property("Out"), inst.get_editor_property("OutV")
EAS.destroy_actor(inst)

print("  bytecode:", prog.code, "floats:", prog.floats)
print("  => Out=%s  OutV=(%.3f, %.3f, %.3f)   [%d steps]" % (out, outv.x, outv.y, outv.z, steps))
