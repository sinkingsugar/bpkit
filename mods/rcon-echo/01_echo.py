"""rcon-echo build: BP_RconEchoCmd : RconCommandObject + BP_RconEchoController : ModController.

The cooked-game proof of the RCON->BP receive channel (docs/CONAN-NOTES.md §Network):
  RconCommand(world, args) override -> Output = "ECHO: " + Join(args, " "), ReturnValue = true
  (the returned string goes back to the RCON client; ReturnValue=true marks success).
The controller exists ONLY to hard-reference the command class so it is in the cooked
load chain -- the plugin's BP-subclass discovery is the thing this mod exists to test.

Authoring notes (each cost an iteration on 2026-06-11; details docs/INTERNALS.md §9):
 - the override graph MUST be built with bridge.create_function_override (a pasted
   FunctionEntry can never become an override -- PostPasteNode rewrites it);
 - logic nodes are pasted ONE PER IMPORT (a 3-node unwired set silently dropped 2);
 - wires to the entry/result terminators use bridge.connect_pins (cross-set);
 - ReturnValue=true comes from Not_PreBool(false) -- a bool pin default that differs
   from its autogen value silently reverts (the v29 lesson), a wire can't;
 - the editor-python smoke test must use call_method (name dispatch); the bound
   method calls the NATIVE UFunction directly and skips the BP override.

Run with Play STOPPED:  python ue_run.py mods/rcon-echo/01_echo.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
import os
import re as _re
from bpkit import bridge as bp, ir, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "rcon-echo"))
sys.modules.pop("re_config", None)
import re_config as MOD

KSL = "/Script/Engine.KismetStringLibrary"
KML = "/Script/Engine.KismetMathLibrary"
RCO_CLASS = "/Script/RconPlugin.RconCommandObject"

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert not les.is_in_play_in_editor(), "Play is running -- stop PIE before building"

# ---------------------------------------------------------------- command BP
cmd_bp, cmd_full = bp.scratch_blueprint(pkg=MOD.OUTPUT_PKG, name=MOD.CMD,
                                        parent=unreal.RconCommandObject)
print("command BP:", cmd_full)

bp_ptr, g_ptr = bp.create_function_override(cmd_bp, "RconCommand", RCO_CLASS)
unreal.BlueprintEditorLibrary.compile_blueprint(cmd_bp)

# logic nodes -- pasted individually (multi-node unwired sets drop nodes silently)
def paste_one(g_build):
    text = "".join(n.render() for n in g_build.nodes)
    n = bp.import_nodes(g_ptr, text)
    assert n == len(g_build.nodes), "paste dropped a node: %d/%d" % (n, len(g_build.nodes))

g1 = ir.Graph("RconCommand")
g1.typed_input(g1.call("JoinStringArray", KSL, pos=(-80, 380)), "Separator", " ", "string")
paste_one(g1)
g2 = ir.Graph("RconCommand")
g2.typed_input(g2.call("Concat_StrStr", KSL, pos=(180, 380)), "A", "ECHO: ", "string")
paste_one(g2)
g3 = ir.Graph("RconCommand")
g3.call("Not_PreBool", KML, pos=(180, 560))
paste_one(g3)

# classify live nodes (first line = the node's own class; body may quote other nodes)
ptr_of = {}
for p in bp.graph_nodes(g_ptr):
    t = bp.export_nodes([p])
    first = t.splitlines()[0]
    if "K2Node_FunctionEntry" in first:    ptr_of["entry"] = p
    elif "K2Node_FunctionResult" in first: ptr_of["result"] = p
    elif "JoinStringArray" in t:           ptr_of["join"] = p
    elif "Concat_StrStr" in t:             ptr_of["concat"] = p
    elif "Not_PreBool" in t:               ptr_of["not"] = p
assert len(ptr_of) == 5, "node classification incomplete: %s" % sorted(ptr_of)

def wire(sk, sp, dk, dp):
    a = bp.find_pin(ptr_of[sk], sp)
    b = bp.find_pin(ptr_of[dk], dp)
    assert a and b, "pin missing: %s.%s / %s.%s" % (sk, sp, dk, dp)
    assert bp.connect_pins(a, b), "wire refused: %s.%s -> %s.%s" % (sk, sp, dk, dp)

wire("entry", "args", "join", "SourceArray")     # entry exec->result is prewired
wire("join", "ReturnValue", "concat", "B")
wire("concat", "ReturnValue", "result", "Output")
wire("not", "ReturnValue", "result", "ReturnValue")

bp.mark_structurally_modified(bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(cmd_bp)

txt = bp.export_nodes(bp.graph_nodes(g_ptr))
errs = _re.findall(r'ErrorMsg="([^"]+)"', txt)
assert not errs, "compile errors: %s" % errs[:2]
assert "bOrphanedPin=True" not in txt, "orphaned pin -- a default/wire didn't merge"

cmd_gen = unreal.BlueprintEditorLibrary.generated_class(cmd_bp)
cdo = unreal.get_default_object(cmd_gen)
cdo.set_editor_property("rcon_command_name", MOD.CMD_NAME)
cdo.set_editor_property("rcon_help_string", MOD.CMD_HELP % MOD.VERSION)
unreal.BlueprintEditorLibrary.compile_blueprint(cmd_bp)
assert unreal.EditorAssetLibrary.save_asset(cmd_full.split(".")[0]), "save failed"

# editor-side smoke test: name-dispatched call must hit the BP override
w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
inst = unreal.new_object(cmd_gen)
out = inst.call_method("RconCommand", (w, ("self", "test")))
assert out == "ECHO: self test", "override did not run: %r" % out
print("command smoke test:", repr(out))

# ------------------------------------------------------------ controller BP
ctl_bp, ctl_full = bp.scratch_blueprint(pkg=MOD.OUTPUT_PKG, name=MOD.CONTROLLER,
                                        parent=unreal.ModController)
clsref = unreal.BlueprintEditorLibrary.get_class_reference_type(
    unreal.RconCommandObject.static_class())
unreal.BlueprintEditorLibrary.add_member_variable(ctl_bp, "EchoCmdClass", clsref)
intt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
unreal.BlueprintEditorLibrary.add_member_variable(ctl_bp, "EchoVersion", intt)
unreal.BlueprintEditorLibrary.compile_blueprint(ctl_bp)
ctl_gen = unreal.BlueprintEditorLibrary.generated_class(ctl_bp)
ctl_cdo = unreal.get_default_object(ctl_gen)
ctl_cdo.set_editor_property("EchoCmdClass", cmd_gen)   # the load-chain anchor
ctl_cdo.set_editor_property("EchoVersion", MOD.VERSION)
unreal.BlueprintEditorLibrary.compile_blueprint(ctl_bp)
assert unreal.EditorAssetLibrary.save_asset(ctl_full.split(".")[0]), "controller save failed"
print("controller BP:", ctl_full, "-> references", cmd_gen.get_name())

print("BUILD OK: rcon-echo v%d (%s + %s in %s)" % (
    MOD.VERSION, MOD.CMD, MOD.CONTROLLER, MOD.OUTPUT_PKG))
