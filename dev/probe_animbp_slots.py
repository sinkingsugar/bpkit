import sys, re
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
sys.modules.pop("bp_bridge", None)
import unreal
import bp_bridge as bp
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["AnimBlueprint"], recursive_classes=True)
a = [a for a in ar.get_assets(far) if "AB_Master_HumanNPC_male" in str(a.asset_name)][0]
path = "%s.%s" % (str(a.package_name), str(a.asset_name))
unreal.EditorAssetLibrary.load_asset(str(a.package_name))
bpobj = bp.find_object(path)
graphs = bp.get_all_graphs(bpobj)
for i, g in enumerate(graphs):
    try: txt = bp.export_nodes(bp.graph_nodes(g))
    except Exception: continue
    # AnimGraphNode_Slot nodes carry SlotName; also note Root/Output pose nodes
    slots = re.findall(r'SlotName="?([A-Za-z0-9_ ]+)"?', txt)
    has_root = "AnimGraphNode_Root" in txt or "Output Pose" in txt or "AnimGraphNode_StateResult" in txt
    if slots:
        print("graph[%d] nodes=%d root_output=%s SLOTS=%s" % (i, len(bp.graph_nodes(g)), has_root, list(dict.fromkeys(slots))))
