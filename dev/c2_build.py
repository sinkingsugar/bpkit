"""C2 manager build (evolving). BP_MountedFollowerManager : ModController.
ReceiveTick:
  - cast player (ConanCharacter); skip the tick if not ready
  - Seq.0: init-guard -> raise 'Mount' cap once (Initialized bool)
  - Seq.1: mount-transition detect -> print MOUNT / DISMOUNT (Step C hangs the
    match+stow / restore here); track WasMounted bool
Run with Play STOPPED.  Run: python ue_run.py dev/c2_build.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge", "bp_author", "bp_compact"):
    sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp
import bp_ir as ir
import bp_compact as bc

PKG, NAME = "/Game/_Scratch", "BP_MountedFollowerManager"
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
CONAN = "/Script/ConanSandbox.ConanCharacter"
TSC = "/Script/ConanSandbox.ThrallSystemComponent"
GS = "/Script/Engine.GameplayStatics"
KSL = "/Script/Engine.KismetSystemLibrary"
KML = "/Script/Engine.KismetMathLibrary"

# edit in place (reuse if present) -- deleting+recreating leaves a stale redirector
# that blocks recreate; the manager uses override EVENTS (not custom events) so
# clear+reinject is safe (no collision-rename).
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL)
boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
for vn in ("Initialized", "WasMounted"):
    unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, vn, boolt)  # no-ops if exists

g = ir.Graph("EventGraph")

def cast_node(target, pos):
    return g.node("K2Node_DynamicCast",
                  ['TargetType="/Script/CoreUObject.Class\'%s\'"' % target], base="DynamicCast", pos=pos)

def seq_node(pos):
    return g.node("K2Node_ExecutionSequence", [], base="Seq", pos=pos)

tick = g.event("ReceiveTick")
getP = g.call("GetPlayerCharacter", GS, pos=(0, 350))
g.typed_input(getP, "PlayerIndex", "0", "int")
cast = cast_node(CONAN, (250, 0))
g.wire(tick, "then", cast, "execute", exec=True)
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
setInit = g.var_set("Initialized", "bool", pos=(1600, 0))
setInit.pin("Initialized").literal("true")
g.wire(addAdj, "then", setInit, "execute", exec=True)

# --- Seq.1: mount-transition detect ---
# NB: player.GetMount() is broken (returns None while riding); GetMountInput is the
# reliable signal (valid when mounted, None when off). See mem player-getmount-broken.
getMount = g.call("GetMountInput", CONAN, pos=(750, 600))
g.wire(PLAYER[0], PLAYER[1], getMount, "self", exec=False)
isValid = g.call("IsValid", KSL, pos=(950, 600))
g.wire(getMount, "ReturnValue", isValid, "Object", exec=False)
getWas = g.var_get("WasMounted", "bool", pos=(950, 800))
neq = g.call("NotEqual_BoolBool", KML, pos=(1150, 700))
g.wire(isValid, "ReturnValue", neq, "A", exec=False)
g.wire(getWas, "WasMounted", neq, "B", exec=False)

seq2 = seq_node((1100, 500))
g.wire(seq, "then_1", seq2, "execute", exec=True)
bChanged = g.branch(pos=(1350, 500))
g.wire(seq2, "then_0", bChanged, "execute", exec=True)
g.wire(neq, "ReturnValue", bChanged, "Condition", exec=False)
bMounted = g.branch(pos=(1600, 500))
g.wire(bChanged, "then", bMounted, "execute", exec=True)
g.wire(isValid, "ReturnValue", bMounted, "Condition", exec=False)
# MOUNT: ForEach the player's followers, print for each non-mount (a follower to stow)
getTSC2 = g.call("GetThrallSystemComponent", CONAN, pos=(1850, 350))
g.wire(PLAYER[0], PLAYER[1], getTSC2, "self", exec=False)
getFol = g.call("GetFollowingThrallCharacters", TSC, pos=(2100, 350))
g.wire(getTSC2, "ReturnValue", getFol, "self", exec=False)
loop = g.foreach(CONAN, pos=(2350, 420))
g.wire(getFol, "ReturnValue", loop, "Array", exec=False)
g.wire(bMounted, "then", loop, "Exec", exec=True)
isMount = g.call("IsMount", CONAN, pos=(2600, 620))
g.wire(loop, "Array Element", isMount, "self", exec=False)
bIsMount = g.branch(pos=(2800, 450))
g.wire(loop, "LoopBody", bIsMount, "execute", exec=True)
g.wire(isMount, "ReturnValue", bIsMount, "Condition", exec=False)
pStow = g.call("PrintString", KSL, pos=(3050, 420))
g.typed_input(pStow, "InString", "STOW A FOLLOWER", "string")
g.wire(bIsMount, "else", pStow, "execute", exec=True)   # not a mount -> a follower to stow
pDis = g.call("PrintString", KSL, pos=(1850, 650))
g.typed_input(pDis, "InString", "FOLLOWERS: DISMOUNT", "string")
g.wire(bMounted, "else", pDis, "execute", exec=True)
# Seq2.1: update WasMounted = isMounted (every tick)
setWas = g.var_set("WasMounted", "bool", pos=(1350, 850))
g.wire(isValid, "ReturnValue", setWas, "WasMounted", exec=False)
g.wire(seq2, "then_1", setWas, "execute", exec=True)

text = g.render()
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("ORPHANS:", len(orphans), orphans if orphans else "(clean)")
