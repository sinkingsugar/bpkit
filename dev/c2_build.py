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
# MOUNT branch -- VERBOSE DEBUG. Exec chain on mount:
#   bMounted.then -> pVer -> pHit -> pCount -> loop.Exec
#   loop.LoopBody -> pBody -> bIsMount(IsMount?) -> else: pStow
#   loop.Completed -> pDone
# Reading the prints: pHit always (mount entered). Then:
#   pCount=0 + pDone, no pBody     -> follower source EMPTY at this tick
#   pCount>0 but NO pBody/pDone    -> loop INERT (stale class / RWT missing)  <-- the cache bug
#   pBody xN but no pStow          -> all followers report IsMount=true (filter)
#   pBody + pStow                  -> WORKING
getVer = g.var_get("MgrVersion", "int", pos=(1850, 250))
pVer = dbg_int("MGR VERSION=", getVer, "MgrVersion", pos=(2050, 250))
g.wire(bMounted, "then", pVer, "execute", exec=True)
pHit = dbg("=== MOUNT DETECTED ===", pos=(2050, 60))
g.wire(pVer, "then", pHit, "execute", exec=True)

getTSC2 = g.call("GetThrallSystemComponent", CONAN, pos=(1850, 420))
g.wire(PLAYER[0], PLAYER[1], getTSC2, "self", exec=False)
getFol = g.call("GetFollowingThrallCharacters", TSC, pos=(2100, 420))
g.wire(getTSC2, "ReturnValue", getFol, "self", exec=False)
# reset DbgCount=0 before the loop (counts followers seen, no wildcard Array_Length)
setCnt0 = g.var_set("DbgCount", "int", pos=(2350, 250)); setCnt0.pin("DbgCount").literal("0")
g.wire(pHit, "then", setCnt0, "execute", exec=True)

loop = g.foreach(CONAN, pos=(2650, 420))
g.wire(getFol, "ReturnValue", loop, "Array", exec=False)
g.wire(setCnt0, "then", loop, "Exec", exec=True)
pBody = dbg("LOOP BODY (a follower)", pos=(2900, 250))
g.wire(loop, "LoopBody", pBody, "execute", exec=True)
# DbgCount += 1
getCnt = g.var_get("DbgCount", "int", pos=(2900, 430))
addCnt = g.call("Add_IntInt", KML, pos=(3100, 430)); g.wire(getCnt, "DbgCount", addCnt, "A", exec=False)
g.typed_input(addCnt, "B", "1", "int")
setCnt = g.var_set("DbgCount", "int", pos=(3300, 250)); g.wire(addCnt, "ReturnValue", setCnt, "DbgCount", exec=False)
g.wire(pBody, "then", setCnt, "execute", exec=True)
# IsMountable (NOT IsMount): IsMount is mount-STATE (flips, true-for-all at mount time);
# IsMountable is the stable creature-type -> True for horses, False for humanoid thralls.
isMtbl = g.call("IsMountable", CONAN, pos=(3550, 700))
g.wire(loop, "Array Element", isMtbl, "self", exec=False)
bIsMtbl = g.branch(pos=(3550, 450))
g.wire(setCnt, "then", bIsMtbl, "execute", exec=True)
g.wire(isMtbl, "ReturnValue", bIsMtbl, "Condition", exec=False)
pStow = dbg("STOW A FOLLOWER", pos=(3800, 420))
g.wire(bIsMtbl, "else", pStow, "execute", exec=True)   # NOT mountable -> humanoid -> stow it
# at completion print the count (followers seen). LOOP COMPLETED firing at all = loop ran.
getCntF = g.var_get("DbgCount", "int", pos=(2900, 60))
pDone = dbg_int("=== LOOP COMPLETED, followers seen=", getCntF, "DbgCount", pos=(3150, 60))
g.wire(loop, "Completed", pDone, "execute", exec=True)

pDis = dbg("FOLLOWERS: DISMOUNT", pos=(1850, 950))
g.wire(bMounted, "else", pDis, "execute", exec=True)
# Seq2.1: update WasMounted = isMounted (every tick)
setWas = g.var_set("WasMounted", "bool", pos=(1350, 850))
g.wire(isValid, "ReturnValue", setWas, "WasMounted", exec=False)
g.wire(seq2, "then_1", setWas, "execute", exec=True)

text = g.render()
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))

# stamp the build version on the CDO so we can tell which class actually spawns
# (read instance.MgrVersion; ==2 -> the fixed class; 0/missing -> a cached old class)
gc = unreal.load_object(None, FULL + "_C")
if gc:
    unreal.get_default_object(gc).set_editor_property("MgrVersion", 4)
    unreal.EditorAssetLibrary.save_asset(PATH)
    print("CDO MgrVersion=4 stamped")
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
