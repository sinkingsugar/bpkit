"""C6b -- BP_MF_HorsesCommand: a UDataActorCommand subclass implementing DoCommand,
the handler for `dc MFHorses <N>` (registered via DT_MF_Commands, see 05). Runs
SERVER-side (the row sets run_on_server). On each invocation it:
  1. parses N from Parameters[0] (clamped 0..MOUNT_LIMIT_MAX),
  2. SETS every player's Mount cap live (reset+add -> applies this tick, no restart),
  3. persists N to the BP_MF_SaveGame slot (survives server restarts),
  4. confirms to the calling admin via a client message box.

Authored with the bpkit library: ir.Graph builders (cast/get_all_actors/array_*/
var_set) + build.build_graph (inject -> auto-relink dropped wires -> compile ->
scan). Run with Play STOPPED:  python ue_run.py mods/mounted-followers/04_command.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal, os
from bpkit import bridge as bp, ir, build, config as _cfg
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
ACTOR = "/Script/Engine.Actor"
PAWN  = "/Script/Engine.Pawn"
SG_CLS_PATH = "%s/%s.%s_C" % (PKG, MOD.SAVEGAME, MOD.SAVEGAME)

bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.DataActorCommand)
print("command BP:", FULL)

g = ir.Graph("EventGraph")

# ================= DoCommand graph =================
ev = g.event("DoCommand", parent=DAC, pos=(0, 0))

# guard: Parameters has >= 1 element (a bare invocation with no tokens -> skip, no message)
lenP = g.array_len(ev, "Parameters", (300, 250), elem_cat="string")
gt = g.call("Greater_IntInt", KML, pos=(550, 250))
g.wire(lenP, "ReturnValue", gt, "A", exec=False)
g.typed_input(gt, "B", "0", "int")
bHas = g.branch(pos=(550, 0))
g.wire(ev, "then", bHas, "execute", exec=True)
g.wire(gt, "ReturnValue", bHas, "Condition", exec=False)

# parse + clamp N. Parameters[0] is the first arg AFTER the command name (Funcom: the name is
# NOT included), so `dc MFHorses 5` -> Parameters == ["5"]. (The v39 "always set to 0" bug was
# the GetItem.Output -> Conv_StringToInt.InString wire dropping on paste -- a wildcard-Output
# drop that inject() now AUTO-RELINKS; see ir.array_get / bridge.missing_links.)
item = g.array_get(ev, "Parameters", 0, (300, 450), elem_cat="string")
toInt = g.call("Conv_StringToInt", KSTR, pos=(800, 450))
g.wire(item, "Output", toInt, "InString", exec=False)
flo = g.call("Max", KML, pos=(1000, 450))   # KismetMathLibrary int Max (BP name "Max")
g.wire(toInt, "ReturnValue", flo, "A", exec=False); g.typed_input(flo, "B", "0", "int")
cap = g.call("Min", KML, pos=(1200, 450))    # int Min -> clamp to [0, MOUNT_LIMIT_MAX]
g.wire(flo, "ReturnValue", cap, "A", exec=False)
g.typed_input(cap, "B", str(MOD.MOUNT_LIMIT_MAX), "int")
CAP = (cap, "ReturnValue")   # the clamped target N

# apply to every player's Mount cap (SET = reset + add), server-side
ga = g.get_all_actors(CONAN, (800, 0))
g.wire(bHas, "then", ga, "execute", exec=True)
loop = g.foreach(ACTOR, pos=(1050, 0))
g.wire(ga, "OutActors", loop, "Array", exec=False)
g.wire(ga, "then", loop, "Exec", exec=True)
castP = g.cast(CONAN, (1300, 0))
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
cp.set("PinType.PinCategory", '"class"')
cp.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/Engine.SaveGame"))
cp.set("PinType.bIsUObjectWrapper", "True"); cp.set("DefaultObject", '"%s"' % SG_CLS_PATH)
# CreateSaveGameObject auto-narrows ReturnValue to the class we pass (BP_MF_SaveGame),
# so NO cast needed -- wire it straight into the cross-instance set.
rp = crt.pin("ReturnValue"); rp.dir = "EGPD_Output"
rp.set("PinType.PinCategory", '"object"'); rp.set("PinType.PinSubCategoryObject", ir.obj_path(SG_CLS_PATH))
g.wire(loop, "Completed", crt, "execute", exec=True)
xs = g.var_set("MountLimit", "int", pos=(1650, 700), parent=SG_CLS_PATH)   # cross-instance set
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

# ---- build + verify (inject auto-relinks the GetItem.Output->Conv.InString drop) ----
build.build_graph(FULL, g)
