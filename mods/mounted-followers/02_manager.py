"""C2 manager build (evolving). BP_MountedFollowerManager : ModController.
ReceiveTick:
  - cast player (ConanCharacter); skip the tick if not ready
  - Seq.0: init-guard -> raise 'Mount' cap once (Initialized bool)
  - Seq.1: mount-transition detect -> print MOUNT / DISMOUNT (Step C hangs the
    match+stow / restore here); track WasMounted bool
Run with Play STOPPED.  Run: python ue_run.py mods/mounted-followers/02_manager.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
import os
from bpkit import bridge as bp, ir, compact as bc, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "mounted-followers"))
sys.modules.pop("mf_config", None)
import mf_config as MOD

PKG, NAME = MOD.OUTPUT_PKG, MOD.MANAGER
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
CONAN = "/Script/ConanSandbox.ConanCharacter"
TSC = "/Script/ConanSandbox.ThrallSystemComponent"
GS = "/Script/Engine.GameplayStatics"
KSL = "/Script/Engine.KismetSystemLibrary"
KML = "/Script/Engine.KismetMathLibrary"
KSTR = "/Script/Engine.KismetStringLibrary"
KARR = "/Script/Engine.KismetArrayLibrary"

# edit in place (reuse if present) -- deleting+recreating leaves a stale redirector
# that blocks recreate; the manager uses override EVENTS (not custom events) so
# clear+reinject is safe (no collision-rename).
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL)
boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
for vn in ("Initialized", "WasMounted"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, boolt)
# build-version tag (CDO default set below) to detect which class actually spawns
intt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
for vn in ("MgrVersion", "DbgCount"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, intt)  # no-ops if exists
# C2 action state: SpareHorse (the mount we stow humanoids onto), SavedMeshXform (rider
# mesh's relative-to-capsule xform saved at stow, restored at dismount so it doesn't float),
# MountIdleAnim (the seated idle pose; CDO default set below). One SavedMeshXform var is fine
# for one humanoid follower; per-rider state is a C3/multi-follower polish item.
conan_ref = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.ConanCharacter.static_class())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "SpareHorse", conan_ref)
# PlayerMount: the horse the player is riding (found by get_rider scan; null when on foot).
# Reliable mount detector -- GetMountInput lags/flakes across mount cycles.
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "PlayerMount", conan_ref)
# C3: distinct horse per follower -> a list of unridden spare horses, indexed by a humanoid
# counter (humanoid #i -> SpareHorses[i]); index-alignment guarantees no two share a horse.
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "SpareHorses",
    unreal.BlueprintEditorLibrary.get_array_type(conan_ref))
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "HumanoidCounter", intt)
xform_t = unreal.BlueprintEditorLibrary.get_struct_type(unreal.Transform.static_struct())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "SavedMeshXform", xform_t)
anim_ref = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.AnimSequence.static_class())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "MountIdleAnim", anim_ref)
ANIM = MOD.IDLE_ANIM

g = ir.Graph("EventGraph")

def cast_node(target, pos):
    return g.node("K2Node_DynamicCast",
                  ['TargetType="/Script/CoreUObject.Class\'%s\'"' % target], base="DynamicCast", pos=pos)

def seq_node(pos):
    return g.node("K2Node_ExecutionSequence", [], base="Seq", pos=pos)

def dbg(msg, pos):
    """A PrintString of a literal; returns the node (wire exec in/out via execute/then)."""
    p = g.call("PrintString", KSL, pos=pos)
    g.typed_input(p, "InString", msg, "string")
    return p

def dbg_int(label, src_node, src_pin, pos):
    """Print '<label><int>' by Conv_IntToString + Concat_StrStr -> PrintString."""
    conv = g.call("Conv_IntToString", KSTR, pos=(pos[0], pos[1] + 140))
    g.wire(src_node, src_pin, conv, "InInt", exec=False)
    cat = g.call("Concat_StrStr", KSTR, pos=(pos[0], pos[1] + 280))
    g.typed_input(cat, "A", label, "string")
    g.wire(conv, "ReturnValue", cat, "B", exec=False)
    p = g.call("PrintString", KSL, pos=pos)
    g.wire(cat, "ReturnValue", p, "InString", exec=False)
    return p

# --- C1 attach/restore node helpers (replicated; reuse the proven Stow/Restore pattern) ---
CHAR = "/Script/Engine.Character"
SMC = "/Script/Engine.SkeletalMeshComponent"
SCENE = "/Script/Engine.SceneComponent"
CMC = "/Script/Engine.CharacterMovementComponent"
ACTOR = "/Script/Engine.Actor"
CLS = {"Mesh": SMC, "CharacterMovement": CMC,
       "CapsuleComponent": "/Script/Engine.CapsuleComponent", "SpareHorse": CONAN,
       "PlayerMount": CONAN, "MountIdleAnim": "/Script/Engine.AnimSequence"}
STRUCTS = {"SavedMeshXform": "/Script/CoreUObject.Transform"}
ENUM = {
    "EAttachmentRule": "/Script/CoreUObject.Enum'/Script/Engine.EAttachmentRule'",
    "EAnimationMode":  "/Script/CoreUObject.Enum'/Script/Engine.EAnimationMode'",
    "EMovementMode":   "/Script/CoreUObject.Enum'/Script/Engine.EMovementMode'",
    "EDetachmentRule": "/Script/CoreUObject.Enum'/Script/Engine.EDetachmentRule'",
}
def type_obj(pin, cls_path):
    pin.set("PinType.PinCategory", '"object"')
    pin.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.Class'%s'" % cls_path)
def type_struct(pin, struct_path):
    pin.set("PinType.PinCategory", '"struct"')
    pin.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.ScriptStruct'%s'" % struct_path)
def type_var_pin(pin, name):
    type_struct(pin, STRUCTS[name]) if name in STRUCTS else type_obj(pin, CLS[name])
def var_self(name, pos):
    n = g.node("K2Node_VariableGet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableGet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Output"; type_var_pin(p, name); return n
def var_set_m(name, pos):
    n = g.node("K2Node_VariableSet", ['VariableReference=(MemberName="%s",bSelfContext=True)' % name],
               base="VariableSet", pos=pos)
    p = n.pin(name); p.dir = "EGPD_Input"; type_var_pin(p, name); return n
def comp_of(target, target_pin, comp_var, pos, parent=CHAR):
    """Read a component (Mesh/CharacterMovement/Capsule) off `target`'s output pin."""
    n = g.node("K2Node_VariableGet",
               ['VariableReference=(MemberName="%s",MemberParent="/Script/CoreUObject.Class\'%s\'",bSelfContext=False)'
                % (comp_var, parent)], base="VariableGet", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"; type_obj(sp, parent)
    op = n.pin(comp_var); op.dir = "EGPD_Output"; type_obj(op, CLS[comp_var])
    g.wire(target, target_pin, n, "self", exec=False); return n
def set_default(node, pin, value, category, enum=None):
    p = node.pin(pin); p.dir = "EGPD_Input"
    p.set("PinType.PinCategory", '"%s"' % category)
    if enum: p.set("PinType.PinSubCategoryObject", ENUM[enum])
    p.set("DefaultValue", '"%s"' % value)
def bare_call(member, parent, pos):
    return g.call(member, parent, pos=pos)
def attach_node(pos, socket, rules="SnapToTarget"):
    n = bare_call("K2_AttachToComponent", SCENE, pos)
    set_default(n, "SocketName", socket, "name")
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EAttachmentRule")
    set_default(n, "bWeldSimulatedBodies", "false", "bool")
    return n
def actor_attach(pos, socket, rules="SnapToTarget"):
    """AActor::K2_AttachToComponent -- attaches the ACTOR (its root) to a parent component.
    Actor attachment REPLICATES (unlike component/mesh attachment), so clients see the rider."""
    n = bare_call("K2_AttachToComponent", ACTOR, pos)
    set_default(n, "SocketName", socket, "name")
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EAttachmentRule")
    set_default(n, "bWeldSimulatedBodies", "false", "bool")
    return n
def actor_detach(pos, rules="KeepWorld"):
    """AActor::K2_DetachFromActor -- the BP-callable detach (matches K2_AttachToComponent). Plain
    'DetachFromActor' is the C++ name and silently does nothing here -- cost the dismount bug."""
    n = bare_call("K2_DetachFromActor", ACTOR, pos)
    for r in ("LocationRule", "RotationRule", "ScaleRule"):
        set_default(n, r, rules, "byte", enum="EDetachmentRule")
    return n
class Chain(object):
    def __init__(self, start_node, start_pin):
        self.node, self.pin = start_node, start_pin
    def then(self, call_node, in_pin="execute", out_pin="then"):
        g.wire(self.node, self.pin, call_node, in_pin, exec=True)
        self.node, self.pin = call_node, out_pin; return call_node

# --- array-function helpers (validated by tests/test_array_nodes.py). Array funcs MUST be
# K2Node_CallArrayFunction (NOT plain CallFunction) with a fully-typed TargetArray, else the
# wildcard never resolves -> "Target Array is undetermined" compile fail. ---
KARRC = "/Script/Engine.KismetArrayLibrary"
def _stype(pin, cat, sub=None, container=None, ref=False, const=False):
    pin.set("PinType.PinCategory", '"%s"' % cat)
    if sub: pin.set("PinType.PinSubCategoryObject", sub)
    if container: pin.set("PinType.ContainerType", container)
    if ref: pin.set("PinType.bIsReference", "True")
    if const: pin.set("PinType.bIsConst", "True")
def arr_fn(member, elem_sub, pos):
    n = g.node("K2Node_CallArrayFunction",
        ['FunctionReference=(MemberParent="%s",MemberName="%s")' % (ir.obj_path(KARRC), member)],
        base="ArrFn", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"; _stype(sp, "object", ir.obj_path(KARRC))
    sp.set("DefaultObject", "/Script/Engine.Default__KismetArrayLibrary"); sp.set("bHidden", "True")
    tp = n.pin("TargetArray"); tp.dir = "EGPD_Input"
    _stype(tp, "object", elem_sub, "Array", ref=True, const=True); tp.set("bDefaultValueIsIgnored", "True")
    return n
def arr_var(name, elem_sub, pos):
    n = g.var_get(name, "object", elem_sub, pos=pos)
    n.pin(name).set("PinType.ContainerType", "Array"); return n
def get_item(arr_node, arr_pin, idx_node, idx_pin, elem_sub, pos):
    n = g.node("K2Node_GetArrayItem", ["bReturnByRefDesired=False"], base="GetItem", pos=pos)
    ap = n.pin("Array"); ap.dir = "EGPD_Input"; _stype(ap, "object", elem_sub, "Array")
    ip = n.pin("Dimension 1"); ip.dir = "EGPD_Input"; _stype(ip, "int")
    op = n.pin("Output"); op.dir = "EGPD_Output"; _stype(op, "object", elem_sub)
    g.wire(arr_node, arr_pin, n, "Array", exec=False)
    g.wire(idx_node, idx_pin, n, "Dimension 1", exec=False)
    return n
def get_all_actors(cls_path, pos):
    """GameplayStatics.GetAllActorsOfClass(cls_path) -> OutActors (object array). ActorClass is a
    class-wrapper pin set via DefaultObject; OutActors typed to the class."""
    n = g.call("GetAllActorsOfClass", GS, pos=pos)
    ap = n.pin("ActorClass"); ap.dir = "EGPD_Input"
    ap.set("PinType.PinCategory", '"class"')
    ap.set("PinType.PinSubCategoryObject", "/Script/CoreUObject.Class'/Script/Engine.Actor'")
    ap.set("PinType.bIsUObjectWrapper", "True"); ap.set("DefaultObject", '"%s"' % cls_path)  # MUST be quoted, else ActorClass=null -> 0 results
    # OutActors is Actor-typed (the wildcard output won't take a narrower type on paste); the
    # runtime ActorClass default still filters to cls_path, so contents are cls_path instances.
    op = n.pin("OutActors"); op.dir = "EGPD_Output"
    _stype(op, "object", "/Script/CoreUObject.Class'/Script/Engine.Actor'", "Array")
    return n
def mc_event(name, pos):
    """A NetMulticast (reliable) custom event. FunctionFlags 201474240 = the exact value a real
    Multicast event uses (from BP_BatDemonGlider's MulticastFlapUpwards in the dumps)."""
    n = g.node("K2Node_CustomEvent",
               ['CustomFunctionName="%s"' % name, "FunctionFlags=201474240"], base="CustomEvent", pos=pos)
    tp = n.pin("then"); tp.dir = "EGPD_Output"; tp.set("PinType.PinCategory", '"exec"')
    return n

# === COSMETIC SEAT loop -- driven NON-GATED from ReceiveTick below, so it runs on EVERY instance
# (server + all clients). Now that the manager is Always Relevant it actually exists + ticks on
# clients, so this applies the seated single-node anim LOCALLY on each client. (v14 logic, which was
# correct -- it just never ran on clients because the manager wasn't relevant.) ===
gaC = get_all_actors(CONAN, (300, -1300))
loopMC = g.foreach(ACTOR, pos=(550, -1300))
g.wire(gaC, "OutActors", loopMC, "Array", exec=False)
g.wire(gaC, "then", loopMC, "Exec", exec=True)
castMC = cast_node(CONAN, (800, -1300))
g.wire(loopMC, "Array Element", castMC, "Object", exec=False)
g.wire(loopMC, "LoopBody", castMC, "execute", exec=True)
getParMC = g.call("GetAttachParentActor", ACTOR, pos=(1050, -1150))
g.wire(loopMC, "Array Element", getParMC, "self", exec=False)
parVMC = g.call("IsValid", KSL, pos=(1250, -1150))
g.wire(getParMC, "ReturnValue", parVMC, "Object", exec=False)
bAttMC = g.branch(pos=(1050, -1300))
g.wire(castMC, "then", bAttMC, "execute", exec=True)
g.wire(parVMC, "ReturnValue", bAttMC, "Condition", exec=False)
meshMC = comp_of(castMC, "AsConan Character", "Mesh", (1300, -1450))
amMC = bare_call("SetAnimationMode", SMC, (1300, -1300))
set_default(amMC, "InAnimationMode", "AnimationSingleNode", "byte", enum="EAnimationMode")
g.wire(meshMC, "Mesh", amMC, "self", exec=False)
# EXCLUDE THE PLAYER: a player pawn has a valid PlayerState on every instance (replicates), unlike
# IsPlayerControlled. (Players aren't actor-attached when mounted so they rarely hit this, but safe.)
getPSMC = g.call("GetPlayerState", "/Script/Engine.Pawn", pos=(1050, -1550))
g.wire(castMC, "AsConan Character", getPSMC, "self", exec=False)
isPlayerMC = g.call("IsValid", KSL, pos=(1180, -1550))
g.wire(getPSMC, "ReturnValue", isPlayerMC, "Object", exec=False)
bPlayerMC = g.branch(pos=(1280, -1300))
g.wire(bAttMC, "then", bPlayerMC, "execute", exec=True)
g.wire(isPlayerMC, "ReturnValue", bPlayerMC, "Condition", exec=False)
# EXCLUDE HORSES: a mounted creature is attached to its rider, so the loop saw it "attached" and
# applied the HUMAN mounted-idle anim to a HORSE skeleton -> broke the ridden horse -> player offset.
isMtblMC = g.call("IsMountable", CONAN, pos=(1280, -1150))
g.wire(castMC, "AsConan Character", isMtblMC, "self", exec=False)
bMtblMC = g.branch(pos=(1500, -1300))
g.wire(bPlayerMC, "else", bMtblMC, "execute", exec=True)
g.wire(isMtblMC, "ReturnValue", bMtblMC, "Condition", exec=False)
# SEAT ONLY IF THE ATTACH PARENT IS ONE OF OUR HORSES. The loop catches ANY attached,
# non-player, non-mountable character -- which wrongly seated thralls attached to benches /
# wheels of pain / stations (saddle pose -> visual offset). A mounted follower is attached to
# a horse (a ConanCharacter with IsMountable=true); a bench/placeable parent is neither. So
# cast the attach parent to ConanCharacter and require IsMountable before posing; a non-horse
# parent fails the cast (or IsMountable) and the character is left exactly as the game set it.
castParMC = cast_node(CONAN, (1700, -1500))
g.wire(getParMC, "ReturnValue", castParMC, "Object", exec=False)
g.wire(bMtblMC, "else", castParMC, "execute", exec=True)   # not player AND not mountable -> check parent
parMtblMC = g.call("IsMountable", CONAN, pos=(1900, -1500))
g.wire(castParMC, "AsConan Character", parMtblMC, "self", exec=False)
bParMtblMC = g.branch(pos=(1750, -1300))   # cast-fail (parent not a ConanCharacter) dead-ends -> skip
g.wire(castParMC, "then", bParMtblMC, "execute", exec=True)
g.wire(parMtblMC, "ReturnValue", bParMtblMC, "Condition", exec=False)
g.wire(bParMtblMC, "then", amMC, "execute", exec=True)   # parent IS a mountable horse -> seat
plMC = bare_call("PlayAnimation", SMC, (1550, -1300))
set_default(plMC, "bLooping", "true", "bool")
animMC = var_self("MountIdleAnim", (1300, -1600))
g.wire(animMC, "MountIdleAnim", plMC, "NewAnimToPlay", exec=False)
g.wire(meshMC, "Mesh", plMC, "self", exec=False)
g.wire(amMC, "then", plMC, "execute", exec=True)
# RESET branch: not attached -> AnimBlueprint. Un-seats dismounted followers on CLIENTS (Pass D's
# server-side reset doesn't replicate). CRITICAL: bForceInitAnimScriptInstance=FALSE. The default
# (true) RE-INITS the AnimBP on EVERY call even when the mode is already AnimationBlueprint (the
# engine doc says so explicitly). Running this on every unattached ConanCharacter each tick
# therefore reinitialized EVERY character's AnimBP every frame -> all animations broke (player +
# thralls + NPCs). With force=false it's a genuine no-op unless the char is actually in SingleNode
# (a previously-seated follower), which it then restores exactly once.
amResetMC = bare_call("SetAnimationMode", SMC, (1500, -1100))
set_default(amResetMC, "InAnimationMode", "AnimationBlueprint", "byte", enum="EAnimationMode")
# bForceInitAnimScriptInstance MUST be false. A pin *default* for it silently reverts to the
# autogen 'true' on reconstruction (bp_ir bool-default gap -- verified: v28 shipped it as true,
# hence "no change"), so WIRE a literal false; a wired pin cannot revert. MakeLiteralBool with an
# unset Value returns false.
falseLit = g.call("MakeLiteralBool", KSL, pos=(1280, -1000))
g.wire(falseLit, "ReturnValue", amResetMC, "bForceInitAnimScriptInstance", exec=False)
g.wire(meshMC, "Mesh", amResetMC, "self", exec=False)
g.wire(bAttMC, "else", amResetMC, "execute", exec=True)

tick = g.event("ReceiveTick")
# Manager is Always Relevant, so it exists + ticks on every client. The cosmetic seat loop above is
# NON-gated (runs on every instance); the gameplay below is server-only (HasAuthority).
haz = g.call("HasAuthority", ACTOR, pos=(-250, 0))
bAuth = g.branch(pos=(-50, 0))
g.wire(tick, "then", gaC, "execute", exec=True)            # NON-GATED cosmetic seat loop (every instance)
g.wire(loopMC, "Completed", bAuth, "execute", exec=True)   # THEN the server-gated stow/gameplay
g.wire(haz, "ReturnValue", bAuth, "Condition", exec=False)
getP = g.call("GetPlayerCharacter", GS, pos=(0, 350))
g.typed_input(getP, "PlayerIndex", "0", "int")
cast = cast_node(CONAN, (250, 0))
g.wire(bAuth, "then", cast, "execute", exec=True)   # server only
g.wire(getP, "ReturnValue", cast, "Object", exec=False)
PLAYER = (cast, "AsConan Character")   # the casted player ConanCharacter output

seq = seq_node((550, 0))
g.wire(cast, "then", seq, "execute", exec=True)

# --- Seq.0: init-guard -> raise Mount cap once ---
getInit = g.var_get("Initialized", "bool", pos=(750, 250))
bInit = g.branch(pos=(950, 0))
g.wire(seq, "then_0", bInit, "execute", exec=True)
g.wire(getInit, "Initialized", bInit, "Condition", exec=False)
getTSC = g.call("GetThrallSystemComponent", CONAN, pos=(1150, 250))
g.wire(PLAYER[0], PLAYER[1], getTSC, "self", exec=False)
addAdj = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(1350, 0))
g.typed_input(addAdj, "Group", "Mount", "name")
g.typed_input(addAdj, "Amount", "5", "int")
g.wire(getTSC, "ReturnValue", addAdj, "self", exec=False)
g.wire(bInit, "else", addAdj, "execute", exec=True)
# ALSO raise EVERY humanoid-follower group cap -- thralls live in Warrior/Crafter/Bearer/
# Performer/Archer by type (MP showed a Crafter capped at 1). Additive/mod-safe; chained.
prev = addAdj
for gi, grp in enumerate(("Warrior", "Crafter", "Bearer", "Performer", "Archer")):
    a = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(1600 + gi * 260, 0))
    g.typed_input(a, "Group", grp, "name")
    g.typed_input(a, "Amount", "5", "int")
    g.wire(getTSC, "ReturnValue", a, "self", exec=False)
    g.wire(prev, "then", a, "execute", exec=True)
    prev = a
setInit = g.var_set("Initialized", "bool", pos=(1600 + 5 * 260, 0))
setInit.pin("Initialized").literal("true")
g.wire(prev, "then", setInit, "execute", exec=True)

# --- Seq.1: mount-transition detect via GET_RIDER SCAN (reliable across cycles) ---
# GetMountInput lags/flakes -- its BP_MountInput object is torn down + recreated each mount
# cycle, so IsValid reads false for a long window on remount (stow fired "after a lot of
# time"). get_rider on the mount is the stable ground truth. Each tick: scan the following
# horses; if one has the player as rider -> that's PlayerMount and we're mounted.
seq2 = seq_node((900, 500))
g.wire(seq, "then_1", seq2, "execute", exec=True)

getTSCd = g.call("GetThrallSystemComponent", CONAN, pos=(700, 700))
g.wire(PLAYER[0], PLAYER[1], getTSCd, "self", exec=False)
getFolD = g.call("GetFollowingThrallCharacters", TSC, pos=(900, 700))
g.wire(getTSCd, "ReturnValue", getFolD, "self", exec=False)
clrPM = var_set_m("PlayerMount", (1100, 500))   # null (value pin left unconnected)
g.wire(seq2, "then_0", clrPM, "execute", exec=True)
loopDet = g.foreach(CONAN, pos=(1300, 650))
g.wire(getFolD, "ReturnValue", loopDet, "Array", exec=False)
g.wire(clrPM, "then", loopDet, "Exec", exec=True)
getRiderDet = g.call("GetRider", CONAN, pos=(1550, 900))
g.wire(loopDet, "Array Element", getRiderDet, "self", exec=False)
eqDet = g.call("EqualEqual_ObjectObject", KML, pos=(1750, 900))
g.wire(getRiderDet, "ReturnValue", eqDet, "A", exec=False)
g.wire(PLAYER[0], PLAYER[1], eqDet, "B", exec=False)
bRiderDet = g.branch(pos=(1550, 650))
g.wire(loopDet, "LoopBody", bRiderDet, "execute", exec=True)
g.wire(eqDet, "ReturnValue", bRiderDet, "Condition", exec=False)
setPM = var_set_m("PlayerMount", (1800, 650))
g.wire(loopDet, "Array Element", setPM, "PlayerMount", exec=False)
g.wire(bRiderDet, "then", setPM, "execute", exec=True)   # this horse's rider == player -> our mount

# isMounted = IsValid(PlayerMount); transition fires after the scan completes
getPM = var_self("PlayerMount", (1300, 1000))
isMounted = g.call("IsValid", KSL, pos=(1550, 1100))
g.wire(getPM, "PlayerMount", isMounted, "Object", exec=False)
getWas = g.var_get("WasMounted", "bool", pos=(1550, 1250))
neq = g.call("NotEqual_BoolBool", KML, pos=(1800, 1150))
g.wire(isMounted, "ReturnValue", neq, "A", exec=False)
g.wire(getWas, "WasMounted", neq, "B", exec=False)
bChanged = g.branch(pos=(2050, 650))
g.wire(loopDet, "Completed", bChanged, "execute", exec=True)
g.wire(neq, "ReturnValue", bChanged, "Condition", exec=False)
bMounted = g.branch(pos=(2300, 650))
g.wire(bChanged, "then", bMounted, "execute", exec=True)
g.wire(isMounted, "ReturnValue", bMounted, "Condition", exec=False)
# MOUNT branch -- the real action (2-pass over followers):
#   Pass A: collect unridden spare horses -> SpareHorses[] (stagger each one's follow distance)
#   Pass B: stow each humanoid onto SpareHorses[counter] (C1 attach chain)
# shared follower source for both passes (one impure get fans out to both loops)
getTSC2 = g.call("GetThrallSystemComponent", CONAN, pos=(1850, 420))
g.wire(PLAYER[0], PLAYER[1], getTSC2, "self", exec=False)
getFol = g.call("GetFollowingThrallCharacters", TSC, pos=(2100, 420))
g.wire(getTSC2, "ReturnValue", getFol, "self", exec=False)

# clear SpareHorses + reset HumanoidCounter before (re)building the spare list each mount
clrArr = arr_fn("Array_Clear", ir.obj_path(CONAN), (1900, 250))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (1900, 470)), "SpareHorses", clrArr, "TargetArray", exec=False)
g.wire(bMounted, "then", clrArr, "execute", exec=True)
setHC0 = g.var_set("HumanoidCounter", "int", pos=(2150, 250)); setHC0.pin("HumanoidCounter").literal("0")
g.wire(clrArr, "then", setHC0, "execute", exec=True)

# PASS A: collect every UNRIDDEN mountable follower into SpareHorses[]
loopA = g.foreach(CONAN, pos=(2400, 250))
g.wire(getFol, "ReturnValue", loopA, "Array", exec=False)
g.wire(setHC0, "then", loopA, "Exec", exec=True)
mtblA = g.call("IsMountable", CONAN, pos=(2650, 480))
g.wire(loopA, "Array Element", mtblA, "self", exec=False)
bMtblA = g.branch(pos=(2650, 250))
g.wire(loopA, "LoopBody", bMtblA, "execute", exec=True)
g.wire(mtblA, "ReturnValue", bMtblA, "Condition", exec=False)
# EXCLUDE the horse the player is riding: a spare horse has NO rider (GetRider invalid).
getRiderA = g.call("GetRider", CONAN, pos=(2900, 480))
g.wire(loopA, "Array Element", getRiderA, "self", exec=False)
ridValA = g.call("IsValid", KSL, pos=(3100, 480))
g.wire(getRiderA, "ReturnValue", ridValA, "Object", exec=False)
bRiddenA = g.branch(pos=(2950, 250))
g.wire(bMtblA, "then", bRiddenA, "execute", exec=True)
g.wire(ridValA, "ReturnValue", bRiddenA, "Condition", exec=False)
addSpare = arr_fn("Array_Add", ir.obj_path(CONAN), (3200, 250))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (3200, 480)), "SpareHorses", addSpare, "TargetArray", exec=False)
niA = addSpare.pin("NewItem"); niA.dir = "EGPD_Input"; _stype(niA, "object", ir.obj_path(CONAN))
g.wire(loopA, "Array Element", addSpare, "NewItem", exec=False)
g.wire(bRiddenA, "else", addSpare, "execute", exec=True)   # mountable AND unridden -> add to SpareHorses
# SPACING: stagger this horse's follow distance by its loop index (index*180) so the horses
# trail in a line behind the player instead of all clustering on one follow point.
idxMul = g.call("Multiply_IntInt", KML, pos=(3450, 480))
g.wire(loopA, "Array Index", idxMul, "A", exec=False)
g.typed_input(idxMul, "B", "180", "int")
idxF = g.call("Conv_IntToDouble", KML, pos=(3650, 480))
g.wire(idxMul, "ReturnValue", idxF, "InInt", exec=False)
setDist = g.call("SetAdditionalFollowDistance", CONAN, pos=(3450, 250))
g.wire(loopA, "Array Element", setDist, "self", exec=False)
g.wire(idxF, "ReturnValue", setDist, "NewFollowDistance", exec=False)
g.wire(addSpare, "then", setDist, "execute", exec=True)

# PASS B: stow each NON-mountable (humanoid) follower onto SpareHorses[counter]
loopB = g.foreach(CONAN, pos=(2400, 750))
g.wire(getFol, "ReturnValue", loopB, "Array", exec=False)
g.wire(loopA, "Completed", loopB, "Exec", exec=True)
mtblB = g.call("IsMountable", CONAN, pos=(2650, 980))
g.wire(loopB, "Array Element", mtblB, "self", exec=False)
bMtblB = g.branch(pos=(2650, 750))
g.wire(loopB, "LoopBody", bMtblB, "execute", exec=True)
g.wire(mtblB, "ReturnValue", bMtblB, "Condition", exec=False)
# claim SpareHorses[HumanoidCounter]; only stow if that index actually holds a horse
hcGet = g.var_get("HumanoidCounter", "int", pos=(2900, 980))
arrGetB = arr_var("SpareHorses", ir.obj_path(CONAN), (2900, 1150))
horse = get_item(arrGetB, "SpareHorses", hcGet, "HumanoidCounter", ir.obj_path(CONAN), (3150, 1050))
# GUARD: counter < len(SpareHorses). (IsValid on the GetArrayItem Output pin won't merge via
# paste -- the bare Object pin doesn't take the special node's output type -- so use an in-range
# int test instead; GetArrayItem.Output still feeds the mesh getter, which DID connect.)
lenB = arr_fn("Array_Length", ir.obj_path(CONAN), (3150, 820))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (3150, 1000)), "SpareHorses", lenB, "TargetArray", exec=False)
lessB = g.call("Less_IntInt", KML, pos=(3350, 820))
g.wire(hcGet, "HumanoidCounter", lessB, "A", exec=False)
g.wire(lenB, "ReturnValue", lessB, "B", exec=False)
bHasHorse = g.branch(pos=(2950, 750))
g.wire(bMtblB, "else", bHasHorse, "execute", exec=True)   # NOT mountable -> humanoid
g.wire(lessB, "ReturnValue", bHasHorse, "Condition", exec=False)
# bHasHorse.then -> stow chain (counter in range -> this humanoid gets its OWN spare horse)

mMesh = comp_of(horse, "Output", "Mesh", (3550, 1150))   # spare horse mesh = attach parent
rMesh = comp_of(loopB, "Array Element", "Mesh", (3550, 950))   # rider mesh (for the seated pose)
rMove = comp_of(loopB, "Array Element", "CharacterMovement", (3550, 1350))
chain = Chain(bHasHorse, "then")
# ACTOR-attach the follower to the saddle -- actor attachment REPLICATES to clients
# (mesh/component attachment did not, which is what desynced MP).
attach = actor_attach((3850, 750), "attachrider")
g.wire(loopB, "Array Element", attach, "self", exec=False)   # the follower ACTOR
g.wire(mMesh, "Mesh", attach, "Parent", exec=False)
chain.then(attach)
# raise the body onto the saddle (root capsule snaps ~90 below the mesh)
setRel = bare_call("K2_SetActorRelativeLocation", ACTOR, (4100, 750))
relp = setRel.pin("NewRelativeLocation"); relp.dir = "EGPD_Input"
type_struct(relp, "/Script/CoreUObject.Vector"); relp.set("DefaultValue", '"0.000000,0.000000,90.000000"')
g.wire(loopB, "Array Element", setRel, "self", exec=False)
chain.then(setRel)
# correct the ~90deg yaw the 'attachrider' socket snaps to (relative rotation replicates with the
# attach). If it ends up flipped, swap -90 -> 90.
setRot = bare_call("K2_SetActorRelativeRotation", ACTOR, (4100, 950))
rotp = setRot.pin("NewRelativeRotation"); rotp.dir = "EGPD_Input"
type_struct(rotp, "/Script/CoreUObject.Rotator"); rotp.set("DefaultValue", '"0.000000,90.000000,0.000000"')
g.wire(loopB, "Array Element", setRot, "self", exec=False)
chain.then(setRot)
disable = bare_call("DisableMovement", CMC, (4350, 750))
g.wire(rMove, "CharacterMovement", disable, "self", exec=False)
chain.then(disable)
nocol = bare_call("SetActorEnableCollision", ACTOR, (4600, 750))
set_default(nocol, "bNewActorEnableCollision", "false", "bool")
g.wire(loopB, "Array Element", nocol, "self", exec=False)
chain.then(nocol)
amode = bare_call("SetAnimationMode", SMC, (4850, 750))
set_default(amode, "InAnimationMode", "AnimationSingleNode", "byte", enum="EAnimationMode")
g.wire(rMesh, "Mesh", amode, "self", exec=False)
chain.then(amode)
play = bare_call("PlayAnimation", SMC, (5100, 750))
set_default(play, "bLooping", "true", "bool")
animGet = var_self("MountIdleAnim", (4850, 1000))
g.wire(animGet, "MountIdleAnim", play, "NewAnimToPlay", exec=False)
g.wire(rMesh, "Mesh", play, "self", exec=False)
chain.then(play)
# advance the counter so the NEXT humanoid takes the NEXT spare horse -> distinct mounts
hcGet2 = g.var_get("HumanoidCounter", "int", pos=(5300, 1000))
addHC = g.call("Add_IntInt", KML, pos=(5300, 900)); g.wire(hcGet2, "HumanoidCounter", addHC, "A", exec=False)
g.typed_input(addHC, "B", "1", "int")
setHC = g.var_set("HumanoidCounter", "int", pos=(5300, 750)); g.wire(addHC, "ReturnValue", setHC, "HumanoidCounter", exec=False)
chain.then(setHC)

# DISMOUNT branch: restore each humanoid follower (reverse of stow) -- replicates C1 build_restore
loopD = g.foreach(CONAN, pos=(2100, 1700))
g.wire(getFol, "ReturnValue", loopD, "Array", exec=False)
g.wire(bMounted, "else", loopD, "Exec", exec=True)
mtblD = g.call("IsMountable", CONAN, pos=(2350, 1930))
g.wire(loopD, "Array Element", mtblD, "self", exec=False)
bMtblD = g.branch(pos=(2350, 1700))
g.wire(loopD, "LoopBody", bMtblD, "execute", exec=True)
g.wire(mtblD, "ReturnValue", bMtblD, "Condition", exec=False)
rMeshD = comp_of(loopD, "Array Element", "Mesh", (2650, 1900))
rMoveD = comp_of(loopD, "Array Element", "CharacterMovement", (2650, 2100))
chainD = Chain(bMtblD, "else")   # NOT mountable -> humanoid -> restore
detachD = actor_detach((2900, 1900))   # ACTOR-detach from the horse (replicates), keep world xform
g.wire(loopD, "Array Element", detachD, "self", exec=False)
chainD.then(detachD)
amodeD = bare_call("SetAnimationMode", SMC, (3150, 1700))
set_default(amodeD, "InAnimationMode", "AnimationBlueprint", "byte", enum="EAnimationMode")
g.wire(rMeshD, "Mesh", amodeD, "self", exec=False)
chainD.then(amodeD)
walkD = bare_call("SetMovementMode", CMC, (3400, 1700))
set_default(walkD, "NewMovementMode", "MOVE_Walking", "byte", enum="EMovementMode")
g.wire(rMoveD, "CharacterMovement", walkD, "self", exec=False)
chainD.then(walkD)
colD = bare_call("SetActorEnableCollision", ACTOR, (3650, 1700))
set_default(colD, "bNewActorEnableCollision", "true", "bool")
g.wire(loopD, "Array Element", colD, "self", exec=False)
chainD.then(colD)

# Seq2.1: update WasMounted = isMounted (every tick)
setWas = g.var_set("WasMounted", "bool", pos=(2600, 1150))
g.wire(isMounted, "ReturnValue", setWas, "WasMounted", exec=False)
g.wire(seq2, "then_1", setWas, "execute", exec=True)

text = g.render()
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))

# stamp the build version on the CDO so we can tell which class actually spawns
# (read instance.MgrVersion; ==2 -> the fixed class; 0/missing -> a cached old class)
gc = unreal.load_object(None, FULL + "_C")
if gc:
    cdo = unreal.get_default_object(gc)
    cdo.set_editor_property("MgrVersion", MOD.MGR_VERSION)
    # ALWAYS RELEVANT: a logic actor (hidden root, no collision) is otherwise NOT relevant to
    # clients, so it never replicates there -> no client instance -> its tick/multicast never reach
    # clients (the root cause of every "host-only" result). Always Relevant = it exists + ticks on
    # every client. (Conan modding wiki: Replication / Relevancy.)
    cdo.set_editor_property("always_relevant", True)
    anim_obj = unreal.load_object(None, ANIM)
    if anim_obj:
        cdo.set_editor_property("MountIdleAnim", anim_obj)
        print("CDO MountIdleAnim set:", anim_obj.get_name())
    unreal.EditorAssetLibrary.save_asset(PATH)
    print("CDO MgrVersion=%d + always_relevant stamped" % MOD.MGR_VERSION)
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("ORPHANS:", len(orphans), orphans if orphans else "(clean)")

# REAL compile verification -- do NOT trust inject's compiled flag (it means "compile
# ran", not "no errors"). Scan the compiled graph per-node for unresolved wildcard pins
# (e.g. an Array_Length whose type never got implied -> "Target Array is undetermined")
# and for compiler-stamped error markers. The ForEach macro legitimately carries wildcard
# pins (resolved via its ResolvedWildcardType header) so it's excluded.
problems = []
for blk in re.split(r'(?=Begin Object Class=)', txt):
    if not blk.strip():
        continue
    name = (re.search(r'Name="([^"]+)"', blk) or [None, "?"])[1]
    is_macro = "K2Node_MacroInstance" in blk  # ForEach etc.: wildcard is expected/resolved
    for pin in re.findall(r'CustomProperties Pin \((.*)\)', blk):
        pn = (re.search(r'PinName="([^"]+)"', pin) or [None, "?"])[1]
        if 'PinCategory="wildcard"' in pin and not is_macro:
            problems.append("WILDCARD unresolved: %s.%s" % (name, pn))
    if "ErrorMsg=" in blk or 'bHasCompilerMessage=True' in blk:
        problems.append("ERROR-MARKED node: %s" % name)
print("COMPILE PROBLEMS:", len(problems))
for p in problems:
    print("  !!", p)
print("BUILD OK" if not problems and not orphans else "BUILD HAS ISSUES -- DO NOT PLAY YET")
