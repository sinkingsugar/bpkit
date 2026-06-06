"""C2 Step A: BP_MountedFollowerManager : DreamworldMods.ModController, with a
BeginPlay that raises the player's 'Mount' follower-group cap. Smallest testable
slice of the manager. Run with Play STOPPED.
Run: python ue_run.py mods/mounted-followers/02a_manager_minimal.py
"""
import sys
# force re-import of our libs (the editor caches modules across ue_run calls, so
# edits to bpkit wouldn't otherwise be picked up)
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

# 1) fresh BP parented to ModController
if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    unreal.EditorAssetLibrary.delete_asset(PATH)
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.ModController)
print("manager BP:", FULL, "| parent:", bp_obj.get_editor_property("parent_class").get_name()
      if False else "ModController")

# 2) author BeginPlay -> GetPlayerCharacter -> cast ConanCharacter -> GetTSC -> AddAdjustment("Mount",5)
g = ir.Graph("EventGraph")
ev = g.event("ReceiveBeginPlay")
getP = g.call("GetPlayerCharacter", GS, pos=(300, 0))
g.typed_input(getP, "PlayerIndex", "0", "int")

cast = g.node("K2Node_DynamicCast",
              ['TargetType="/Script/CoreUObject.Class\'%s\'"' % CONAN], base="DynamicCast", pos=(600, 0))
g.wire(ev, "then", cast, "execute", exec=True)
g.wire(getP, "ReturnValue", cast, "Object", exec=False)

getTSC = g.call("GetThrallSystemComponent", CONAN, pos=(900, 150))
# DynamicCast output pin name is "As" + display name (UE inserts spaces): "AsConan Character"
g.wire(cast, "AsConan Character", getTSC, "self", exec=False)

addAdj = g.call("AddThrallGroupLimitAdjustment", TSC, pos=(1150, 0))
g.typed_input(addAdj, "Group", "Mount", "name")
g.typed_input(addAdj, "Amount", "5", "int")
g.wire(getTSC, "ReturnValue", addAdj, "self", exec=False)
g.wire(cast, "then", addAdj, "execute", exec=True)

text = g.render()

# 3) clear + inject + compile
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
print("cleared:", bp.clear_graph(bp_ptr, graph_ptr))
print("inject:", bp.inject(FULL, text, graph_name="EventGraph"))

# 4) orphan check + readback
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
orphans = re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("ORPHANS:", len(orphans), orphans if orphans else "(clean)")
print(bc.compact_graph(bc.parse_nodes(txt), "EventGraph"))
