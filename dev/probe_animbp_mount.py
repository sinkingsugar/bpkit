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
terms = re.compile(r"mount|horse|saddle|\brider\b|riding", re.I)
hits = 0
for i, g in enumerate(graphs):
    try:
        txt = bp.export_nodes(bp.graph_nodes(g))
    except Exception as e:
        continue
    lines = [ln.strip() for ln in txt.splitlines() if terms.search(ln)]
    # collapse to the informative lines: node class, MemberName, state/var names
    info = [ln[:150] for ln in lines if any(k in ln for k in
            ("MemberName", "Begin Object", "NodeComment", "BoundGraph", "StateMachine",
             "FunctionReference", "VariableReference", "Name=", "PinName"))]
    if info:
        hits += 1
        print("=== graph[%d] nodes=%d (%d mount-lines) ===" % (i, len(bp.graph_nodes(g)), len(lines)))
        for ln in info[:10]:
            print("   ", ln)
print("graphs with mount refs:", hits)
