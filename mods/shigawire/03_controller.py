"""Shigawire build step 03 -- BP_ShigawireController : ModController.

Sole job (v1): register our two item rows by merging DT_SW_Items into the game's
/Game/Items/ItemTable. MergeDataTables is BlueprintProtected and resolves ONLY inside
the ModController `ModDataTableOperations` override (verified for mounted-followers:
it silently drops in the event graph). The base ModController calls
ModDataTableOperations at mod-init on every instance, which is exactly when/where the
rows must register. (The pull/CC/cable gameplay lives in BP_SW_HookProjectile, step 04.)

Idempotent (scratch_blueprint clears+reinjects). Run with Play STOPPED.
    python ue_run.py mods/shigawire/03_controller.py
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

PKG, NAME = MOD.OUTPUT_PKG, MOD.CONTROLLER
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME
DTAB = "/Script/Engine.DataTable"
MODCTRL = unreal.ModController.static_class().get_path_name()
OURS_OBJ = MOD.full(MOD.ITEMS_DT)                                  # DT_SW_Items object path
_git = MOD.GAME_ITEM_TABLE
GAME_OBJ = "%s.%s" % (_git, _git.rsplit("/", 1)[1])               # /Game/Items/ItemTable.ItemTable

# create-or-reset the ModController BP
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("controller BP:", FULL)

# ModDataTableOperations override: MergeDataTables(MergeInto=game ItemTable, ToBeAdded=DT_SW_Items)
OPFN = "ModDataTableOperations"
op_bp_ptr, op_gptr = bp.create_function_override(bp_obj, OPFN, MODCTRL)
og = ir.Graph(OPFN)
opMerge = og.node("K2Node_CallFunction",
                  ['FunctionReference=(MemberName="MergeDataTables",bSelfContext=True)'],
                  base="CallFunction", pos=(560, 0))
# self-context VariableGets drop on paste into an override graph -> feed both tables as
# resolved DefaultObject refs (quoted object path = the editor's canonical resolved form).
mi = opMerge.pin("MergeIntoDataTable"); mi.dir = "EGPD_Input"
mi.set("PinType.PinCategory", '"object"'); mi.set("PinType.PinSubCategoryObject", ir.obj_path(DTAB))
mi.set("DefaultObject", '"%s"' % GAME_OBJ)     # game's ItemTable
ta = opMerge.pin("ToBeAddedDataTable"); ta.dir = "EGPD_Input"
ta.set("PinType.PinCategory", '"object"'); ta.set("PinType.PinSubCategoryObject", ir.obj_path(DTAB))
ta.set("DefaultObject", '"%s"' % OURS_OBJ)     # our DT_SW_Items
op_text = og.render(); op_auth = op_text.count("Begin Object Class=")
op_res = bp.inject(FULL, op_text, graph_name=OPFN, compile=False, save=False)
op_drop = op_auth - (op_res.get("pasted") or 0)
print("override inject:", op_res, "authored:", op_auth, ("DROPPED %d" % op_drop) if op_drop else "")

# live-wire: function entry 'then' exec -> MergeDataTables 'execute' (cross-set; paste won't link it)
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

bp.mark_structurally_modified(op_bp_ptr)
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
unreal.EditorAssetLibrary.save_asset(PATH)

# verify
op_txt = bp.export_nodes(bp.graph_nodes(op_gptr))
op_orph = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', op_txt)
op_defs = re.findall(r'DefaultObject=([^,)\s]+)', op_txt)
print("override: MergeDataTables present:", 'MemberName="MergeDataTables"' in op_txt,
      "| table defaults:", op_defs, "| orphans:", op_orph if op_orph else "(clean)")
print("03 OK" if 'MemberName="MergeDataTables"' in op_txt and not op_orph else "03 ISSUE")
