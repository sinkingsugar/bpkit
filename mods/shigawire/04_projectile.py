"""Shigawire build step 04 -- the LAUNCH TECH on BP_SW_HookProjectile.

The pull is split into a consistent horizontal zip toward the hook + a shaped/clamped
vertical pop, so what you hit decides the launch (cook-tuned via sw_config):

    delta      = impactLoc - instLoc                       (impact = the embedded hook)
    horizontal = Normalize( MakeVector(delta.X, delta.Y, 0) ) * HORIZ_SPEED
    vertical   = MapRangeClamped( Abs(delta.Z), 0..DZ_REF, UP_MIN..UP_MAX )
    LaunchCharacter( MakeVector(horiz.X, horiz.Y, vertical), xy=T, z=T )

-> level wall = strong forward zip + modest pop; ledge above OR floor below = bigger
launch (Abs makes the floor pogo you UP); UP_MAX caps it so it's never orbit. Appended
to the projectile's StopProjectile event (fires when the hook embeds), server-gated.

Self-resetting: deletes + re-clones BP_SW_HookProjectile from the axe-projectile source
each run, so the logic is fully re-authorable while we tune. Run with Play STOPPED.
    python ue_run.py mods/shigawire/04_projectile.py
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
ACTOR = "/Script/Engine.Actor"
CHAR  = "/Script/Engine.Character"
CONAN = "/Script/ConanSandbox.ConanCharacter"
PAWN  = "/Script/Engine.Pawn"
KML   = "/Script/Engine.KismetMathLibrary"
VEC   = ir.struct_path("/Script/CoreUObject.Vector")
EAL   = unreal.EditorAssetLibrary

# self-reset: fresh clone from source so we can re-author the logic cleanly
if EAL.does_asset_exist(PATH):
    EAL.delete_asset(PATH)
if not EAL.duplicate_asset(MOD.SRC_PROJECTILE, PATH):
    print("ABORT: could not (re)clone", PATH); raise SystemExit
EAL.save_asset(PATH)
print("fresh clone:", PATH)

g = ir.Graph("EventGraph")
def vout(n, p): return n.pin(p).typed("struct", VEC, direction="EGPD_Output")
def vin(n, p):  return n.pin(p).typed("struct", VEC, direction="EGPD_Input")
def fpin(n, p, d):
    q = n.pin(p); q.dir = d
    q.set("PinType.PinCategory", '"real"'); q.set("PinType.PinSubCategory", '"double"')
    return q
def flit(n, p, v):
    q = fpin(n, p, "EGPD_Input"); q.set("DefaultValue", '"%s"' % v); return q
def selfctx(member, pos):
    return g.node("K2Node_CallFunction",
                  ['FunctionReference=(MemberName="%s",bSelfContext=True)' % member],
                  base="CallFunction", pos=pos)

# --- exec spine ---
branch = g.branch(pos=(900, 300))
auth   = selfctx("HasAuthority", pos=(560, 440)); auth.pin("ReturnValue").typed("bool", direction="EGPD_Output")
inst   = selfctx("GetInstigator", pos=(560, 540)); inst.pin("ReturnValue").typed("object", ir.obj_path(PAWN), direction="EGPD_Output")
cast   = g.cast(CONAN, pos=(1180, 300))
cast.pin("Object").typed("object", ir.obj_path(PAWN), direction="EGPD_Input")
cast.pin("AsConan Character").typed("object", ir.obj_path(CONAN), direction="EGPD_Output")

# --- locations ---
impLoc = selfctx("K2_GetActorLocation", pos=(1180, 640)); vout(impLoc, "ReturnValue")     # hook = projectile loc
insLoc = g.call("K2_GetActorLocation", ACTOR, pos=(1180, 760)); vout(insLoc, "ReturnValue")
insLoc.pin("self").typed("object", ir.obj_path(CONAN), direction="EGPD_Input")

# --- delta + break ---
delta  = g.call("Subtract_VectorVector", KML, pos=(1500, 700)); vin(delta, "A"); vin(delta, "B"); vout(delta, "ReturnValue")
brkD   = g.call("BreakVector", KML, pos=(1780, 700)); vin(brkD, "InVec")
fpin(brkD, "X", "EGPD_Output"); fpin(brkD, "Y", "EGPD_Output"); fpin(brkD, "Z", "EGPD_Output")

# --- horizontal: Normalize(flat) * HORIZ_SPEED, then break to X/Y ---
flat   = g.call("MakeVector", KML, pos=(2060, 560)); fpin(flat, "X", "EGPD_Input"); fpin(flat, "Y", "EGPD_Input"); flit(flat, "Z", 0); vout(flat, "ReturnValue")
norm   = g.call("Normal", KML, pos=(2320, 560)); vin(norm, "A"); vout(norm, "ReturnValue")
hvel   = g.call("Multiply_VectorFloat", KML, pos=(2580, 560)); vin(hvel, "A"); flit(hvel, "B", MOD.HORIZ_SPEED); vout(hvel, "ReturnValue")
brkH   = g.call("BreakVector", KML, pos=(2840, 560)); vin(brkH, "InVec")
fpin(brkH, "X", "EGPD_Output"); fpin(brkH, "Y", "EGPD_Output"); fpin(brkH, "Z", "EGPD_Output")

# --- vertical: MapRangeClamped(Abs(delta.Z), 0..DZ_REF, UP_MIN..UP_MAX) ---
absZ   = g.call("Abs", KML, pos=(2060, 840)); fpin(absZ, "A", "EGPD_Input"); fpin(absZ, "ReturnValue", "EGPD_Output")
mapped = g.call("MapRangeClamped", KML, pos=(2400, 840))
fpin(mapped, "Value", "EGPD_Input")
flit(mapped, "InRangeA", 0.0); flit(mapped, "InRangeB", MOD.DZ_REF)
flit(mapped, "OutRangeA", MOD.UP_MIN); flit(mapped, "OutRangeB", MOD.UP_MAX)
fpin(mapped, "ReturnValue", "EGPD_Output")

# --- compose launch vector + LaunchCharacter ---
lvec   = g.call("MakeVector", KML, pos=(2840, 740)); fpin(lvec, "X", "EGPD_Input"); fpin(lvec, "Y", "EGPD_Input"); fpin(lvec, "Z", "EGPD_Input"); vout(lvec, "ReturnValue")
launch = g.call("LaunchCharacter", CHAR, pos=(3120, 300))
launch.pin("self").typed("object", ir.obj_path(CHAR), direction="EGPD_Input"); vin(launch, "LaunchVelocity")
g.typed_input(launch, "bXYOverride", "true", "bool"); g.typed_input(launch, "bZOverride", "true", "bool")

# --- auto-return: give the LAUNCHER back to the thrower (server-side). The thrown weapon
# IS the consumable -- BP_ProjectileWeaponThrown.WeaponThrown decrements the weapon's stack
# and RemoveItem(self)s it; the ammo row (920141) is only the projectile DEFINITION, never an
# inventory item. So we refund WEAPON_TEMPLATE_ID (920140, real icon/name), NOT the ammo
# (920141 = the dev-icon "weird item" of the earlier attempt). SpawnTemplateItem(self=character,
# templateID, context) is the base projectile's proven grant; context must be a valid tag
# ("loot_ground"); an EMPTY context no-ops. The item lands in `self`'s inventory.
giveback = g.call("SpawnTemplateItem", CONAN, pos=(3460, 300))
giveback.pin("self").typed("object", ir.obj_path(CONAN), direction="EGPD_Input")
g.typed_input(giveback, "templateID", MOD.WEAPON_TEMPLATE_ID, "int")
g.typed_input(giveback, "context", "loot_ground", "name")

# --- wiring ---
g.wire(branch, "then", cast, "execute", exec=True)
g.wire(cast, "then", launch, "execute", exec=True)
g.wire(launch, "then", giveback, "execute", exec=True)   # ...then return the hook
g.wire(cast, "AsConan Character", giveback, "self", exec=False)
g.wire(auth, "ReturnValue", branch, "Condition", exec=False); branch.pin("Condition").typed("bool", direction="EGPD_Input")
g.wire(inst, "ReturnValue", cast, "Object", exec=False)
g.wire(cast, "AsConan Character", insLoc, "self", exec=False)
g.wire(cast, "AsConan Character", launch, "self", exec=False)
g.wire(impLoc, "ReturnValue", delta, "A", exec=False)
g.wire(insLoc, "ReturnValue", delta, "B", exec=False)
g.wire(delta, "ReturnValue", brkD, "InVec", exec=False)
g.wire(brkD, "X", flat, "X", exec=False)
g.wire(brkD, "Y", flat, "Y", exec=False)
g.wire(flat, "ReturnValue", norm, "A", exec=False)
g.wire(norm, "ReturnValue", hvel, "A", exec=False)
g.wire(hvel, "ReturnValue", brkH, "InVec", exec=False)
g.wire(brkH, "X", lvec, "X", exec=False)
g.wire(brkH, "Y", lvec, "Y", exec=False)
g.wire(brkD, "Z", absZ, "A", exec=False)
g.wire(absZ, "ReturnValue", mapped, "Value", exec=False)
g.wire(mapped, "ReturnValue", lvec, "Z", exec=False)
g.wire(lvec, "ReturnValue", launch, "LaunchVelocity", exec=False)

text = g.render()
res = bp.inject(FULL, text, graph_name="EventGraph", compile=False, save=False)
print("inject:", res, "authored:", text.count("Begin Object Class="))

# live-wire StopProjectile terminal (DestroyComponent) -> our branch
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
    print("StopProjectile-terminal -> branch:", bp.connect_pins(a, bpin) if (a and bpin) else "PINS MISSING")
else:
    print("!! terminal/branch not found:", bool(term_ptr), bool(branch_ptr))

bp.mark_structurally_modified(bp_ptr)
bp_obj = EAL.load_asset(PATH)
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)

# suppress the embedded "dummy projectile" pickup so nothing sticks in the world (the hook
# returns to inventory instead). Set on the CDO AFTER compile, then save (no recompile after).
cdo = unreal.get_default_object(bp_obj.generated_class())
cdo.set_editor_property("ShouldSpawnDummyProjectile", False)
EAL.save_asset(PATH)
print("ShouldSpawnDummyProjectile ->", cdo.get_editor_property("ShouldSpawnDummyProjectile"))

full_txt = bp.export_nodes(bp.graph_nodes(gptr))
orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', full_txt)
for fn in ("LaunchCharacter", "MapRangeClamped", "MakeVector", "BreakVector", "SpawnTemplateItem"):
    print("  has %-22s %s" % (fn, ('MemberName="%s"' % fn) in full_txt))
print("orphans:", sorted(set(orph)) if orph else "(clean)")
print("04 OK" if 'MemberName="LaunchCharacter"' in full_txt and not orph else "04 CHECK")
