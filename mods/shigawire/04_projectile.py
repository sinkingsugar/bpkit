"""Shigawire build step 04 -- the PULL on BP_SW_HookProjectile.

The cloned projectile is a BP_BaseProjectile child whose EventGraph has a StopProjectile
event (fires when the hook stops/embeds at impact: Event -> CallParent -> DestroyComponent).
We APPEND a server-gated pull after that terminal:

    HasAuthority? -> GetInstigator -> cast ConanCharacter
      -> launch_character( GetDirectionUnitVector(instLoc, impactLoc) * PULL_SPEED, xy=T, z=T )

i.e. fling the thrower toward where the hook bit. Ballistic feel (launch + gravity).
The enemy flinch (add_stagger) is a FAST FOLLOW (step 05) -- StopProjectile carries no hit
actor, so it needs a sphere-overlap; the pull is the make-or-break feel to validate first.

connect_pins live-wires the StopProjectile terminal -> our branch (paste only cross-links
within the pasted set; the pre-existing terminal needs a live wire -- manager pattern).
Run with Play STOPPED.   python ue_run.py mods/shigawire/04_projectile.py
"""
import sys, os, re
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import bridge as bp, ir, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "shigawire"))
sys.modules.pop("sw_config", None)
import sw_config as MOD

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: Play-in-Editor running."); raise SystemExit

PKG, NAME = MOD.OUTPUT_PKG, MOD.HOOK
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME

# idempotency: inject APPENDS, so skip if the pull is already authored (re-deploy safe).
# To re-author the logic, delete BP_SW_HookProjectile and redeploy from step 01.
_bp0, _g0 = bp.find_graph(FULL, "EventGraph")
if _g0 and 'MemberName="LaunchCharacter"' in bp.export_nodes(bp.graph_nodes(_g0)):
    print("04 SKIP: pull already authored on", NAME); raise SystemExit

ACTOR = "/Script/Engine.Actor"
CHAR  = "/Script/Engine.Character"
CONAN = "/Script/ConanSandbox.ConanCharacter"
PAWN  = "/Script/Engine.Pawn"
KML   = "/Script/Engine.KismetMathLibrary"
VEC   = ir.struct_path("/Script/CoreUObject.Vector")

g = ir.Graph("EventGraph")
def vout(n, p): return n.pin(p).typed("struct", VEC, direction="EGPD_Output")
def vin(n, p):  return n.pin(p).typed("struct", VEC, direction="EGPD_Input")
def selfctx(member, pos):
    return g.node("K2Node_CallFunction",
                  ['FunctionReference=(MemberName="%s",bSelfContext=True)' % member],
                  base="CallFunction", pos=pos)

# --- nodes ---
branch  = g.branch(pos=(900, 320))
auth    = selfctx("HasAuthority", pos=(560, 460))
auth.pin("ReturnValue").typed("bool", direction="EGPD_Output")
inst    = selfctx("GetInstigator", pos=(560, 560))
inst.pin("ReturnValue").typed("object", ir.obj_path(PAWN), direction="EGPD_Output")
cast    = g.cast(CONAN, pos=(1180, 320))
cast.pin("Object").typed("object", ir.obj_path(PAWN), direction="EGPD_Input")
cast.pin("AsConan Character").typed("object", ir.obj_path(CONAN), direction="EGPD_Output")
selfLoc = selfctx("K2_GetActorLocation", pos=(1180, 620)); vout(selfLoc, "ReturnValue")
instLoc = g.call("K2_GetActorLocation", ACTOR, pos=(1500, 720)); vout(instLoc, "ReturnValue")
instLoc.pin("self").typed("object", ir.obj_path(CONAN), direction="EGPD_Input")
dirN    = g.call("GetDirectionUnitVector", KML, pos=(1820, 660))
vin(dirN, "From"); vin(dirN, "To"); vout(dirN, "ReturnValue")
mul     = g.call("Multiply_VectorFloat", KML, pos=(2120, 620))
vin(mul, "A"); vout(mul, "ReturnValue")
b = mul.pin("B"); b.dir = "EGPD_Input"
b.set("PinType.PinCategory", '"real"'); b.set("PinType.PinSubCategory", '"double"')
b.set("DefaultValue", '"%s"' % MOD.PULL_SPEED)
launch  = g.call("LaunchCharacter", CHAR, pos=(2460, 320))
launch.pin("self").typed("object", ir.obj_path(CHAR), direction="EGPD_Input")
vin(launch, "LaunchVelocity")
g.typed_input(launch, "bXYOverride", "true", "bool")
g.typed_input(launch, "bZOverride", "true", "bool")

# --- wiring (exec: branch.then -> cast -> launch) ---
g.wire(branch, "then", cast, "execute", exec=True)
g.wire(cast, "then", launch, "execute", exec=True)
# data
g.wire(auth, "ReturnValue", branch, "Condition", exec=False)
g.wire(inst, "ReturnValue", cast, "Object", exec=False)
g.wire(cast, "AsConan Character", instLoc, "self", exec=False)
g.wire(cast, "AsConan Character", launch, "self", exec=False)
g.wire(instLoc, "ReturnValue", dirN, "From", exec=False)
g.wire(selfLoc, "ReturnValue", dirN, "To", exec=False)
g.wire(dirN, "ReturnValue", mul, "A", exec=False)
g.wire(mul, "ReturnValue", launch, "LaunchVelocity", exec=False)

text = g.render()
authored = text.count("Begin Object Class=")
res = bp.inject(FULL, text, graph_name="EventGraph", compile=False, save=False)
print("inject:", res, "authored:", authored)

# --- live-wire the StopProjectile terminal (DestroyComponent) -> our branch ---
bp_ptr, gptr = bp.find_graph(FULL, "EventGraph")
term_ptr = branch_ptr = None
for p in bp.graph_nodes(gptr):
    t = bp.export_nodes([p])
    if 'MemberName="K2_DestroyComponent"' in t:
        term_ptr = p
    elif "K2Node_IfThenElse" in t.splitlines()[0]:
        branch_ptr = p
if term_ptr and branch_ptr:
    a = bp.find_pin(term_ptr, "then", 1); bpin = bp.find_pin(branch_ptr, "execute", 0)
    print("StopProjectile-terminal -> branch wired:",
          bp.connect_pins(a, bpin) if (a and bpin) else "PINS MISSING")
else:
    print("!! terminal/branch not found:", bool(term_ptr), bool(branch_ptr))

bp.mark_structurally_modified(bp_ptr)
bp_obj = unreal.EditorAssetLibrary.load_asset(PATH)
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
unreal.EditorAssetLibrary.save_asset(PATH)

# --- verify: orphans + presence ---
full_txt = bp.export_nodes(bp.graph_nodes(gptr))
orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', full_txt)
print("LaunchCharacter present:", 'MemberName="LaunchCharacter"' in full_txt,
      "| GetDirectionUnitVector:", 'MemberName="GetDirectionUnitVector"' in full_txt)
print("orphans:", sorted(set(orph)) if orph else "(clean)")
print("04 OK" if 'MemberName="LaunchCharacter"' in full_txt and not orph else "04 CHECK")
