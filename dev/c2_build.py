"""C2 manager build (evolving). BP_MountedFollowerManager : ModController.
Step A+ : ReceiveTick raises the player's 'Mount' cap ONCE (guarded by an
'Initialized' bool), since the framework auto-spawns the ModController before the
player exists (BeginPlay was too early). Run with Play STOPPED.
Run: python ue_run.py dev/c2_build.py
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

if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    unreal.EditorAssetLibrary.delete_asset(PATH)
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL)

# member var: Initialized (bool)
boolt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("bool")
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "Initialized", boolt)

g = ir.Graph("EventGraph")
tick = g.event("ReceiveTick")
getInit = g.var_get("Initialized", "bool", pos=(250, 200))
branch = g.branch(pos=(500, 0))
g.wire(tick, "then", branch, "execute", exec=True)
g.wire(getInit, "Initialized", branch, "Condition", exec=False)

# False (not initialized yet) -> try to raise the cap
getP = g.call("GetPlayerCharacter", GS, pos=(500, 300))
g.typed_input(getP, "PlayerIndex", "0", "int")
cast = g.node("K2Node_DynamicCast",
              ['TargetType="/Script/CoreUObject.Class\'%s\'"' % CONAN], base="DynamicCast", pos=(800, 0))
g.wire(branch, "Else", cast, "execute", exec=True)        # False exec out
g.wire(getP, "ReturnValue", cast, "Object", exec=False)
getTSC = g.call("GetThrallSystemComponent", CONAN, pos=(1100, 250))
g.wire(cast, "AsConan Character", getTSC, "self", exec=False)
addAdj = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(1350, 0))
g.typed_input(addAdj, "Group", "Mount", "name")
g.typed_input(addAdj, "Amount", "5", "int")
g.wire(getTSC, "ReturnValue", addAdj, "self", exec=False)
g.wire(cast, "then", addAdj, "execute", exec=True)        # cast success
setInit = g.var_set("Initialized", "bool", pos=(1650, 0))
setInit.pin("Initialized").literal("true")
g.wire(addAdj, "then", setInit, "execute", exec=True)

text = g.render()
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("ORPHANS:", len(orphans), orphans if orphans else "(clean)")
print(bc.compact_graph(bc.parse_nodes(txt), "EventGraph"))
