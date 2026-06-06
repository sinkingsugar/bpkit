import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_bridge",):
    sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp

# 1) locate the AnimBP asset
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["AnimBlueprint"], recursive_classes=True)
assets = ar.get_assets(far)
matches = [a for a in assets if "AB_Master_HumanNPC_male" in str(a.asset_name)]
print("matches:", [str(a.asset_name) for a in matches][:5])
if matches:
    a = matches[0]
    path = "%s.%s" % (str(a.package_name), str(a.asset_name))
    print("PATH:", path)
    # 2) enumerate graphs + node counts (NO text export -- just gauge structure)
    unreal.EditorAssetLibrary.load_asset(str(a.package_name))
    bpobj = bp.find_object(path)
    print("bp ptr:", hex(bpobj) if bpobj else None)
    if bpobj:
        graphs = bp.get_all_graphs(bpobj)
        print("graph count:", len(graphs))
        total = 0
        for i, g in enumerate(graphs):
            n = len(bp.graph_nodes(g))
            total += n
            print("  graph[%d] ptr=%s nodes=%d" % (i, hex(g), n))
        print("total nodes:", total)
