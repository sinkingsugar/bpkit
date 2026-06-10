"""C2 manager build (canonical). BP_MountedFollowerManager : ModController.
ReceiveTick:
  - non-gated cosmetic seat loop first (runs on EVERY instance: server + clients)
  - then server-only (HasAuthority), PER PLAYER (v34): for every player pawn --
    raise the follower group caps once; detect mount state (get_rider scan over
    that player's followers); mounted -> stow unseated humanoids onto spare
    horses + per-tick maintain the seated ones (defeats the leash-AI re-enable);
    unmounted -> restore the seated ones. Level-triggered + idempotent: no
    transition state, so a follower whistled mid-ride saddles up too.
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
KTL = "/Script/Engine.KismetTextLibrary"

# === DIAGNOSTIC FLAGS (see README §Debugging) ===
# DEBUG: PIE-only PrintString beacons at the one-shot beats (caps/stow/sweep/rescue + leash
#   catch). On screen + log + `~` console. PrintString is compiled OUT of Shipping, so these
#   never reach players -- but flip False for the release deploy to keep the graph lean.
# HUD_DIAG: SHIP-VISIBLE HUDShowFIFO banner ("kept a rider seated", once per ride) when the
#   maintain pass catches the leash AI re-mobilizing a seated rider. The leash bug only
#   reproduces in the COOKED game where PrintString doesn't exist -- this is the one signal
#   that survives there (the proven v26-v32 pattern).
DEBUG = True
HUD_DIAG = True

# edit in place (reuse if present) -- deleting+recreating leaves a stale redirector
# that blocks recreate; the manager uses override EVENTS (not custom events) so
# clear+reinject is safe (no collision-rename).
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL)
# build-version tag (CDO default set below) to detect which class actually spawns
intt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
for vn in ("MgrVersion", "HumanoidCounter"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, intt)  # no-ops if exists
conan_ref = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.ConanCharacter.static_class())
# PlayerMount: per-player-iteration SCRATCH -- the horse the CURRENT player is riding (found by
# get_rider scan; null when on foot). Safe as a member var because the player ForEach body runs
# to completion per element. (GetMountInput lags/flakes across mount cycles -- get_rider is the
# stable ground truth.)
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "PlayerMount", conan_ref)
# Scratch arrays. Per-player-iteration: SpareHorses = the unridden, unoccupied follower horses
# (humanoid #i -> SpareHorses[i]; index-alignment guarantees no two share a horse);
# OccupiedHorses = horses already carrying a seated humanoid (so re-stows can't double-book a
# horse across ticks). Per-TICK: ActiveSeats = every horse a MOUNTED player legitimized this
# tick (its occupied horses + horses stowed onto this tick) -- the global restore sweep frees
# any seated humanoid whose horse is NOT in it. Persistent: InitializedPlayers = player pawns
# whose group caps were already raised (the adjustment is ADDITIVE -- it must fire once per
# pawn, never per tick; a relogged player is a NEW pawn -> re-applied once, same net effect as
# the old per-boot init).
conan_arr = unreal.BlueprintEditorLibrary.get_array_type(conan_ref)
for vn in ("SpareHorses", "OccupiedHorses", "ActiveSeats", "InitializedPlayers"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, conan_arr)
anim_ref = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.AnimSequence.static_class())
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "MountIdleAnim", anim_ref)
if HUD_DIAG:
    # once-per-ride latch for the "kept a rider seated" banner (re-armed while unmounted)
    boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "ReportedCatch", boolt)
ANIM = MOD.IDLE_ANIM

g = ir.Graph("EventGraph")

def cast_node(target, pos):
    return g.node("K2Node_DynamicCast",
                  ['TargetType="/Script/CoreUObject.Class\'%s\'"' % target], base="DynamicCast", pos=pos)

# --- diagnostic node helpers (flags defined at the top; see README §Debugging) ---
def dbg(msg, pos):
    """PrintString beacon, auto-stamped with the build version; wire exec via execute/then.
    Only call under DEBUG. PIE-only (PrintString is compiled out of Shipping)."""
    p = g.call("PrintString", KSL, pos=pos)
    g.typed_input(p, "InString", "MF v%d: %s" % (MOD.MGR_VERSION, msg), "string")
    return p
def txt_lit(s, pos):
    c = g.call("Conv_StringToText", KTL, pos=pos)
    g.typed_input(c, "InString", s, "string")
    return c
def fifo(txt_node, pos):
    """SHIP-VISIBLE banner: ConanCharacter.HUDShowFIFO(FText) -> the local client's scrolling
    event feed; survives Shipping. WorldContextObject is AUTO-MANAGED: the compiler binds it to
    self (manual links to it are DROPPED on paste -- verified v26). Only call under HUD_DIAG."""
    f = g.call("HUDShowFIFO", CONAN, pos=pos)
    g.wire(txt_node, "ReturnValue", f, "Text", exec=False)
    return f

# --- C1 attach/restore node helpers (replicated; reuse the proven Stow/Restore pattern) ---
CHAR = "/Script/Engine.Character"
SMC = "/Script/Engine.SkeletalMeshComponent"
SCENE = "/Script/Engine.SceneComponent"
CMC = "/Script/Engine.CharacterMovementComponent"
ACTOR = "/Script/Engine.Actor"
CLS = {"Mesh": SMC, "CharacterMovement": CMC,
       "CapsuleComponent": "/Script/Engine.CapsuleComponent",
       "PlayerMount": CONAN, "MountIdleAnim": "/Script/Engine.AnimSequence"}
STRUCTS = {}
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
def arr_item_pin(node, pin_name, elem_sub):
    """Type a CallArrayFunction's element pin (NewItem / ItemToFind) to match TargetArray."""
    p = node.pin(pin_name); p.dir = "EGPD_Input"; _stype(p, "object", elem_sub)
    return p
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
# EXCLUDE THE PLAYER. Historically authored as GetPlayerState+IsValid ("replicates, unlike
# IsPlayerControlled") -- but GetPlayerState is NOT a UFUNCTION in this build and the paste
# SILENTLY DROPPED it since v30: the exclusion has always been a no-op at runtime (harmless,
# because a riding player isn't actor-attached to a mountable parent here). IsPlayerControlled
# DOES resolve; on clients it only covers the local player, which is strictly better than the
# nothing we actually had.
isPlayerMC = g.call("IsPlayerControlled", "/Script/Engine.Pawn", pos=(1100, -1550))
g.wire(castMC, "AsConan Character", isPlayerMC, "self", exec=False)
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
g.wire(loopMC, "Completed", bAuth, "execute", exec=True)   # THEN the server-gated per-player pass
g.wire(haz, "ReturnValue", bAuth, "Condition", exec=False)

# === v34 PER-PLAYER PASS (the host-only fix). GetPlayerCharacter(0) served exactly one player;
# now EVERY player pawn gets the full treatment. Player pawns are found by re-walking the SAME
# GetAllActorsOfClass result the cosmetic loop consumed: a player pawn is a ConanCharacter with
# a valid PlayerState (the proven discriminator from the cosmetic loop -- no new node kinds).
# Stow/restore is LEVEL-TRIGGERED and idempotent instead of transition-edge-triggered: per tick,
# per mounted player, every UNSEATED humanoid follower is stowed (one-shot by construction: the
# seated-check gates it) and every SEATED one gets the v31/v32 leash maintain; per unmounted
# player, every seated follower is restored (one-shot: after the restore it is no longer seated,
# so the v28 every-tick-AnimBP-reinit catastrophe cannot recur). This retires WasMounted/the
# transition machinery -- and a follower whistled mid-ride now saddles up too. ===
clrActive = arr_fn("Array_Clear", ir.obj_path(CONAN), (50, 350))
g.wire(arr_var("ActiveSeats", ir.obj_path(CONAN), (50, 550)), "ActiveSeats", clrActive, "TargetArray", exec=False)
g.wire(bAuth, "then", clrActive, "execute", exec=True)   # per-tick: reset the legit-seat set
loopPS = g.foreach(ACTOR, pos=(250, 200))
g.wire(gaC, "OutActors", loopPS, "Array", exec=False)
g.wire(clrActive, "then", loopPS, "Exec", exec=True)
castP = cast_node(CONAN, (500, 200))
g.wire(loopPS, "Array Element", castP, "Object", exec=False)
g.wire(loopPS, "LoopBody", castP, "execute", exec=True)
# PLAYER GATE: IsPlayerControlled -- server-accurate, and this pass is HasAuthority-gated.
# Do NOT use GetPlayerState here: it is not a UFUNCTION in this Conan build, and the paste
# SILENTLY DROPS unresolvable CallFunction nodes (no orphan, no compile error -- IsValid then
# reads an unwired pin = null = false), which killed the whole per-player pass in v34/v35.
# Caught 2026-06-10 via live PIE probe + the authored-vs-pasted count check at the bottom.
isPl = g.call("IsPlayerControlled", "/Script/Engine.Pawn", pos=(600, 400))
g.wire(castP, "AsConan Character", isPl, "self", exec=False)
bIsPl = g.branch(pos=(750, 200))
g.wire(castP, "then", bIsPl, "execute", exec=True)
g.wire(isPl, "ReturnValue", bIsPl, "Condition", exec=False)
P = (castP, "AsConan Character")   # this iteration's player ConanCharacter

# this player's followers (pure calls -> data-only fan-out to every loop below re-evaluates
# against the CURRENT P wire, the proven v32 pattern)
getTSCp = g.call("GetThrallSystemComponent", CONAN, pos=(750, 550))
g.wire(P[0], P[1], getTSCp, "self", exec=False)
getFolP = g.call("GetFollowingThrallCharacters", TSC, pos=(1000, 550))
g.wire(getTSCp, "ReturnValue", getFolP, "self", exec=False)

# --- init: raise every follower group cap ONCE per player pawn (additive adjustment -- per-tick
# re-fire would stack forever, hence the InitializedPlayers guard) ---
hasInit = arr_fn("Array_Contains", ir.obj_path(CONAN), (950, 0))
g.wire(arr_var("InitializedPlayers", ir.obj_path(CONAN), (950, -180)), "InitializedPlayers", hasInit, "TargetArray", exec=False)
arr_item_pin(hasInit, "ItemToFind", ir.obj_path(CONAN))
g.wire(P[0], P[1], hasInit, "ItemToFind", exec=False)
bInitP = g.branch(pos=(1200, 200))
g.wire(bIsPl, "then", bInitP, "execute", exec=True)
g.wire(hasInit, "ReturnValue", bInitP, "Condition", exec=False)
prev, prev_pin = bInitP, "else"   # not yet initialized -> raise the caps
for gi, grp in enumerate(("Mount", "Warrior", "Crafter", "Bearer", "Performer", "Archer")):
    a = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(1450 + gi * 260, 0))
    g.typed_input(a, "Group", grp, "name")
    g.typed_input(a, "Amount", "5", "int")
    g.wire(getTSCp, "ReturnValue", a, "self", exec=False)
    g.wire(prev, prev_pin, a, "execute", exec=True)
    prev, prev_pin = a, "then"
addInit = arr_fn("Array_Add", ir.obj_path(CONAN), (1450 + 6 * 260, 0))
g.wire(arr_var("InitializedPlayers", ir.obj_path(CONAN), (1450 + 6 * 260, -180)), "InitializedPlayers", addInit, "TargetArray", exec=False)
arr_item_pin(addInit, "NewItem", ir.obj_path(CONAN))
g.wire(P[0], P[1], addInit, "NewItem", exec=False)
g.wire(prev, prev_pin, addInit, "execute", exec=True)
initTail = addInit
if DEBUG:
    dbgInit = dbg("+5 follower caps applied (new player)", (1450 + 7 * 260, 0))
    g.wire(addInit, "then", dbgInit, "execute", exec=True)
    initTail = dbgInit

# --- mount detect: scan THIS player's following horses for GetRider()==P ---
clrPM = var_set_m("PlayerMount", (1250, 550))   # null (value pin left unconnected)
g.wire(bInitP, "then", clrPM, "execute", exec=True)      # already initialized
g.wire(initTail, "then", clrPM, "execute", exec=True)    # just initialized (exec inputs merge)
loopDet = g.foreach(CONAN, pos=(1500, 550))
g.wire(getFolP, "ReturnValue", loopDet, "Array", exec=False)
g.wire(clrPM, "then", loopDet, "Exec", exec=True)
getRiderDet = g.call("GetRider", CONAN, pos=(1750, 800))
g.wire(loopDet, "Array Element", getRiderDet, "self", exec=False)
eqDet = g.call("EqualEqual_ObjectObject", KML, pos=(1950, 800))
g.wire(getRiderDet, "ReturnValue", eqDet, "A", exec=False)
g.wire(P[0], P[1], eqDet, "B", exec=False)
bRiderDet = g.branch(pos=(1750, 550))
g.wire(loopDet, "LoopBody", bRiderDet, "execute", exec=True)
g.wire(eqDet, "ReturnValue", bRiderDet, "Condition", exec=False)
setPM = var_set_m("PlayerMount", (2000, 550))
g.wire(loopDet, "Array Element", setPM, "PlayerMount", exec=False)
g.wire(bRiderDet, "then", setPM, "execute", exec=True)   # this horse's rider == P -> P's mount

getPM = var_self("PlayerMount", (2050, 800))
isMounted = g.call("IsValid", KSL, pos=(2250, 850))
g.wire(getPM, "PlayerMount", isMounted, "Object", exec=False)
bMountedP = g.branch(pos=(2300, 550))
g.wire(loopDet, "Completed", bMountedP, "execute", exec=True)
g.wire(isMounted, "ReturnValue", bMountedP, "Condition", exec=False)

# === MOUNTED: three passes over this player's followers. ===
# Pass O: collect horses ALREADY carrying a seated humanoid, so the spare pool can't
# double-book a horse on later ticks (a stowed rider doesn't register as the horse's "rider",
# so GetRider can't exclude these).
clrOcc = arr_fn("Array_Clear", ir.obj_path(CONAN), (2550, 300))
g.wire(arr_var("OccupiedHorses", ir.obj_path(CONAN), (2550, 520)), "OccupiedHorses", clrOcc, "TargetArray", exec=False)
g.wire(bMountedP, "then", clrOcc, "execute", exec=True)
loopO = g.foreach(CONAN, pos=(2800, 300))
g.wire(getFolP, "ReturnValue", loopO, "Array", exec=False)
g.wire(clrOcc, "then", loopO, "Exec", exec=True)
mtblO = g.call("IsMountable", CONAN, pos=(3050, 530))
g.wire(loopO, "Array Element", mtblO, "self", exec=False)
bMtblO = g.branch(pos=(3050, 300))
g.wire(loopO, "LoopBody", bMtblO, "execute", exec=True)
g.wire(mtblO, "ReturnValue", bMtblO, "Condition", exec=False)
getParO = g.call("GetAttachParentActor", ACTOR, pos=(3300, 530))
g.wire(loopO, "Array Element", getParO, "self", exec=False)
castParO = cast_node(CONAN, (3300, 300))
g.wire(getParO, "ReturnValue", castParO, "Object", exec=False)
g.wire(bMtblO, "else", castParO, "execute", exec=True)   # humanoid -> who carries it? (cast-fail = nobody)
parMtblO = g.call("IsMountable", CONAN, pos=(3550, 530))
g.wire(castParO, "AsConan Character", parMtblO, "self", exec=False)
bSeatO = g.branch(pos=(3550, 300))
g.wire(castParO, "then", bSeatO, "execute", exec=True)
g.wire(parMtblO, "ReturnValue", bSeatO, "Condition", exec=False)
addOcc = arr_fn("Array_Add", ir.obj_path(CONAN), (3800, 300))
g.wire(arr_var("OccupiedHorses", ir.obj_path(CONAN), (3800, 520)), "OccupiedHorses", addOcc, "TargetArray", exec=False)
arr_item_pin(addOcc, "NewItem", ir.obj_path(CONAN))
g.wire(castParO, "AsConan Character", addOcc, "NewItem", exec=False)
g.wire(bSeatO, "then", addOcc, "execute", exec=True)
addActO = arr_fn("Array_Add", ir.obj_path(CONAN), (4050, 300))   # this seat is legit (owner is mounted)
g.wire(arr_var("ActiveSeats", ir.obj_path(CONAN), (4050, 520)), "ActiveSeats", addActO, "TargetArray", exec=False)
arr_item_pin(addActO, "NewItem", ir.obj_path(CONAN))
g.wire(castParO, "AsConan Character", addActO, "NewItem", exec=False)
g.wire(addOcc, "then", addActO, "execute", exec=True)

# Pass A: build the spare pool -- mountable, unridden (excludes P's own mount), unoccupied.
clrArr = arr_fn("Array_Clear", ir.obj_path(CONAN), (2550, 950))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (2550, 1170)), "SpareHorses", clrArr, "TargetArray", exec=False)
g.wire(loopO, "Completed", clrArr, "execute", exec=True)
setHC0 = g.var_set("HumanoidCounter", "int", pos=(2800, 950)); setHC0.pin("HumanoidCounter").literal("0")
g.wire(clrArr, "then", setHC0, "execute", exec=True)
loopA = g.foreach(CONAN, pos=(3050, 950))
g.wire(getFolP, "ReturnValue", loopA, "Array", exec=False)
g.wire(setHC0, "then", loopA, "Exec", exec=True)
mtblA = g.call("IsMountable", CONAN, pos=(3300, 1180))
g.wire(loopA, "Array Element", mtblA, "self", exec=False)
bMtblA = g.branch(pos=(3300, 950))
g.wire(loopA, "LoopBody", bMtblA, "execute", exec=True)
g.wire(mtblA, "ReturnValue", bMtblA, "Condition", exec=False)
getRiderA = g.call("GetRider", CONAN, pos=(3550, 1180))
g.wire(loopA, "Array Element", getRiderA, "self", exec=False)
ridValA = g.call("IsValid", KSL, pos=(3750, 1180))
g.wire(getRiderA, "ReturnValue", ridValA, "Object", exec=False)
bRiddenA = g.branch(pos=(3600, 950))
g.wire(bMtblA, "then", bRiddenA, "execute", exec=True)
g.wire(ridValA, "ReturnValue", bRiddenA, "Condition", exec=False)
occA = arr_fn("Array_Contains", ir.obj_path(CONAN), (3850, 1180))
g.wire(arr_var("OccupiedHorses", ir.obj_path(CONAN), (3850, 1400)), "OccupiedHorses", occA, "TargetArray", exec=False)
arr_item_pin(occA, "ItemToFind", ir.obj_path(CONAN))
g.wire(loopA, "Array Element", occA, "ItemToFind", exec=False)
bOccA = g.branch(pos=(3900, 950))
g.wire(bRiddenA, "else", bOccA, "execute", exec=True)    # unridden -> already carrying a thrall?
g.wire(occA, "ReturnValue", bOccA, "Condition", exec=False)
addSpare = arr_fn("Array_Add", ir.obj_path(CONAN), (4150, 950))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (4150, 1170)), "SpareHorses", addSpare, "TargetArray", exec=False)
arr_item_pin(addSpare, "NewItem", ir.obj_path(CONAN))
g.wire(loopA, "Array Element", addSpare, "NewItem", exec=False)
g.wire(bOccA, "else", addSpare, "execute", exec=True)    # free horse -> spare pool
# SPACING: stagger this horse's follow distance by its loop index (index*180) so the horses
# trail in a line behind the player instead of all clustering on one follow point.
idxMul = g.call("Multiply_IntInt", KML, pos=(4400, 1180))
g.wire(loopA, "Array Index", idxMul, "A", exec=False)
g.typed_input(idxMul, "B", "180", "int")
idxF = g.call("Conv_IntToDouble", KML, pos=(4600, 1180))
g.wire(idxMul, "ReturnValue", idxF, "InInt", exec=False)
setDist = g.call("SetAdditionalFollowDistance", CONAN, pos=(4400, 950))
g.wire(loopA, "Array Element", setDist, "self", exec=False)
g.wire(idxF, "ReturnValue", setDist, "NewFollowDistance", exec=False)
g.wire(addSpare, "then", setDist, "execute", exec=True)

# Pass B: every humanoid follower. SEATED (attach parent is a mountable horse) -> the per-tick
# MAINTAIN (the v31/v32 leash fix: Conan's follower catch-up AI re-enables a seated rider's
# movement after a while -- cooked-game-only repro -- and CharacterMovement walks the still-
# attached pawn to the ground; re-pin MOVE_None + re-assert the saddle xform every tick, so the
# re-enable never survives a frame). UNSEATED -> STOW onto SpareHorses[HumanoidCounter]
# (one-shot by construction: next tick it is seated and lands in the maintain branch).
loopB = g.foreach(CONAN, pos=(2550, 1700))
g.wire(getFolP, "ReturnValue", loopB, "Array", exec=False)
g.wire(loopA, "Completed", loopB, "Exec", exec=True)
mtblB = g.call("IsMountable", CONAN, pos=(2800, 1930))
g.wire(loopB, "Array Element", mtblB, "self", exec=False)
bMtblB = g.branch(pos=(2800, 1700))
g.wire(loopB, "LoopBody", bMtblB, "execute", exec=True)
g.wire(mtblB, "ReturnValue", bMtblB, "Condition", exec=False)
# seated? = attached AND the attach parent casts to a mountable ConanCharacter
getParB = g.call("GetAttachParentActor", ACTOR, pos=(3050, 1930))
g.wire(loopB, "Array Element", getParB, "self", exec=False)
parVB = g.call("IsValid", KSL, pos=(3250, 1930))
g.wire(getParB, "ReturnValue", parVB, "Object", exec=False)
bParVB = g.branch(pos=(3050, 1700))
g.wire(bMtblB, "else", bParVB, "execute", exec=True)     # humanoid
g.wire(parVB, "ReturnValue", bParVB, "Condition", exec=False)
castParB = cast_node(CONAN, (3300, 1700))
g.wire(getParB, "ReturnValue", castParB, "Object", exec=False)
g.wire(bParVB, "then", castParB, "execute", exec=True)   # attached -> to whom?
parMtblB = g.call("IsMountable", CONAN, pos=(3550, 1930))
g.wire(castParB, "AsConan Character", parMtblB, "self", exec=False)
bSeatB = g.branch(pos=(3550, 1700))                       # (CastFailed = attached to a placeable
g.wire(castParB, "then", bSeatB, "execute", exec=True)    #  bench/wheel -> leave it exactly alone)
g.wire(parMtblB, "ReturnValue", bSeatB, "Condition", exec=False)

rMeshB = comp_of(loopB, "Array Element", "Mesh", (3800, 2200))
rMoveB = comp_of(loopB, "Array Element", "CharacterMovement", (3800, 2380))

# MAINTAIN (seated): idempotent when already frozen; instantly undoes the leash AI's re-enable.
disableM = bare_call("DisableMovement", CMC, (3850, 1500))
g.wire(rMoveB, "CharacterMovement", disableM, "self", exec=False)
if HUD_DIAG:
    # CATCH DETECTION: sample IsMovingOnGround BEFORE the re-pin -- true means the leash AI
    # actually re-mobilized this seated rider and the maintain pass is earning its keep.
    # Report ONCE per ride (ReportedCatch, re-armed while the owner is on foot): a HUDShowFIFO
    # banner (ship-visible -- the leash only repros COOKED) + a DEBUG PrintString for the log.
    movingB = g.call("IsMovingOnGround", CMC, pos=(3850, 1300))
    g.wire(rMoveB, "CharacterMovement", movingB, "self", exec=False)
    bMovB = g.branch(pos=(4050, 1300))
    g.wire(bSeatB, "then", bMovB, "execute", exec=True)
    g.wire(movingB, "ReturnValue", bMovB, "Condition", exec=False)
    getRC = g.var_get("ReportedCatch", "bool", pos=(4250, 1150))
    bRC = g.branch(pos=(4300, 1300))
    g.wire(bMovB, "then", bRC, "execute", exec=True)
    g.wire(getRC, "ReportedCatch", bRC, "Condition", exec=False)
    fifoCatch = fifo(txt_lit("Mounted Followers v%d: kept a rider seated" % MOD.MGR_VERSION,
                             (4500, 1100)), (4700, 1150))
    g.wire(bRC, "else", fifoCatch, "execute", exec=True)   # first catch this ride -> banner
    catchTail = fifoCatch
    if DEBUG:
        dbgCatch = dbg("leash maintain caught a re-mobilized rider -- re-pinned", (4900, 1150))
        g.wire(fifoCatch, "then", dbgCatch, "execute", exec=True)
        catchTail = dbgCatch
    setRC = g.var_set("ReportedCatch", "bool", pos=(5100, 1150)); setRC.pin("ReportedCatch").literal("true")
    g.wire(catchTail, "then", setRC, "execute", exec=True)
    # all paths converge on the re-pin (exec inputs merge)
    g.wire(setRC, "then", disableM, "execute", exec=True)   # first catch, after the banner
    g.wire(bRC, "then", disableM, "execute", exec=True)     # already reported this ride
    g.wire(bMovB, "else", disableM, "execute", exec=True)   # not moving -> routine re-pin
else:
    g.wire(bSeatB, "then", disableM, "execute", exec=True)
setRelM = bare_call("K2_SetActorRelativeLocation", ACTOR, (4100, 1500))
relpM = setRelM.pin("NewRelativeLocation"); relpM.dir = "EGPD_Input"
type_struct(relpM, "/Script/CoreUObject.Vector"); relpM.set("DefaultValue", '"0.000000,0.000000,90.000000"')
g.wire(loopB, "Array Element", setRelM, "self", exec=False)
g.wire(disableM, "then", setRelM, "execute", exec=True)
setRotM = bare_call("K2_SetActorRelativeRotation", ACTOR, (4350, 1500))
rotpM = setRotM.pin("NewRelativeRotation"); rotpM.dir = "EGPD_Input"
type_struct(rotpM, "/Script/CoreUObject.Rotator"); rotpM.set("DefaultValue", '"0.000000,90.000000,0.000000"')
g.wire(loopB, "Array Element", setRotM, "self", exec=False)
g.wire(setRelM, "then", setRotM, "execute", exec=True)

# STOW (unseated): claim SpareHorses[HumanoidCounter]; only if the counter is in range
# ("not enough horses" leaves the extras walking, by design). GUARD is an int-range test --
# IsValid won't merge onto a GetArrayItem.Output pin via paste (v32 lesson).
hcGet = g.var_get("HumanoidCounter", "int", pos=(3800, 2560))
arrGetB = arr_var("SpareHorses", ir.obj_path(CONAN), (3800, 2730))
horse = get_item(arrGetB, "SpareHorses", hcGet, "HumanoidCounter", ir.obj_path(CONAN), (4050, 2630))
lenB = arr_fn("Array_Length", ir.obj_path(CONAN), (4050, 2400))
g.wire(arr_var("SpareHorses", ir.obj_path(CONAN), (4050, 2580)), "SpareHorses", lenB, "TargetArray", exec=False)
lessB = g.call("Less_IntInt", KML, pos=(4250, 2400))
g.wire(hcGet, "HumanoidCounter", lessB, "A", exec=False)
g.wire(lenB, "ReturnValue", lessB, "B", exec=False)
bHasHorse = g.branch(pos=(3950, 1850))
g.wire(bParVB, "else", bHasHorse, "execute", exec=True)  # unattached humanoid -> stow
g.wire(bSeatB, "else", bHasHorse, "execute", exec=True)  # attached to a non-horse ConanCharacter (odd) -> treat as unseated
g.wire(lessB, "ReturnValue", bHasHorse, "Condition", exec=False)
mMesh = comp_of(horse, "Output", "Mesh", (4300, 2630))   # spare horse mesh = attach parent
chain = Chain(bHasHorse, "then")
# ACTOR-attach the follower to the saddle -- actor attachment REPLICATES to clients
# (mesh/component attachment did not, which is what desynced MP).
attach = actor_attach((4250, 1850), "attachrider")
g.wire(loopB, "Array Element", attach, "self", exec=False)   # the follower ACTOR
g.wire(mMesh, "Mesh", attach, "Parent", exec=False)
chain.then(attach)
# legitimize this seat immediately, or the same tick's global sweep would un-stow it
addActSt = arr_fn("Array_Add", ir.obj_path(CONAN), (4500, 2100))
g.wire(arr_var("ActiveSeats", ir.obj_path(CONAN), (4500, 2300)), "ActiveSeats", addActSt, "TargetArray", exec=False)
arr_item_pin(addActSt, "NewItem", ir.obj_path(CONAN))
g.wire(horse, "Output", addActSt, "NewItem", exec=False)
chain.then(addActSt)
# raise the body onto the saddle (root capsule snaps ~90 below the mesh)
setRel = bare_call("K2_SetActorRelativeLocation", ACTOR, (4500, 1850))
relp = setRel.pin("NewRelativeLocation"); relp.dir = "EGPD_Input"
type_struct(relp, "/Script/CoreUObject.Vector"); relp.set("DefaultValue", '"0.000000,0.000000,90.000000"')
g.wire(loopB, "Array Element", setRel, "self", exec=False)
chain.then(setRel)
# correct the ~90deg yaw the 'attachrider' socket snaps to (relative rotation replicates with the
# attach). If it ends up flipped, swap -90 -> 90.
setRot = bare_call("K2_SetActorRelativeRotation", ACTOR, (4750, 1850))
rotp = setRot.pin("NewRelativeRotation"); rotp.dir = "EGPD_Input"
type_struct(rotp, "/Script/CoreUObject.Rotator"); rotp.set("DefaultValue", '"0.000000,90.000000,0.000000"')
g.wire(loopB, "Array Element", setRot, "self", exec=False)
chain.then(setRot)
disable = bare_call("DisableMovement", CMC, (5000, 1850))
g.wire(rMoveB, "CharacterMovement", disable, "self", exec=False)
chain.then(disable)
nocol = bare_call("SetActorEnableCollision", ACTOR, (5250, 1850))
set_default(nocol, "bNewActorEnableCollision", "false", "bool")
g.wire(loopB, "Array Element", nocol, "self", exec=False)
chain.then(nocol)
amode = bare_call("SetAnimationMode", SMC, (5500, 1850))
set_default(amode, "InAnimationMode", "AnimationSingleNode", "byte", enum="EAnimationMode")
g.wire(rMeshB, "Mesh", amode, "self", exec=False)
chain.then(amode)
play = bare_call("PlayAnimation", SMC, (5750, 1850))
set_default(play, "bLooping", "true", "bool")
animGet = var_self("MountIdleAnim", (5500, 2100))
g.wire(animGet, "MountIdleAnim", play, "NewAnimToPlay", exec=False)
g.wire(rMeshB, "Mesh", play, "self", exec=False)
chain.then(play)
# advance the counter so the NEXT humanoid takes the NEXT spare horse -> distinct mounts
hcGet2 = g.var_get("HumanoidCounter", "int", pos=(6000, 2100))
addHC = g.call("Add_IntInt", KML, pos=(6000, 2000)); g.wire(hcGet2, "HumanoidCounter", addHC, "A", exec=False)
g.typed_input(addHC, "B", "1", "int")
setHC = g.var_set("HumanoidCounter", "int", pos=(6000, 1850)); g.wire(addHC, "ReturnValue", setHC, "HumanoidCounter", exec=False)
chain.then(setHC)
if DEBUG:
    chain.then(dbg("stowed a rider onto a spare horse", (6250, 1850)))

# NOT MOUNTED housekeeping pass over the followers. Horses: reset the staggered follow
# distance (the stagger otherwise outlives the ride). Humanoids: STATUE RESCUE -- if a horse
# died mid-ride its rider auto-detached but kept our stow freeze (MOVE_None, no collision);
# while the owner stayed mounted the stow pass re-seats it, but once the owner is on foot
# nothing else would unfreeze it (the global sweep below only handles SEATED bodies). So an
# unattached humanoid follower stuck in MOVE_None gets movement + collision back here. (The
# anim reset is the cosmetic loop's job -- its force=false AnimBP call is a no-op unless the
# char is genuinely stuck in SingleNode.) Restoring SEATED riders is NOT done per-player --
# the global sweep covers it (and the cases a follower-list walk can't: followers that LEFT
# the list mid-ride, owners who logged out while mounted).
loopDist = g.foreach(CONAN, pos=(2550, 3050))
g.wire(getFolP, "ReturnValue", loopDist, "Array", exec=False)
distEntry = (bMountedP, "else")
if HUD_DIAG:
    # re-arm the once-per-ride "kept a rider seated" banner while the owner is on foot
    setRC0 = g.var_set("ReportedCatch", "bool", pos=(2350, 3050)); setRC0.pin("ReportedCatch").literal("false")
    g.wire(bMountedP, "else", setRC0, "execute", exec=True)
    distEntry = (setRC0, "then")
g.wire(distEntry[0], distEntry[1], loopDist, "Exec", exec=True)
mtblD0 = g.call("IsMountable", CONAN, pos=(2800, 3280))
g.wire(loopDist, "Array Element", mtblD0, "self", exec=False)
bMtblD0 = g.branch(pos=(2800, 3050))
g.wire(loopDist, "LoopBody", bMtblD0, "execute", exec=True)
g.wire(mtblD0, "ReturnValue", bMtblD0, "Condition", exec=False)
convD0 = g.call("Conv_IntToDouble", KML, pos=(3050, 3280))
g.typed_input(convD0, "InInt", "0", "int")
setDist0 = g.call("SetAdditionalFollowDistance", CONAN, pos=(3050, 3050))
g.wire(loopDist, "Array Element", setDist0, "self", exec=False)
g.wire(convD0, "ReturnValue", setDist0, "NewFollowDistance", exec=False)
g.wire(bMtblD0, "then", setDist0, "execute", exec=True)
# humanoid -> unattached AND frozen (MOVE_None)? -> give it movement + collision back
getParD0 = g.call("GetAttachParentActor", ACTOR, pos=(3050, 3450))
g.wire(loopDist, "Array Element", getParD0, "self", exec=False)
parVD0 = g.call("IsValid", KSL, pos=(3250, 3450))
g.wire(getParD0, "ReturnValue", parVD0, "Object", exec=False)
bParVD0 = g.branch(pos=(3300, 3050))
g.wire(bMtblD0, "else", bParVD0, "execute", exec=True)
g.wire(parVD0, "ReturnValue", bParVD0, "Condition", exec=False)
rMoveD0 = comp_of(loopDist, "Array Element", "CharacterMovement", (3300, 3280))
# MovementMode is a byte(EMovementMode) property on the movement comp; MOVE_None == 0
mmD0 = g.node("K2Node_VariableGet",
    ['VariableReference=(MemberName="MovementMode",MemberParent="/Script/CoreUObject.Class\'%s\'",bSelfContext=False)' % CMC],
    base="VariableGet", pos=(3550, 3280))
spD0 = mmD0.pin("self"); spD0.dir = "EGPD_Input"; type_obj(spD0, CMC)
opD0 = mmD0.pin("MovementMode"); opD0.dir = "EGPD_Output"
opD0.set("PinType.PinCategory", '"byte"'); opD0.set("PinType.PinSubCategoryObject", ENUM["EMovementMode"])
g.wire(rMoveD0, "CharacterMovement", mmD0, "self", exec=False)
eqMMD0 = g.call("EqualEqual_ByteByte", KML, pos=(3750, 3280))
g.wire(mmD0, "MovementMode", eqMMD0, "A", exec=False)
g.typed_input(eqMMD0, "B", "0", "byte")   # 0 == MOVE_None
bFrozD0 = g.branch(pos=(3550, 3050))
g.wire(bParVD0, "else", bFrozD0, "execute", exec=True)   # unattached humanoid
g.wire(eqMMD0, "ReturnValue", bFrozD0, "Condition", exec=False)
walkD0 = bare_call("SetMovementMode", CMC, (3800, 3050))
set_default(walkD0, "NewMovementMode", "MOVE_Walking", "byte", enum="EMovementMode")
g.wire(rMoveD0, "CharacterMovement", walkD0, "self", exec=False)
g.wire(bFrozD0, "then", walkD0, "execute", exec=True)
colD0 = bare_call("SetActorEnableCollision", ACTOR, (4050, 3050))
set_default(colD0, "bNewActorEnableCollision", "true", "bool")
g.wire(loopDist, "Array Element", colD0, "self", exec=False)
g.wire(walkD0, "then", colD0, "execute", exec=True)
if DEBUG:
    dbgResc = dbg("statue rescue (unfroze a stranded rider)", (4300, 3050))
    g.wire(colD0, "then", dbgResc, "execute", exec=True)

# === GLOBAL RESTORE SWEEP (after the player loop): any humanoid still seated on a horse NO
# mounted player legitimized this tick (ActiveSeats) gets restored. ONE restore path covers
# everything: the normal dismount, a follower that left the follow list mid-ride, and a player
# who logged out while mounted. Players themselves are EXCLUDED via the PlayerState check (a
# riding player can read as attached-to-a-mountable -- "restoring" one would be a forced
# dismount). One-shot by construction: restored -> no longer seated, so the plain AnimBP-mode
# call fires exactly once (no v28 every-tick-reinit recurrence). ===
loopG = g.foreach(ACTOR, pos=(250, 3700))
g.wire(gaC, "OutActors", loopG, "Array", exec=False)
g.wire(loopPS, "Completed", loopG, "Exec", exec=True)
castG = cast_node(CONAN, (500, 3700))
g.wire(loopG, "Array Element", castG, "Object", exec=False)
g.wire(loopG, "LoopBody", castG, "execute", exec=True)
# player exclusion: IsPlayerControlled (server-side sweep -> accurate). NOT GetPlayerState --
# see the gate note above: that node silently vanishes on paste in this build, and an
# always-false exclusion HERE would let the sweep force-dismount a riding player.
isPlG = g.call("IsPlayerControlled", "/Script/Engine.Pawn", pos=(600, 3900))
g.wire(castG, "AsConan Character", isPlG, "self", exec=False)
bIsPlG = g.branch(pos=(750, 3700))
g.wire(castG, "then", bIsPlG, "execute", exec=True)
g.wire(isPlG, "ReturnValue", bIsPlG, "Condition", exec=False)
mtblG = g.call("IsMountable", CONAN, pos=(750, 4050))
g.wire(castG, "AsConan Character", mtblG, "self", exec=False)
bMtblG = g.branch(pos=(1000, 3700))
g.wire(bIsPlG, "else", bMtblG, "execute", exec=True)     # not a player
g.wire(mtblG, "ReturnValue", bMtblG, "Condition", exec=False)
getParG = g.call("GetAttachParentActor", ACTOR, pos=(1000, 4050))
g.wire(castG, "AsConan Character", getParG, "self", exec=False)
castParG = cast_node(CONAN, (1250, 3700))
g.wire(getParG, "ReturnValue", castParG, "Object", exec=False)
g.wire(bMtblG, "else", castParG, "execute", exec=True)   # humanoid -> seated on what? (cast-fail = not seated)
parMtblG = g.call("IsMountable", CONAN, pos=(1500, 4050))
g.wire(castParG, "AsConan Character", parMtblG, "self", exec=False)
bSeatG = g.branch(pos=(1500, 3700))
g.wire(castParG, "then", bSeatG, "execute", exec=True)
g.wire(parMtblG, "ReturnValue", bSeatG, "Condition", exec=False)
activeG = arr_fn("Array_Contains", ir.obj_path(CONAN), (1750, 4050))
g.wire(arr_var("ActiveSeats", ir.obj_path(CONAN), (1750, 4250)), "ActiveSeats", activeG, "TargetArray", exec=False)
arr_item_pin(activeG, "ItemToFind", ir.obj_path(CONAN))
g.wire(castParG, "AsConan Character", activeG, "ItemToFind", exec=False)
bActiveG = g.branch(pos=(1750, 3700))
g.wire(bSeatG, "then", bActiveG, "execute", exec=True)   # seated -> is this seat legit this tick?
g.wire(activeG, "ReturnValue", bActiveG, "Condition", exec=False)
rMeshG = comp_of(castG, "AsConan Character", "Mesh", (2000, 4050))
rMoveG = comp_of(castG, "AsConan Character", "CharacterMovement", (2000, 4230))
chainG = Chain(bActiveG, "else")                          # NOT legitimized -> restore
detachG = actor_detach((2250, 3700))   # ACTOR-detach from the horse (replicates), keep world xform
g.wire(castG, "AsConan Character", detachG, "self", exec=False)
chainG.then(detachG)
amodeG = bare_call("SetAnimationMode", SMC, (2500, 3700))
set_default(amodeG, "InAnimationMode", "AnimationBlueprint", "byte", enum="EAnimationMode")
g.wire(rMeshG, "Mesh", amodeG, "self", exec=False)
chainG.then(amodeG)
walkG = bare_call("SetMovementMode", CMC, (2750, 3700))
set_default(walkG, "NewMovementMode", "MOVE_Walking", "byte", enum="EMovementMode")
g.wire(rMoveG, "CharacterMovement", walkG, "self", exec=False)
chainG.then(walkG)
colG = bare_call("SetActorEnableCollision", ACTOR, (3000, 3700))
set_default(colG, "bNewActorEnableCollision", "true", "bool")
g.wire(castG, "AsConan Character", colG, "self", exec=False)
chainG.then(colG)
if DEBUG:
    chainG.then(dbg("sweep-restored a rider (dismount/orphan)", (3250, 3700)))

text = g.render()
n_authored = text.count("Begin Object Class=")
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
res = bp.inject(FULL, text, graph_name="EventGraph")
print("inject:", res)
# PASTE-DROP GUARD: ImportNodesFromText SILENTLY DISCARDS nodes whose function ref doesn't
# resolve on this build (no orphan, no compile error -- downstream pins just lose their links;
# this is how GetPlayerState vanished in v34/v35 and killed the per-player pass). authored !=
# pasted is the only tell.
dropped = n_authored - (res.get("pasted") or 0)
if dropped:
    print("!! PASTE DROPPED %d NODE(S): authored %d, pasted %d -- a function ref didn't"
          " resolve on this build. Diff the render against the readback to find it." %
          (dropped, n_authored, res.get("pasted")))

# stamp the build version on the CDO so we can tell which class actually spawns
# (read instance.MgrVersion to detect a cached old class)
gc = unreal.load_object(None, FULL + "_C")
if gc:
    cdo = unreal.get_default_object(gc)
    cdo.set_editor_property("MgrVersion", MOD.MGR_VERSION)
    # ALWAYS RELEVANT: a logic actor (hidden root, no collision) is otherwise NOT relevant to
    # clients, so it never replicates there -> no client instance -> its tick/multicast never reach
    # clients (the root cause of every "host-only" result). Always Relevant = it exists + ticks on
    # every client. (Conan modding wiki: Replication / Relevancy.)
    cdo.set_editor_property("always_relevant", True)
    # PERF: tick at 10 Hz instead of every frame. The whole mod is polling logic; 100 ms of
    # seat/maintain/restore latency is imperceptible, and it cuts the per-frame
    # GetAllActorsOfClass + anim-reset sweep cost ~6x on every instance (server AND clients).
    try:
        tickfn = cdo.get_editor_property("primary_actor_tick")
        tickfn.set_editor_property("tick_interval", 0.1)
        cdo.set_editor_property("primary_actor_tick", tickfn)
        print("CDO tick_interval=0.1 set")
    except Exception as e:
        print("tick_interval NOT set (perf fix skipped):", e)
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
print("BUILD OK" if not problems and not orphans and not dropped
      else "BUILD HAS ISSUES -- DO NOT PLAY YET")
