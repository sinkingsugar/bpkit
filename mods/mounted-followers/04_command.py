"""C6b -- BP_MF_HorsesCommand: a UDataActorCommand subclass implementing DoCommand,
the handler for `dc MFHorses <N>` (registered via DT_MF_Commands, see 05). Runs
SERVER-side (the row sets run_on_server). On each invocation it:
  1. parses N from Parameters[0] (clamped 0..MOUNT_LIMIT_MAX),
  2. SETS every player's Mount cap live (reset+add -> applies this tick, no restart),
  3. persists N to the BP_MF_SaveGame slot (survives server restarts),
  4. confirms to the calling admin via a client message box.

Run with Play STOPPED:  python ue_run.py mods/mounted-followers/04_command.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal, os, re
from bpkit import bridge as bp, ir, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "mounted-followers"))
sys.modules.pop("mf_config", None)
import mf_config as MOD

PKG, NAME = MOD.OUTPUT_PKG, MOD.COMMAND
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME

DAC   = "/Script/ConanSandbox.DataActorCommand"
CONAN = "/Script/ConanSandbox.ConanCharacter"
CPC   = "/Script/ConanSandbox.ConanPlayerController"
TSC   = "/Script/ConanSandbox.ThrallSystemComponent"
GS    = "/Script/Engine.GameplayStatics"
KML   = "/Script/Engine.KismetMathLibrary"
KSTR  = "/Script/Engine.KismetStringLibrary"
KTL   = "/Script/Engine.KismetTextLibrary"
KARR  = "/Script/Engine.KismetArrayLibrary"
ACTOR = "/Script/Engine.Actor"
PAWN  = "/Script/Engine.Pawn"
SG_CLS_PATH = "%s/%s.%s_C" % (PKG, MOD.SAVEGAME, MOD.SAVEGAME)

bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.DataActorCommand)
print("command BP:", FULL)

g = ir.Graph("EventGraph")

# ---- helpers (the proven manager patterns) ----
def cast_node(target, pos):
    return g.node("K2Node_DynamicCast", ['TargetType="%s"' % ir.obj_path(target)],
                  base="DynamicCast", pos=pos)

def get_all_actors(cls_path, pos):
    n = g.call("GetAllActorsOfClass", GS, pos=pos)
    ap = n.pin("ActorClass"); ap.dir = "EGPD_Input"
    ap.set("PinType.PinCategory", '"class"')
    ap.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/Engine.Actor"))
    ap.set("PinType.bIsUObjectWrapper", "True"); ap.set("DefaultObject", '"%s"' % cls_path)
    op = n.pin("OutActors"); op.dir = "EGPD_Output"
    op.set("PinType.PinCategory", '"object"')
    op.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/Engine.Actor"))
    op.set("PinType.ContainerType", "Array")
    return n

def arr_len_str(arr_node, arr_pin, pos):
    n = g.node("K2Node_CallArrayFunction",
        ['FunctionReference=(MemberParent="%s",MemberName="Array_Length")' % ir.obj_path(KARR)],
        base="ArrFn", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"
    sp.set("PinType.PinCategory", '"object"'); sp.set("PinType.PinSubCategoryObject", ir.obj_path(KARR))
    sp.set("DefaultObject", "/Script/Engine.Default__KismetArrayLibrary"); sp.set("bHidden", "True")
    tp = n.pin("TargetArray"); tp.dir = "EGPD_Input"
    tp.set("PinType.PinCategory", '"string"'); tp.set("PinType.ContainerType", "Array")
    tp.set("PinType.bIsReference", "True"); tp.set("PinType.bIsConst", "True")
    tp.set("bDefaultValueIsIgnored", "True")
    rp = n.pin("ReturnValue"); rp.dir = "EGPD_Output"; rp.set("PinType.PinCategory", '"int"')
    g.wire(arr_node, arr_pin, n, "TargetArray", exec=False)
    return n

def get_item_str(arr_node, arr_pin, idx, pos):
    n = g.node("K2Node_GetArrayItem", ["bReturnByRefDesired=False"], base="GetItem", pos=pos)
    ap = n.pin("Array"); ap.dir = "EGPD_Input"
    ap.set("PinType.PinCategory", '"string"'); ap.set("PinType.ContainerType", "Array")
    ip = n.pin("Dimension 1"); ip.dir = "EGPD_Input"
    ip.set("PinType.PinCategory", '"int"'); ip.set("DefaultValue", '"%d"' % idx)
    op = n.pin("Output"); op.dir = "EGPD_Output"; op.set("PinType.PinCategory", '"string"')
    g.wire(arr_node, arr_pin, n, "Array", exec=False)
    return n

def xset_int(name, cls_path, pos):
    """cross-instance VariableSet of an int member `name` on a `cls_path` instance
    (wire target into 'self', value into `name`). Validated 2026-06-13."""
    n = g.node("K2Node_VariableSet",
        ['VariableReference=(MemberName="%s",MemberParent="%s",bSelfContext=False)'
         % (name, ir.obj_path(cls_path))], base="VariableSet", pos=pos)
    sp = n.pin("self"); sp.dir = "EGPD_Input"
    sp.set("PinType.PinCategory", '"object"'); sp.set("PinType.PinSubCategoryObject", ir.obj_path(cls_path))
    vp = n.pin(name); vp.dir = "EGPD_Input"; vp.set("PinType.PinCategory", '"int"')
    return n

# ================= DoCommand graph =================
ev = g.event("DoCommand", parent=DAC, pos=(0, 0))

# guard: Parameters has >= 1 element (else a bare `dc MFHorses` would parse "" -> 0)
lenP = arr_len_str(ev, "Parameters", (300, 250))
gt = g.call("Greater_IntInt", KML, pos=(550, 250))
g.wire(lenP, "ReturnValue", gt, "A", exec=False)
g.typed_input(gt, "B", "0", "int")
bHas = g.branch(pos=(550, 0))
g.wire(ev, "then", bHas, "execute", exec=True)
g.wire(gt, "ReturnValue", bHas, "Condition", exec=False)

# parse + clamp N
item = get_item_str(ev, "Parameters", 0, (300, 450))
toInt = g.call("Conv_StringToInt", KSTR, pos=(800, 450))
g.wire(item, "Output", toInt, "InString", exec=False)
flo = g.call("Max", KML, pos=(1000, 450))   # KismetMathLibrary int Max (BP name "Max")
g.wire(toInt, "ReturnValue", flo, "A", exec=False); g.typed_input(flo, "B", "0", "int")
cap = g.call("Min", KML, pos=(1200, 450))    # int Min -> clamp to [0, MOUNT_LIMIT_MAX]
g.wire(flo, "ReturnValue", cap, "A", exec=False)
g.typed_input(cap, "B", str(MOD.MOUNT_LIMIT_MAX), "int")
CAP = (cap, "ReturnValue")   # the clamped target N

# apply to every player's Mount cap (SET = reset + add), server-side
ga = get_all_actors(CONAN, (800, 0))
g.wire(bHas, "then", ga, "execute", exec=True)
loop = g.foreach(ACTOR, pos=(1050, 0))
g.wire(ga, "OutActors", loop, "Array", exec=False)
g.wire(ga, "then", loop, "Exec", exec=True)
castP = cast_node(CONAN, (1300, 0))
g.wire(loop, "Array Element", castP, "Object", exec=False)
g.wire(loop, "LoopBody", castP, "execute", exec=True)
isPl = g.call("IsPlayerControlled", PAWN, pos=(1550, 250))
g.wire(castP, "AsConan Character", isPl, "self", exec=False)
bPl = g.branch(pos=(1550, 0))
g.wire(castP, "then", bPl, "execute", exec=True)
g.wire(isPl, "ReturnValue", bPl, "Condition", exec=False)
getTSC = g.call("GetThrallSystemComponent", CONAN, pos=(1800, 250))
g.wire(castP, "AsConan Character", getTSC, "self", exec=False)
rst = g.call("ResetThrallGroupLimitAdjustment", TSC, pos=(1800, 0))
g.typed_input(rst, "Group", "Mount", "name")
g.wire(getTSC, "ReturnValue", rst, "self", exec=False)
g.wire(bPl, "then", rst, "execute", exec=True)
addc = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(2050, 0))
g.typed_input(addc, "Group", "Mount", "name")
g.wire(CAP[0], CAP[1], addc, "Amount", exec=False)
g.wire(getTSC, "ReturnValue", addc, "self", exec=False)
g.wire(rst, "then", addc, "execute", exec=True)

# persist N to the SaveGame slot (after the loop)
crt = g.call("CreateSaveGameObject", GS, pos=(1050, 700))
cp = crt.pin("SaveGameClass"); cp.dir = "EGPD_Input"
cp.set("PinType.PinCategory", '"class"'); cp.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/Engine.SaveGame"))
cp.set("PinType.bIsUObjectWrapper", "True"); cp.set("DefaultObject", '"%s"' % SG_CLS_PATH)
# CreateSaveGameObject auto-narrows ReturnValue to the class we pass (BP_MF_SaveGame),
# so NO cast needed -- wire it straight into the cross-instance set (cast was redundant
# -> compiler error "'ReturnValue' is already a BP MF Save Game").
rp = crt.pin("ReturnValue"); rp.dir = "EGPD_Output"
rp.set("PinType.PinCategory", '"object"'); rp.set("PinType.PinSubCategoryObject", ir.obj_path(SG_CLS_PATH))
g.wire(loop, "Completed", crt, "execute", exec=True)
xs = xset_int("MountLimit", SG_CLS_PATH, (1650, 700))
g.wire(crt, "ReturnValue", xs, "self", exec=False)
g.wire(CAP[0], CAP[1], xs, "MountLimit", exec=False)
g.wire(crt, "then", xs, "execute", exec=True)
sav = g.call("SaveGameToSlot", GS, pos=(1950, 700))
g.typed_input(sav, "SlotName", MOD.SAVE_SLOT, "string")
g.typed_input(sav, "UserIndex", "0", "int")
g.wire(crt, "ReturnValue", sav, "SaveGameObject", exec=False)
g.wire(xs, "then", sav, "execute", exec=True)

# confirm to the calling admin (client message box; runs on their client via the Client RPC)
i2s = g.call("Conv_IntToString", KSTR, pos=(1650, 950))
g.wire(CAP[0], CAP[1], i2s, "InInt", exec=False)
cc = g.call("Concat_StrStr", KSTR, pos=(1850, 950))
g.typed_input(cc, "A", "Mounted Followers: Mount follower limit set to ", "string")
g.wire(i2s, "ReturnValue", cc, "B", exec=False)
t2t = g.call("Conv_StringToText", KTL, pos=(2050, 950))
g.wire(cc, "ReturnValue", t2t, "InString", exec=False)
show = g.call("ClientShowMessageBox", CPC, pos=(2250, 700))
g.wire(ev, "CallingPlayerController", show, "self", exec=False)
g.wire(t2t, "ReturnValue", show, "Title", exec=False)
g.wire(t2t, "ReturnValue", show, "Message", exec=False)
g.wire(sav, "then", show, "execute", exec=True)

# ---- inject + verify ----
text = g.render()
n_authored = text.count("Begin Object Class=")
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
res = bp.inject(FULL, text, graph_name="EventGraph")
print("inject:", res)
dropped = n_authored - (res.get("pasted") or 0)
if dropped:
    print("!! PASTE DROPPED %d NODE(S): authored %d, pasted %d" % (dropped, n_authored, res.get("pasted")))

txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("ORPHANS:", len(orphans), orphans if orphans else "(clean)")
problems = []
for blk in re.split(r'(?=Begin Object Class=)', txt):
    if not blk.strip():
        continue
    nm = (re.search(r'Name="([^"]+)"', blk) or [None, "?"])[1]
    is_macro = "K2Node_MacroInstance" in blk
    for pin in re.findall(r'CustomProperties Pin \((.*)\)', blk):
        if 'PinCategory="wildcard"' in pin and not is_macro:
            pn = (re.search(r'PinName="([^"]+)"', pin) or [None, "?"])[1]
            problems.append("WILDCARD %s.%s" % (nm, pn))
    if "ErrorMsg=" in blk or 'bHasCompilerMessage=True' in blk:
        problems.append("ERROR node %s" % nm)
# confirm the cross-instance set's self pin actually linked to the cast output
xset_blk = [b for b in re.split(r'(?=Begin Object Class=)', txt) if "K2Node_VariableSet" in b]
for b in xset_blk:
    selfpin = re.search(r'PinName="self"[^\n]*?(LinkedTo=\([^)]*\))?', b)
    print("xset self linked:", "LinkedTo" in (selfpin.group(0) if selfpin else ""))
print("COMPILE PROBLEMS:", len(problems), problems)
print("BUILD OK" if not problems and not orphans and not dropped else "BUILD HAS ISSUES")
