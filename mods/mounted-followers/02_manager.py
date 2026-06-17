"""C2 manager build (canonical). BP_MountedFollowerManager : ModController.
ReceiveTick:
  - cosmetic seat loop first, on every RENDER-capable instance (clients + listen
    host + SP); a dedicated server skips it (no render). Ungated by mount state.
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
import re
from bpkit import bridge as bp, ir, build, compact as bc, config as _cfg
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
UMGLIB = "/Script/UMG.WidgetBlueprintLibrary"
USERWIDGET = "/Script/UMG.UserWidget"
TEXTBLOCK = "/Script/UMG.TextBlock"
OVERLAY_WBP = "%s/WBP_DebugOverlay.WBP_DebugOverlay_C" % PKG   # generated class of the debug widget
DTAB = "/Script/Engine.DataTable"
GAMESTATE = "/Script/Engine.GameStateBase"   # has PlayerArray (cheap player enumeration; v40)
PSTATE = "/Script/Engine.PlayerState"
SG_CLS_PATH = "%s/%s.%s_C" % (PKG, MOD.SAVEGAME, MOD.SAVEGAME)   # BP_MF_SaveGame generated class
MODCTRL = unreal.ModController.static_class().get_path_name()    # ModController (declares MergeDataTables)
DT_CMD_OBJ = MOD.full(MOD.CMD_TABLE)                              # our 1-row command table (object path)
_ccc = MOD.CUSTOM_CMD_TABLE
CUSTOM_CMD_OBJ = "%s.%s" % (_ccc, _ccc.rsplit("/", 1)[1])        # game's CustomConsoleCommandsDataTable

# === DIAGNOSTIC FLAGS (see README §Debugging) ===
# DEBUG: PIE-only PrintString beacons at the one-shot beats (caps/stow/sweep/rescue + leash
#   catch). On screen + log + `~` console. PrintString is compiled OUT of Shipping (screen,
#   log AND console -- a shipped build logs NOTHING from BP), so these never reach players --
#   but flip False for the release deploy to keep the graph lean.
# HUD_DIAG: optional SHIP-VISIBLE HUDShowFIFO banner ("kept a rider seated", once per ride)
#   when the maintain pass catches the leash AI re-mobilizing a seated rider -- the ONLY
#   channel that survives Shipping (proven v26-v32). Default OFF: the shipped mod is silent.
DEBUG = True
HUD_DIAG = False
# OVERLAY: reusable in-game debug overlay (UMG WBP_DebugOverlay, a persistent on-screen text panel
#   that survives Shipping -- unlike PrintString). Built client-side on the render path. SPIKE STAGE:
#   currently just creates the widget + shows a static "alive" string to prove the BP create/show pipe
#   (Python can't init UMG widgets -- CreateWidget is BP-only). Next: pump the follower-AI state string.
OVERLAY = True   # debug overlay via g.create_widget (K2Node_CreateWidget). SPIKE: static "alive" text.

# edit in place (reuse if present) -- deleting+recreating leaves a stale redirector
# that blocks recreate; the manager uses override EVENTS (not custom events) so
# clear+reinject is safe (no collision-rename).
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL)
# build-version tag (CDO default set below) to detect which class actually spawns
intt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
# MountLimit: the resolved Mount-cap N for the player being initialized (loaded from the SaveGame
# slot, else DEFAULT_MOUNT_LIMIT). Scratch per-player-init (the player ForEach body runs to
# completion per element, like PlayerMount).
for vn in ("MgrVersion", "HumanoidCounter", "MountLimit"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, intt)  # no-ops if exists
# v40 PERF GATE (revised -- no MP trade-off):
#  - The COSMETIC loop runs on every RENDER-capable instance (clients + listen host + SP), ungated, so
#    each client always re-derives EVERYONE's seated-follower pose (the mod never replicated custom
#    state -- it recomputes per-instance from native attach/get_rider replication). Only a *dedicated*
#    server (no render, anim invisible + non-replicated) skips it -> is_dedicated_server gate.
#  - The server's expensive GLOBAL SWEEP (its own GetAllActorsOfClass) gates on SweepRun = AnyMounted
#    OR WasMounted (1-tick trailing so a just-dismounted/orphaned seat is still restored the tick after
#    the last mount). AnyMounted is set in the server per-player GetRider detect. WasMounted = last
#    tick's AnyMounted. So an idle DEDICATED server does ZERO GetAllActorsOfClass.
_boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
for vn in ("AnyMounted", "SweepRun", "WasMounted"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, _boolt)
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
if OVERLAY:
    # holds the created debug-overlay widget instance (created once, client-side)
    uw_ref = unreal.BlueprintEditorLibrary.get_object_reference_type(unreal.UserWidget.static_class())
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "OverlayWidget", uw_ref)
    # per-tick string accumulator for the follower-state dump
    _strt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("string")
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "OverlayText", _strt)
if DEBUG or HUD_DIAG:
    # once-per-ride latch for the leash-catch report (re-armed while unmounted)
    boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "ReportedCatch", boolt)
ANIM = MOD.IDLE_ANIM

g = ir.Graph("EventGraph")

# === bpkit library bindings ==================================================
# Engine-generic node-builders (cast / get_all_actors / array_* / var_* / chain)
# now live on ir.Graph; the Conan/gameplay-specific ones (comp_of / attach /
# detach / HUD) live in mf_nodes. These thin adapters bind them to THIS module's
# graph `g` and keep the historical local names, so the graph body below is
# UNCHANGED (the gotcha-encoding bodies are gone -- they're in the library now).
sys.modules.pop("mf_nodes", None)
import mf_nodes as mf
CHAR, SMC, SCENE, CMC, ACTOR, CAPSULE = mf.CHAR, mf.SMC, mf.SCENE, mf.CMC, mf.ACTOR, mf.CAPSULE
CLS, STRUCTS, ENUM = mf.CLS, mf.STRUCTS, mf.ENUM

def cast_node(target, pos):         return g.cast(target, pos)
def get_all_actors(cls_path, pos):  return g.get_all_actors(cls_path, pos)
def bare_call(member, parent, pos): return g.call(member, parent, pos=pos)
def Chain(node, pin):               return g.chain(node, pin)
def arr_fn(member, elem_sub, pos):  return g.array_fn(member, pos, elem_sub=elem_sub)
def arr_var(name, elem_sub, pos):   return g.array_var(name, pos, elem_sub=elem_sub)
def arr_item_pin(node, pin_name, elem_sub):
    return g.array_item_pin(node, pin_name, elem_sub=elem_sub)
def get_item(arr_node, arr_pin, idx_node, idx_pin, elem_sub, pos):
    return g.array_get(arr_node, arr_pin, (idx_node, idx_pin), pos, elem_sub=elem_sub)

def type_obj(pin, cls_path):        mf.type_obj(pin, cls_path)
def type_struct(pin, struct_path):  mf.type_struct(pin, struct_path)
def var_self(name, pos):            return mf.var_self(g, name, pos)
def var_set_m(name, pos):           return mf.var_set_m(g, name, pos)
def comp_of(target, target_pin, comp_var, pos, parent=CHAR):
    return mf.comp_of(g, target, target_pin, comp_var, pos, parent)
def set_default(node, pin, value, category, enum=None):
    mf.set_default(node, pin, value, category, enum)
def attach_node(pos, socket, rules="SnapToTarget"):  return mf.attach_component(g, pos, socket, rules)
def actor_attach(pos, socket, rules="SnapToTarget"): return mf.attach_actor(g, pos, socket, rules)
def actor_detach(pos, rules="KeepWorld"):            return mf.detach_actor(g, pos, rules)
def dbg(msg, pos):                  return mf.dbg(g, msg, pos, MOD.MGR_VERSION)
def txt_lit(s, pos):                return mf.txt_lit(g, s, pos)
def fifo(txt_node, pos):            return mf.fifo(g, txt_node, pos)

# === v45 helpers: leash push/pop (Conan's OWN primitives) + console state dump ===============
# The follower-AI jam is LEASHING. While seated we re-pin MOVE_None every tick, which fights Conan's
# catch-up/leash AI and JAMS it -- the follower comes off the saddle stuck on BT_Leashing (combat
# suppressed, engagement overridden to PASSIVE/DEFENSIVE) and won't auto-engage until it re-aggros
# (AstroCat 2026-06; cook-only -- the leash never trips in PIE). v43 (try_resume+cancel) and v44
# (reset_all_subtrees) were piecemeal restore-side guesses. v45 uses Conan's OWN pair, found by
# dumping BTTask_FinishLeashing + reflecting the ConanAttackerAIController surface (docs/CONAN-AI.md):
#   STOW push   -> SetShouldNotLeash(true): the leash never trips while seated, so catch-up never
#                  engages and there is nothing to jam (the per-tick MOVE_None re-pin is now belt).
#   RESTORE pop -> SetShouldNotLeash(false) + FinishLeashing(): re-enable leashing and run the game's
#                  own clean leash-exit -- exactly what Conan's BT_Leashing finish task calls.
# Both live on ConanAttackerAIController (HumanAIController extends it): GetController -> cast -> call.
# A follower whose controller isn't a ConanAttackerAIController fails the cast and is skipped (terminal).
PAWN = "/Script/Engine.Pawn"
ATKCTRL = "/Script/ConanSandbox.ConanAttackerAIController"
ATKCAST = "AsConan Attacker AIController"   # DynamicCast success pin (verified in BTTask_FinishLeashing)
KSL_STR = "/Script/Engine.KismetStringLibrary"

def bool_lit(val, pos):
    """Revert-proof bool literal: MakeLiteralBool(unset)=false; Not_PreBool flips it to true. (A wired
    pin can't silently revert to its autogen default the way a set pin-default can -- bp_ir bool gap.)"""
    mk = g.call("MakeLiteralBool", KSL, pos=pos)
    if not val:
        return mk, "ReturnValue"
    nt = g.call("Not_PreBool", KML, pos=(pos[0] + 190, pos[1]))
    g.wire(mk, "ReturnValue", nt, "A", exec=False)
    return nt, "ReturnValue"

def _ctrl_cast(fol, fol_pin, pos):
    """GetController (pure) -> cast ConanAttackerAIController. Returns the cast node (exec ENTRY --
    wire the running exec into its 'execute'; cast-fail dead-ends -> the follower is skipped)."""
    x, y = pos
    getc = g.call("GetController", PAWN, pos=(x, y + 220))
    g.wire(fol, fol_pin, getc, "self", exec=False)
    cst = g.cast(ATKCTRL, pos=(x + 230, y))
    g.wire(getc, "ReturnValue", cst, "Object", exec=False)
    return cst

def no_leash_on(fol, fol_pin, pos):
    """STOW push: SetShouldNotLeash(true) on the follower's controller. Returns the cast (exec entry)."""
    x, y = pos
    cst = _ctrl_cast(fol, fol_pin, pos)
    noL = g.call("SetShouldNotLeash", ATKCTRL, pos=(x + 490, y))
    tn, tp = bool_lit(True, (x + 300, y + 260))
    g.wire(tn, tp, noL, "NewShouldNotLeash", exec=False)
    g.wire(cst, ATKCAST, noL, "self", exec=False)
    g.wire(cst, "then", noL, "execute", exec=True)
    return cst

def restore_leash(fol, fol_pin, pos):
    """RESTORE pop: SetShouldNotLeash(false) + FinishLeashing() -- Conan's own clean leash-exit
    (mirrors BTTask_FinishLeashing). Returns the cast (exec entry)."""
    x, y = pos
    cst = _ctrl_cast(fol, fol_pin, pos)
    noL = g.call("SetShouldNotLeash", ATKCTRL, pos=(x + 490, y))
    fn, fp = bool_lit(False, (x + 300, y + 260))
    g.wire(fn, fp, noL, "NewShouldNotLeash", exec=False)
    g.wire(cst, ATKCAST, noL, "self", exec=False)
    g.wire(cst, "then", noL, "execute", exec=True)
    fin = g.call("FinishLeashing", ATKCTRL, pos=(x + 760, y))
    g.wire(cst, ATKCAST, fin, "self", exec=False)
    g.wire(noL, "then", fin, "execute", exec=True)
    return cst

def dump_ai(fol, fol_pin, pos):
    """DEBUG console line via PrintString (our dbg channel): 'MF vN dismount leash=<b>' -- the
    follower's leash/catch-up state at dismount. Returns the PrintString exec node. (IsAIControllerLeashing
    is pure -> safe as data; HaveValidTarget was dropped -- it's IMPURE and pruned when used as a pure pin.)"""
    x, y = pos
    lz = g.call("IsAIControllerLeashing", CONAN, pos=(x, y + 200))
    g.wire(fol, fol_pin, lz, "self", exec=False)
    bs1 = g.call("Conv_BoolToString", KSL_STR, pos=(x + 220, y + 200))
    g.wire(lz, "ReturnValue", bs1, "InBool", exec=False)
    c1 = g.call("Concat_StrStr", KSL_STR, pos=(x + 440, y + 120))
    g.typed_input(c1, "A", "MF v%d dismount leash=" % MOD.MGR_VERSION, "string")
    g.wire(bs1, "ReturnValue", c1, "B", exec=False)
    p = g.call("PrintString", KSL, pos=(x + 660, y))
    g.wire(c1, "ReturnValue", p, "InString", exec=False)
    return p

# === COSMETIC SEAT loop -- driven from ReceiveTick below on every RENDER-capable instance (clients +
# listen host + SP); a dedicated server skips it (v41 IsDedicatedServer gate -- no render). Ungated by
# mount state. Now that the manager is Always Relevant it actually exists + ticks on clients, so this
# applies the seated single-node anim LOCALLY on each client. (v14 logic, which was correct -- it just
# never ran on clients because the manager wasn't relevant.) ===
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
# v41 PERF: the OLD tick blindly ran GetAllActorsOfClass(ConanCharacter) -- O(every player + thrall +
# NPC on the server) -- every tick on every instance, even when nobody was riding. Now: reset the
# AnyMounted gate, run the cheap PlayerArray-driven per-player pass (server) which sets AnyMounted, and
# gate the two expensive GetAllActorsOfClass calls -- the cosmetic on IsDedicatedServer (render-capable
# instances only), the global restore sweep on SweepRun (= AnyMounted OR WasMounted).
resetAM = g.var_set("AnyMounted", "bool", pos=(-700, 0)); resetAM.pin("AnyMounted").literal("false")
g.wire(tick, "then", resetAM, "execute", exec=True)
haz = g.call("HasAuthority", ACTOR, pos=(-500, 0))
bAuth = g.branch(pos=(-300, 0))
g.wire(haz, "ReturnValue", bAuth, "Condition", exec=False)

# v40 (revised -- no MP trade-off): the COSMETIC runs on every RENDER-capable instance (clients +
# listen host + SP), ungated, so each re-derives EVERY seated follower's pose. Only a *dedicated*
# server skips it (no render; the anim is invisible + non-replicated). Both paths then run the
# server pass (bAuth). gaC -> loopMC is wired at the cosmetic-loop definition above.
dds = g.call("IsDedicatedServer", KSL, pos=(-650, -250))   # KismetSystemLibrary, not GameplayStatics
ddsBranch = g.branch(pos=(-450, -250))
g.wire(dds, "ReturnValue", ddsBranch, "Condition", exec=False)
g.wire(resetAM, "then", ddsBranch, "execute", exec=True)
# v46 OVERLAY (render path, before the cosmetic loop): build the debug overlay once + show it, then
# SetText its 'Body'. Client-side (this is the non-dedicated render branch). SPIKE: static text to
# prove the BP create/show pipe (CreateWidget is BP-only -- Python can't init UMG widgets).
if OVERLAY:
    gpc = g.call("GetPlayerController", GS, pos=(-300, -760))   # pure (data)
    g.typed_input(gpc, "PlayerIndex", "0", "int")
    owVal = g.call("IsValid", KSL, pos=(-120, -560))
    g.wire(var_self("OverlayWidget", (-300, -560)), "OverlayWidget", owVal, "Object", exec=False)
    bOw = g.branch(pos=(-120, -760))
    g.wire(ddsBranch, "else", bOw, "execute", exec=True)
    g.wire(owVal, "ReturnValue", bOw, "Condition", exec=False)
    # not created yet -> CreateWidget(WBP_DebugOverlay, OwningPlayer=PC) + store + AddToViewport.
    # K2Node_CreateWidget (the specialized node) -- WidgetBlueprintLibrary.Create isn't paste-resolvable.
    crt = g.create_widget(OVERLAY_WBP, pos=(120, -880))
    g.wire(gpc, "ReturnValue", crt, "OwningPlayer", exec=False)
    g.wire(bOw, "else", crt, "execute", exec=True)
    owStore = var_set_m("OverlayWidget", (380, -880))
    g.wire(crt, "ReturnValue", owStore, "OverlayWidget", exec=False)
    g.wire(crt, "then", owStore, "execute", exec=True)
    atv = g.call("AddToViewport", USERWIDGET, pos=(620, -880))
    g.typed_input(atv, "ZOrder", "1000000", "int")   # debug layer on top of the game HUD (HP bar etc.)
    g.wire(var_self("OverlayWidget", (620, -1060)), "OverlayWidget", atv, "self", exec=False)
    g.wire(owStore, "then", atv, "execute", exec=True)
    # converge (both branches) -> SetText(Body). GetWidgetFromName's Name is a const FName& (by-ref)
    # -> it must be WIRED, a literal default is rejected; feed a MakeLiteralName.
    gwn = g.call("GetWidgetFromName", USERWIDGET, pos=(880, -740))   # pure (data)
    g.wire(var_self("OverlayWidget", (880, -920)), "OverlayWidget", gwn, "self", exec=False)
    mln = g.call("MakeLiteralName", KSL, pos=(660, -560))
    g.typed_input(mln, "Value", "Body", "name")
    g.wire(mln, "ReturnValue", gwn, "Name", exec=False)
    castTB = g.cast(TEXTBLOCK, pos=(1120, -760))
    g.wire(gwn, "ReturnValue", castTB, "Object", exec=False)
    g.wire(bOw, "then", castTB, "execute", exec=True)    # already created -> just set text
    g.wire(atv, "then", castTB, "execute", exec=True)    # just created -> set text
    # --- build the live state string from the LOCAL player's followers (client-side; accurate on a
    # listen/SP host where client==server). Per follower: " [eng=<byte> lsh=<bool>]" appended to the
    # OverlayText accumulator. Built in BP nodes so it survives Shipping (no PrintString/GetAll). ---
    clrTxt = g.var_set("OverlayText", "string", pos=(1120, -1100))
    clrTxt.pin("OverlayText").literal(
        "MFv%d  eng:0=passive 1=def 2=aggr  move:0=FROZEN 1=walk 2=nav 3=fall  "
        "tgt=hasTarget fol=following cd=canAttack(cooldownDone)" % MOD.MGR_VERSION)
    g.wire(castTB, "then", clrTxt, "execute", exec=True)
    getPawn = g.call("K2_GetPawn", "/Script/Engine.Controller", pos=(620, -1280))   # pure
    g.wire(gpc, "ReturnValue", getPawn, "self", exec=False)
    castLP = g.cast(CONAN, pos=(860, -1100))
    g.wire(getPawn, "ReturnValue", castLP, "Object", exec=False)
    g.wire(clrTxt, "then", castLP, "execute", exec=True)
    getTSCo = g.call("GetThrallSystemComponent", CONAN, pos=(1100, -1300))   # pure
    g.wire(castLP, "AsConan Character", getTSCo, "self", exec=False)
    getFolO = g.call("GetFollowingThrallCharacters", TSC, pos=(1340, -1300))  # pure
    g.wire(getTSCo, "ReturnValue", getFolO, "self", exec=False)
    loopO = g.foreach(CONAN, pos=(1100, -1100))
    g.wire(getFolO, "ReturnValue", loopO, "Array", exec=False)
    g.wire(castLP, "then", loopO, "Exec", exec=True)
    # per-follower fields. The controller cast to ConanAttackerAIController GATES the append: it
    # succeeds for HUMANOID followers (HumanAIController extends it) and CastFails for horses
    # (CreatureAIController) -> the readout shows only the humanoids that actually have the dismount-AI
    # bug (horses skipped, no clutter). Every field read is PURE (safe as a data pin).
    eb = g.call("GetEngagementBehavior", CONAN, pos=(1340, -1880))
    g.wire(loopO, "Array Element", eb, "self", exec=False)
    ebs = g.call("Conv_ByteToString", KSL_STR, pos=(1560, -1880))   # enum is byte-backed
    g.wire(eb, "ReturnValue", ebs, "InByte", exec=False)
    lz = g.call("IsAIControllerLeashing", CONAN, pos=(1340, -1780))
    g.wire(loopO, "Array Element", lz, "self", exec=False)
    lzs = g.call("Conv_BoolToString", KSL_STR, pos=(1560, -1780))
    g.wire(lz, "ReturnValue", lzs, "InBool", exec=False)
    # movement mode (0=None=FROZEN, 1=Walking, 3=NavWalking) -- VariableGet off the CMC (statue-rescue pattern)
    rMoveOv = comp_of(loopO, "Array Element", "CharacterMovement", (1340, -1660))
    mmOv = g.node("K2Node_VariableGet",
        ['VariableReference=(MemberName="MovementMode",MemberParent="/Script/CoreUObject.Class\'%s\'",bSelfContext=False)' % CMC],
        base="VariableGet", pos=(1560, -1660))
    spOv = mmOv.pin("self"); spOv.dir = "EGPD_Input"; type_obj(spOv, CMC)
    opOv = mmOv.pin("MovementMode"); opOv.dir = "EGPD_Output"
    opOv.set("PinType.PinCategory", '"byte"'); opOv.set("PinType.PinSubCategoryObject", ENUM["EMovementMode"])
    g.wire(rMoveOv, "CharacterMovement", mmOv, "self", exec=False)
    mvs = g.call("Conv_ByteToString", KSL_STR, pos=(1780, -1660))
    g.wire(mmOv, "MovementMode", mvs, "InByte", exec=False)
    # still attached to a horse? (stuck-seated tell)
    getParOv = g.call("GetAttachParentActor", ACTOR, pos=(1340, -1540))
    g.wire(loopO, "Array Element", getParOv, "self", exec=False)
    seatV = g.call("IsValid", KSL, pos=(1560, -1540))
    g.wire(getParOv, "ReturnValue", seatV, "Object", exec=False)
    seats = g.call("Conv_BoolToString", KSL_STR, pos=(1780, -1540))
    g.wire(seatV, "ReturnValue", seats, "InBool", exec=False)
    # FILTER to humanoids: horses also cast to ConanAttackerAIController (CreatureAIController extends it),
    # so the cast doesn't exclude them -- IsMountable does (true=horse). Skip mountables; only humanoid
    # followers (the ones with the dismount-AI bug) reach the cast + append.
    mtblOv = g.call("IsMountable", CONAN, pos=(1100, -1380))
    g.wire(loopO, "Array Element", mtblOv, "self", exec=False)
    bMtblOv = g.branch(pos=(1300, -1100))
    g.wire(loopO, "LoopBody", bMtblOv, "execute", exec=True)
    g.wire(mtblOv, "ReturnValue", bMtblOv, "Condition", exec=False)
    # controller (humanoid only): GetController -> cast -> is_attacking / is_in_combat_range
    getCtrlOv = g.call("GetController", PAWN, pos=(1340, -1380))
    g.wire(loopO, "Array Element", getCtrlOv, "self", exec=False)
    castCtrlOv = g.cast(ATKCTRL, pos=(1580, -1160))
    g.wire(getCtrlOv, "ReturnValue", castCtrlOv, "Object", exec=False)
    g.wire(bMtblOv, "else", castCtrlOv, "execute", exec=True)   # not mountable = humanoid -> proceed (horse skipped)
    atk = g.call("IsAttacking", ATKCTRL, pos=(1340, -1280))
    g.wire(castCtrlOv, ATKCAST, atk, "self", exec=False)
    atks = g.call("Conv_BoolToString", KSL_STR, pos=(1560, -1280))
    g.wire(atk, "ReturnValue", atks, "InBool", exec=False)
    cmb = g.call("IsInCombatRange", ATKCTRL, pos=(1340, -1180))
    g.wire(castCtrlOv, ATKCAST, cmb, "self", exec=False)
    cmbs = g.call("Conv_BoolToString", KSL_STR, pos=(1560, -1180))
    g.wire(cmb, "ReturnValue", cmbs, "InBool", exec=False)
    # fol = is_following (PURE -- safe as data); cd = is_attack_cooldown_done (IMPURE -> wired into the
    # exec chain below alongside have_valid_target, else it prunes). Both off the cast controller.
    folc = g.call("IsFollowing", ATKCTRL, pos=(1780, -1280))
    g.wire(castCtrlOv, ATKCAST, folc, "self", exec=False)
    fols = g.call("Conv_BoolToString", KSL_STR, pos=(1980, -1280))
    g.wire(folc, "ReturnValue", fols, "InBool", exec=False)
    cdc = g.call("IsAttackCooldownDone", ATKCTRL, pos=(1780, -1180))
    g.wire(castCtrlOv, ATKCAST, cdc, "self", exec=False)
    cds = g.call("Conv_BoolToString", KSL_STR, pos=(1980, -1180))
    g.wire(cdc, "ReturnValue", cds, "InBool", exec=False)
    # have_valid_target is IMPURE -> call it IN the exec chain (between the cast and the append), not as a
    # pure data pin (which prunes it -- the v44 lesson). Its bool result feeds the line. This is the field
    # the "HUD shows nothing weird while it keeps getting hit" symptom points at: does the AI see a target?
    hvt = g.call("HaveValidTarget", CONAN, pos=(1340, -1080))
    g.wire(loopO, "Array Element", hvt, "self", exec=False)
    hvts = g.call("Conv_BoolToString", KSL_STR, pos=(1560, -1080))
    g.wire(hvt, "ReturnValue", hvts, "InBool", exec=False)
    # line = "  | eng=<e> leash=<l> move=<m> seat=<s> atk=<a> combat=<c> tgt=<t>" (alternating lit/value concats)
    k1 = g.call("Concat_StrStr", KSL_STR, pos=(2000, -1700)); g.typed_input(k1, "A", "  | eng=", "string"); g.wire(ebs, "ReturnValue", k1, "B", exec=False)
    k2 = g.call("Concat_StrStr", KSL_STR, pos=(2180, -1700)); g.wire(k1, "ReturnValue", k2, "A", exec=False); g.typed_input(k2, "B", " leash=", "string")
    k3 = g.call("Concat_StrStr", KSL_STR, pos=(2360, -1700)); g.wire(k2, "ReturnValue", k3, "A", exec=False); g.wire(lzs, "ReturnValue", k3, "B", exec=False)
    k4 = g.call("Concat_StrStr", KSL_STR, pos=(2540, -1700)); g.wire(k3, "ReturnValue", k4, "A", exec=False); g.typed_input(k4, "B", " move=", "string")
    k5 = g.call("Concat_StrStr", KSL_STR, pos=(2720, -1700)); g.wire(k4, "ReturnValue", k5, "A", exec=False); g.wire(mvs, "ReturnValue", k5, "B", exec=False)
    k6 = g.call("Concat_StrStr", KSL_STR, pos=(2900, -1700)); g.wire(k5, "ReturnValue", k6, "A", exec=False); g.typed_input(k6, "B", " seat=", "string")
    k7 = g.call("Concat_StrStr", KSL_STR, pos=(3080, -1700)); g.wire(k6, "ReturnValue", k7, "A", exec=False); g.wire(seats, "ReturnValue", k7, "B", exec=False)
    k8 = g.call("Concat_StrStr", KSL_STR, pos=(3260, -1700)); g.wire(k7, "ReturnValue", k8, "A", exec=False); g.typed_input(k8, "B", " atk=", "string")
    k9 = g.call("Concat_StrStr", KSL_STR, pos=(3440, -1700)); g.wire(k8, "ReturnValue", k9, "A", exec=False); g.wire(atks, "ReturnValue", k9, "B", exec=False)
    k10 = g.call("Concat_StrStr", KSL_STR, pos=(3620, -1700)); g.wire(k9, "ReturnValue", k10, "A", exec=False); g.typed_input(k10, "B", " combat=", "string")
    k11 = g.call("Concat_StrStr", KSL_STR, pos=(3800, -1700)); g.wire(k10, "ReturnValue", k11, "A", exec=False); g.wire(cmbs, "ReturnValue", k11, "B", exec=False)
    k12 = g.call("Concat_StrStr", KSL_STR, pos=(3980, -1700)); g.wire(k11, "ReturnValue", k12, "A", exec=False); g.typed_input(k12, "B", " tgt=", "string")
    k13 = g.call("Concat_StrStr", KSL_STR, pos=(4160, -1700)); g.wire(k12, "ReturnValue", k13, "A", exec=False); g.wire(hvts, "ReturnValue", k13, "B", exec=False)
    k14 = g.call("Concat_StrStr", KSL_STR, pos=(4340, -1700)); g.wire(k13, "ReturnValue", k14, "A", exec=False); g.typed_input(k14, "B", " fol=", "string")
    k15 = g.call("Concat_StrStr", KSL_STR, pos=(4520, -1700)); g.wire(k14, "ReturnValue", k15, "A", exec=False); g.wire(fols, "ReturnValue", k15, "B", exec=False)
    k16 = g.call("Concat_StrStr", KSL_STR, pos=(4700, -1700)); g.wire(k15, "ReturnValue", k16, "A", exec=False); g.typed_input(k16, "B", " cd=", "string")
    k17 = g.call("Concat_StrStr", KSL_STR, pos=(4880, -1700)); g.wire(k16, "ReturnValue", k17, "A", exec=False); g.wire(cds, "ReturnValue", k17, "B", exec=False)
    # append (only reached on cast success -> humanoid followers only)
    otGet = g.var_get("OverlayText", "string", pos=(2000, -1060))
    appc = g.call("Concat_StrStr", KSL_STR, pos=(5060, -1460)); g.wire(otGet, "OverlayText", appc, "A", exec=False); g.wire(k17, "ReturnValue", appc, "B", exec=False)
    setOT = g.var_set("OverlayText", "string", pos=(4560, -1160))
    g.wire(appc, "ReturnValue", setOT, "OverlayText", exec=False)
    g.wire(castCtrlOv, "then", hvt, "execute", exec=True)   # cast ok -> target (impure)...
    g.wire(hvt, "then", cdc, "execute", exec=True)          # ...-> cooldown (also impure)...
    g.wire(cdc, "then", setOT, "execute", exec=True)        # ...-> append
    # loop done -> SetText(Body, OverlayText)
    otGet2 = g.var_get("OverlayText", "string", pos=(2000, -940))
    conv = g.call("Conv_StringToText", KTL, pos=(2220, -940))
    g.wire(otGet2, "OverlayText", conv, "InString", exec=False)
    setTxt = g.call("SetText", TEXTBLOCK, pos=(2440, -1100))
    g.wire(castTB, "AsText", setTxt, "self", exec=False)   # TextBlock display name is "Text" -> AsText
    g.wire(conv, "ReturnValue", setTxt, "InText", exec=False)
    g.wire(loopO, "Completed", setTxt, "execute", exec=True)
    g.wire(setTxt, "then", gaC, "execute", exec=True)      # then continue to the cosmetic loop
    g.wire(castLP, "CastFailed", gaC, "execute", exec=True)  # safety: player not a ConanChar -> skip dump
else:
    g.wire(ddsBranch, "else", gaC, "execute", exec=True)        # render -> cosmetic
g.wire(loopMC, "Completed", bAuth, "execute", exec=True)    # cosmetic done -> server pass
g.wire(ddsBranch, "then", bAuth, "execute", exec=True)      # dedicated -> skip cosmetic, server pass

# (v40 revised: no client-side mount detect needed -- clients run the cosmetic ungated via the
# is_dedicated_server branch above, so they always animate every player's seated followers.)

# NOTE: `dc MFHorses N` registration (merging our command row into the game's
# CustomConsoleCommandsDataTable) is NOT done here. MergeDataTables is BlueprintProtected and ONLY
# resolves inside the ModController `ModDataTableOperations` override -- in the event graph it silently
# drops. That override is built after this graph injects (see the override section near the bottom).

# === v34 PER-PLAYER PASS (the host-only fix). GetPlayerCharacter(0) served exactly one player;
# now EVERY player pawn gets the full treatment. v41: player pawns are enumerated via
# GameState.PlayerArray -> GetPawn -> cast to ConanCharacter (O(players)), NOT by re-walking the
# cosmetic loop's GetAllActorsOfClass result -- so the old IsPlayerControlled/PlayerState filter is gone.
# Stow/restore is LEVEL-TRIGGERED and idempotent instead of transition-edge-triggered: per tick,
# per mounted player, every UNSEATED humanoid follower is stowed (one-shot by construction: the
# seated-check gates it) and every SEATED one gets the v31/v32 leash maintain; per unmounted
# player, every seated follower is restored (one-shot: after the restore it is no longer seated,
# so the v28 every-tick-AnimBP-reinit catastrophe cannot recur). This retires the per-player
# transition machinery -- and a follower whistled mid-ride now saddles up too. (Note: WasMounted is
# reintroduced in v41 purely as the global sweep's 1-tick trailing gate -- see the sweep below.) ===
clrActive = arr_fn("Array_Clear", ir.obj_path(CONAN), (50, 350))
g.wire(arr_var("ActiveSeats", ir.obj_path(CONAN), (50, 550)), "ActiveSeats", clrActive, "TargetArray", exec=False)
g.wire(bAuth, "then", clrActive, "execute", exec=True)   # per-tick: reset the legit-seat set
# v40 PERF: enumerate players via GameState.PlayerArray (O(players)) instead of walking the whole
# GetAllActorsOfClass(ConanCharacter) result (O(every player+thrall+NPC)). The PlayerArray entries ARE
# the players, so the old IsPlayerControlled filter is gone. The whole per-player pass (caps/detect/
# stow/restore) now uses only follower lists -> cheap -> runs every tick (un-gated by mount state, so
# new players still get their cap init). Only the cosmetic (gated on IsDedicatedServer) and the
# global restore sweep (gated on SweepRun) are gated by anything.
gsGet = g.call("GetGameState", GS, pos=(0, 200))
paGet = g.node("K2Node_VariableGet",
    ['VariableReference=(MemberName="PlayerArray",MemberParent="%s",bSelfContext=False)' % ir.obj_path(GAMESTATE)],
    base="VariableGet", pos=(220, 380))
_psp = paGet.pin("self"); _psp.dir = "EGPD_Input"; type_obj(_psp, GAMESTATE)
_pap = paGet.pin("PlayerArray"); _pap.dir = "EGPD_Output"; type_obj(_pap, PSTATE)
_pap.set("PinType.ContainerType", "Array")
g.wire(gsGet, "ReturnValue", paGet, "self", exec=False)
loopPS = g.foreach(PSTATE, pos=(250, 200))
g.wire(paGet, "PlayerArray", loopPS, "Array", exec=False)
g.wire(clrActive, "then", loopPS, "Exec", exec=True)
psPawn = g.call("GetPawn", PSTATE, pos=(450, 400))
g.wire(loopPS, "Array Element", psPawn, "self", exec=False)
castP = cast_node(CONAN, (500, 200))
g.wire(psPawn, "ReturnValue", castP, "Object", exec=False)
g.wire(loopPS, "LoopBody", castP, "execute", exec=True)
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
g.wire(castP, "then", bInitP, "execute", exec=True)   # PlayerArray entries are already players
g.wire(hasInit, "ReturnValue", bInitP, "Condition", exec=False)
prev, prev_pin = bInitP, "else"   # not yet initialized -> SET this player's Mount cap
# v39: MOUNT-ONLY + configurable. Read the limit N from the SaveGame slot (does-exist ? loaded :
# DEFAULT_MOUNT_LIMIT) into the MountLimit member, then SET the Mount group cap =
# reset("Mount") + add("Mount", N). No longer touches Warrior/Crafter/Bearer/Performer/Archer, so
# it can't clobber Better Thralls' groups (the per-tick BT fight -> FPS tank / limit-overwrite bug,
# AstroCat 2026-06-13). Read fresh per new player so a `dc MFHorses N` set mid-session reaches joiners.
dse = g.call("DoesSaveGameExist", GS, pos=(1450, 0))
g.typed_input(dse, "SlotName", MOD.SAVE_SLOT, "string")
g.typed_input(dse, "UserIndex", "0", "int")
g.wire(prev, prev_pin, dse, "execute", exec=True)   # DoesSaveGameExist is IMPURE -> in the exec chain
bSave = g.branch(pos=(1650, 200))
g.wire(dse, "then", bSave, "execute", exec=True)
g.wire(dse, "ReturnValue", bSave, "Condition", exec=False)
# exists -> load + cast + copy the saved MountLimit into the member
loadSG = g.call("LoadGameFromSlot", GS, pos=(1900, -50))
g.typed_input(loadSG, "SlotName", MOD.SAVE_SLOT, "string")
g.typed_input(loadSG, "UserIndex", "0", "int")
g.wire(bSave, "then", loadSG, "execute", exec=True)   # LoadGameFromSlot is IMPURE -> in the exec chain
castSG = cast_node(SG_CLS_PATH, (2150, -50))
g.wire(loadSG, "ReturnValue", castSG, "Object", exec=False)
g.wire(loadSG, "then", castSG, "execute", exec=True)
sgGet = g.var_get("MountLimit", "int", parent=SG_CLS_PATH, pos=(2400, -200))
g.wire(castSG, "AsBP MF Save Game", sgGet, "self", exec=False)
setLimL = g.var_set("MountLimit", "int", pos=(2400, -50))
g.wire(sgGet, "MountLimit", setLimL, "MountLimit", exec=False)
g.wire(castSG, "then", setLimL, "execute", exec=True)
# absent -> default
setLimD = g.var_set("MountLimit", "int", pos=(1900, 320))
setLimD.pin("MountLimit").literal(str(MOD.DEFAULT_MOUNT_LIMIT))
g.wire(bSave, "else", setLimD, "execute", exec=True)
# converge -> SET the Mount cap to MountLimit (reset our prior adjustment, then add N)
rstM = g.call("ResetThrallGroupLimitAdjustment", TSC, pos=(2650, 0))
g.typed_input(rstM, "Group", "Mount", "name")
g.wire(getTSCp, "ReturnValue", rstM, "self", exec=False)
g.wire(setLimL, "then", rstM, "execute", exec=True)
g.wire(setLimD, "then", rstM, "execute", exec=True)   # both branches merge here
addM = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(2900, 0))
g.typed_input(addM, "Group", "Mount", "name")
limGet = g.var_get("MountLimit", "int", pos=(2900, 220))
g.wire(limGet, "MountLimit", addM, "Amount", exec=False)
g.wire(getTSCp, "ReturnValue", addM, "self", exec=False)
g.wire(rstM, "then", addM, "execute", exec=True)
# record the player -> apply once per pawn (the dc command re-applies to live players itself)
addInit = arr_fn("Array_Add", ir.obj_path(CONAN), (3150, 0))
g.wire(arr_var("InitializedPlayers", ir.obj_path(CONAN), (3150, -180)), "InitializedPlayers", addInit, "TargetArray", exec=False)
arr_item_pin(addInit, "NewItem", ir.obj_path(CONAN))
g.wire(P[0], P[1], addInit, "NewItem", exec=False)
g.wire(addM, "then", addInit, "execute", exec=True)
initTail = addInit
if DEBUG:
    dbgInit = dbg("Mount cap SET for new player", (3400, 0))
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
# v40: this player is mounted -> raise the gate so the cosmetic + sweep run this tick.
setAMtrue = g.var_set("AnyMounted", "bool", pos=(2500, 250)); setAMtrue.pin("AnyMounted").literal("true")
g.wire(bMountedP, "then", setAMtrue, "execute", exec=True)
clrOcc = arr_fn("Array_Clear", ir.obj_path(CONAN), (2550, 300))
g.wire(arr_var("OccupiedHorses", ir.obj_path(CONAN), (2550, 520)), "OccupiedHorses", clrOcc, "TargetArray", exec=False)
g.wire(setAMtrue, "then", clrOcc, "execute", exec=True)
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
# v42: REMOVED the per-spare-horse follow-distance stagger (was SetAdditionalFollowDistance =
# index*180 while mounted, reset to 0 when on foot -- see the unmounted pass below). It was
# purely cosmetic spacing (fan the spare horses into a trailing line) but it CLOBBERED the
# player's own follow-distance setting: AdditionalFollowDistance is exactly the knob the in-game
# follow-distance control drives, and the unmounted reset forced it to 0 on every horse follower
# every tick (10 Hz), so any distance the player picked snapped back to the base (~5m). Seated
# followers are actor-attached to their horse, so dropping the stagger only means the spare horses
# follow at the player's chosen distance instead of a mod-imposed line. addSpare's exec just ends
# the loop-body chain (the foreach iterates internally).

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
if DEBUG or HUD_DIAG:
    # CATCH DETECTION: sample IsMovingOnGround BEFORE the re-pin -- true means the leash AI
    # actually re-mobilized this seated rider and the maintain pass is earning its keep.
    # Report ONCE per ride (ReportedCatch, re-armed while the owner is on foot). Reporters are
    # flag-dependent: DEBUG -> PrintString (PIE-only; Shipping compiles it to a no-op -- a
    # shipped build logs NOTHING from BP), HUD_DIAG -> HUDShowFIFO (the only ship-visible
    # channel). Both flags off -> no detection nodes at all, just the bare re-pin.
    movingB = g.call("IsMovingOnGround", CMC, pos=(3850, 1300))
    g.wire(rMoveB, "CharacterMovement", movingB, "self", exec=False)
    bMovB = g.branch(pos=(4050, 1300))
    g.wire(bSeatB, "then", bMovB, "execute", exec=True)
    g.wire(movingB, "ReturnValue", bMovB, "Condition", exec=False)
    getRC = g.var_get("ReportedCatch", "bool", pos=(4250, 1150))
    bRC = g.branch(pos=(4300, 1300))
    g.wire(bMovB, "then", bRC, "execute", exec=True)
    g.wire(getRC, "ReportedCatch", bRC, "Condition", exec=False)
    catchTail, catchPin = bRC, "else"   # first catch this ride -> report chain
    if HUD_DIAG:
        fifoCatch = fifo(txt_lit("Mounted Followers v%d: kept a rider seated" % MOD.MGR_VERSION,
                                 (4500, 1100)), (4700, 1150))
        g.wire(catchTail, catchPin, fifoCatch, "execute", exec=True)
        catchTail, catchPin = fifoCatch, "then"
    if DEBUG:
        dbgCatch = dbg("leash maintain caught a re-mobilized rider -- re-pinned", (4900, 1150))
        g.wire(catchTail, catchPin, dbgCatch, "execute", exec=True)
        catchTail, catchPin = dbgCatch, "then"
    setRC = g.var_set("ReportedCatch", "bool", pos=(5100, 1150)); setRC.pin("ReportedCatch").literal("true")
    g.wire(catchTail, catchPin, setRC, "execute", exec=True)
    # all paths converge on the re-pin (exec inputs merge)
    g.wire(setRC, "then", disableM, "execute", exec=True)   # first catch, after the report
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
# v45 PUSH: gate leashing OFF while seated, re-asserted every tick right alongside the MOVE_None
# re-pin. With the leash gated, Conan's catch-up AI never engages on the horse-dragged seated
# follower -> the state machine can't jam -> the follower comes off the saddle clean. (The MOVE_None
# re-pin above is now belt-and-suspenders; SetShouldNotLeash is the actual root-cause cure.)
cstLeashM = no_leash_on(loopB, "Array Element", (4600, 1500))
g.wire(setRotM, "then", cstLeashM, "execute", exec=True)

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

# NOT MOUNTED housekeeping pass over the followers. Horses: nothing (v42 removed the
# follow-distance stagger reset -- it clobbered the player's own setting). Humanoids: STATUE
# RESCUE -- if a horse
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
if DEBUG or HUD_DIAG:
    # re-arm the once-per-ride leash-catch report while the owner is on foot
    setRC0 = g.var_set("ReportedCatch", "bool", pos=(2350, 3050)); setRC0.pin("ReportedCatch").literal("false")
    g.wire(bMountedP, "else", setRC0, "execute", exec=True)
    distEntry = (setRC0, "then")
g.wire(distEntry[0], distEntry[1], loopDist, "Exec", exec=True)
mtblD0 = g.call("IsMountable", CONAN, pos=(2800, 3280))
g.wire(loopDist, "Array Element", mtblD0, "self", exec=False)
bMtblD0 = g.branch(pos=(2800, 3050))
g.wire(loopDist, "LoopBody", bMtblD0, "execute", exec=True)
g.wire(mtblD0, "ReturnValue", bMtblD0, "Condition", exec=False)
# v42: the horse branch (bMtblD0 "then") used to reset SetAdditionalFollowDistance to 0 here --
# removed (see Pass A). A horse follower now needs no unmounted housekeeping, so "then" dead-ends;
# only the humanoid branch ("else") does work (the statue rescue below).
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
# v46 ROOT-CAUSE FIX: restore to MOVE_NavWalking (2), NOT MOVE_Walking (1). AI followers path + fight
# on the navmesh (NavWalking); plain Walking is physics-walking and the AI can't path to targets, so it
# gets hit but won't engage. We froze with MOVE_None, so we must un-freeze to the AI's mode, not Walking
# (the v1 bug -- AstroCat/Giovanni 2026-06-17: works at move=2, fails when stuck at move=1).
set_default(walkD0, "NewMovementMode", "MOVE_NavWalking", "byte", enum="EMovementMode")
g.wire(rMoveD0, "CharacterMovement", walkD0, "self", exec=False)
g.wire(bFrozD0, "then", walkD0, "execute", exec=True)
colD0 = bare_call("SetActorEnableCollision", ACTOR, (4050, 3050))
set_default(colD0, "bNewActorEnableCollision", "true", "bool")
g.wire(loopDist, "Array Element", colD0, "self", exec=False)
g.wire(walkD0, "then", colD0, "execute", exec=True)
# v45: same leash pop as the global sweep -- the orphan/statue-rescue path also needs the follower's
# leash re-enabled + cleanly exited, not just movement+collision back. SetShouldNotLeash(false) +
# FinishLeashing() (replaces v43 try_resume/cancel + v44 reset_all_subtrees).
rescTail, rescPin = colD0, "then"
if DEBUG:
    dbgResc = dbg("statue rescue (unfroze a stranded rider)", (4300, 3050))
    g.wire(colD0, "then", dbgResc, "execute", exec=True)
    rescTail, rescPin = dbgResc, "then"
cstD = restore_leash(loopDist, "Array Element", (4600, 3050))
g.wire(rescTail, rescPin, cstD, "execute", exec=True)

# === GLOBAL RESTORE SWEEP (after the player loop): any humanoid still seated on a horse NO
# mounted player legitimized this tick (ActiveSeats) gets restored. ONE restore path covers
# everything: the normal dismount, a follower that left the follow list mid-ride, and a player
# who logged out while mounted. Players themselves are EXCLUDED via the PlayerState check (a
# riding player can read as attached-to-a-mountable -- "restoring" one would be a forced
# dismount). One-shot by construction: restored -> no longer seated, so the plain AnimBP-mode
# call fires exactly once (no v28 every-tick-reinit recurrence). ===
loopG = g.foreach(ACTOR, pos=(250, 3700))
# v40 (revised): the server's global restore sweep gets its OWN GetAllActorsOfClass, GATED on
# SweepRun = AnyMounted OR WasMounted (1-tick trailing so a just-dismounted/orphaned seat is still
# restored the tick after the last mount). So an idle dedicated server does ZERO GetAllActorsOfClass.
orSweep = g.call("BooleanOR", KML, pos=(-150, 3450))
g.wire(g.var_get("AnyMounted", "bool", pos=(-350, 3400)), "AnyMounted", orSweep, "A", exec=False)
g.wire(g.var_get("WasMounted", "bool", pos=(-350, 3500)), "WasMounted", orSweep, "B", exec=False)
setSweepRun = g.var_set("SweepRun", "bool", pos=(-150, 3550))
g.wire(orSweep, "ReturnValue", setSweepRun, "SweepRun", exec=False)
g.wire(loopPS, "Completed", setSweepRun, "execute", exec=True)   # server per-player pass done
setWasG = g.var_set("WasMounted", "bool", pos=(40, 3550))
g.wire(g.var_get("AnyMounted", "bool", pos=(-150, 3680)), "AnyMounted", setWasG, "WasMounted", exec=False)
g.wire(setSweepRun, "then", setWasG, "execute", exec=True)
sweepGate = g.branch(pos=(230, 3450))
g.wire(g.var_get("SweepRun", "bool", pos=(40, 3380)), "SweepRun", sweepGate, "Condition", exec=False)
g.wire(setWasG, "then", sweepGate, "execute", exec=True)
gaC_s = get_all_actors(CONAN, (430, 3550))   # the sweep's own GAAC -- only runs when SweepRun
g.wire(sweepGate, "then", gaC_s, "execute", exec=True)
g.wire(gaC_s, "OutActors", loopG, "Array", exec=False)
g.wire(gaC_s, "then", loopG, "Exec", exec=True)
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
# v46 ROOT-CAUSE FIX: MOVE_NavWalking (2), not MOVE_Walking (1) -- see the statue-rescue note above.
# This is THE dismount-AI bug: restore left the follower in physics-Walking, where the AI can't path/fight.
set_default(walkG, "NewMovementMode", "MOVE_NavWalking", "byte", enum="EMovementMode")
g.wire(rMoveG, "CharacterMovement", walkG, "self", exec=False)
chainG.then(walkG)
colG = bare_call("SetActorEnableCollision", ACTOR, (3000, 3700))
set_default(colG, "bNewActorEnableCollision", "true", "bool")
g.wire(castG, "AsConan Character", colG, "self", exec=False)
chainG.then(colG)
# v45: POP THE LEASH -- the matched counterpart of the stow's SetShouldNotLeash(true) push. The seated
# maintain pass disabled leashing while seated; here we re-enable it AND run Conan's own clean leash-exit
# so the post-dismount leash behaves like a normal follower's (the catch-up machine is never left jammed).
# SetShouldNotLeash(false) + FinishLeashing() is exactly what Conan's BT_Leashing finish task calls --
# it clears the leash subtree + its engagement-behaviour override the way the game does (replaces v43's
# TryResume/Cancel + v44's ResetAllBehaviorSubtreesToDefault). Cooked/real-server only -- no leash in PIE.
if DEBUG:
    chainG.then(dump_ai(castG, "AsConan Character", (3300, 3450)))   # console: leash state at dismount
    chainG.then(dbg("sweep-restored a rider (dismount/orphan)", (4550, 3700)))
# ungated; terminal (cast-fail = controller isn't a ConanAttackerAIController -> skip).
chainG.then(restore_leash(castG, "AsConan Character", (4900, 3700)))

# Build the EventGraph through the harness: clear + inject (auto-relinks any wire the engine
# drops on paste -- the GetArrayItem.Output class) + compile + save + full scan (dropped
# nodes via count, dropped wires, orphans, wildcards, error nodes) + BUILD OK. The
# ModDataTableOperations override + CDO stamping follow (separate graph / class defaults).
build.build_graph(FULL, g)
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")   # ptrs for the override + CDO below

# === REGISTER `dc MFHorses N`: merge our command row into the game's CustomConsoleCommandsDataTable.
# MergeDataTables is BlueprintProtected -- it resolves ONLY inside the ModController
# `ModDataTableOperations` override (verified: drops in the event graph, resolves here). The base
# ModController calls ModDataTableOperations at mod-init, on every instance (server + clients), which
# is exactly when/where the row must be registered. Pattern (mrq-echo): create the override
# (entry+result via the editor path -- paste can't make an override), inject the merge + table gets as
# a pasted set, then connect_pins the entry exec -> merge (cross-set; paste won't link to the entry). ===
OPFN = "ModDataTableOperations"
op_bp_ptr, op_gptr = bp.create_function_override(bp_obj, OPFN, MODCTRL)
og = ir.Graph(OPFN)
# self-context VariableGets DROP on paste into this function override graph (only entry+merge survive),
# so feed the two tables as asset DefaultObject refs directly on the merge inputs instead.
opMerge = og.node("K2Node_CallFunction",
                  ['FunctionReference=(MemberName="MergeDataTables",bSelfContext=True)'],
                  base="CallFunction", pos=(560, 0))
# Feed the tables as asset DefaultObject refs (self-context VariableGets DROP on paste into a
# function override graph -- verified). The QUOTED object path is the editor's canonical RESOLVED
# form: setting Class'path' normalizes to "path", and unquoted is cleared as unresolvable. So quoted
# == a resolved object ref (verified 2026-06-13).
mi = opMerge.pin("MergeIntoDataTable"); mi.dir = "EGPD_Input"
mi.set("PinType.PinCategory", '"object"'); mi.set("PinType.PinSubCategoryObject", ir.obj_path(DTAB))
mi.set("DefaultObject", '"%s"' % CUSTOM_CMD_OBJ)   # game's CustomConsoleCommandsDataTable
ta = opMerge.pin("ToBeAddedDataTable"); ta.dir = "EGPD_Input"
ta.set("PinType.PinCategory", '"object"'); ta.set("PinType.PinSubCategoryObject", ir.obj_path(DTAB))
ta.set("DefaultObject", '"%s"' % DT_CMD_OBJ)        # our DT_MF_Commands
op_text = og.render(); op_auth = op_text.count("Begin Object Class=")
op_res = bp.inject(FULL, op_text, graph_name=OPFN, compile=False, save=False)
op_drop = op_auth - (op_res.get("pasted") or 0)
print("override inject:", op_res, "authored:", op_auth, "DROPPED %d" % op_drop if op_drop else "")
# live-wire: function entry 'then' exec -> MergeDataTables 'execute' (cross-set)
entry_ptr = merge_ptr = None
for p in bp.graph_nodes(op_gptr):
    head = bp.export_nodes([p]).splitlines()[0]
    if "K2Node_FunctionEntry" in head:
        entry_ptr = p
    elif "K2Node_CallFunction" in head:
        merge_ptr = p
if entry_ptr and merge_ptr:
    a = bp.find_pin(entry_ptr, "then", 1); b = bp.find_pin(merge_ptr, "execute", 0)
    print("entry->merge wired:", bp.connect_pins(a, b) if (a and b) else "PINS MISSING")
else:
    print("!! override entry/merge not found:", bool(entry_ptr), bool(merge_ptr))
bp.mark_structurally_modified(bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
# verify the override graph
op_txt = bp.export_nodes(bp.graph_nodes(op_gptr))
op_orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', op_txt)
op_defs = re.findall(r'DefaultObject=([^,)\s]+)', op_txt)
print("override: MergeDataTables present:", 'MemberName="MergeDataTables"' in op_txt,
      "| table defaults:", op_defs, "| orphans:", op_orph if op_orph else "(clean)")

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
# (EventGraph scan + BUILD OK verdict are handled by build.build_graph above; the override
# graph has its own verify, and the CDO stamping printed its own confirmation.)
