import sys, re
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
sys.modules.pop("bp_bridge", None)
import unreal
import bp_bridge as bp
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["Blueprint"], recursive_classes=True)
a = [a for a in ar.get_assets(far) if str(a.asset_name) == "BPEmoteController"][0]
path = "%s.%s" % (str(a.package_name), str(a.asset_name))
unreal.EditorAssetLibrary.load_asset(str(a.package_name))
graphs = bp.read_blueprint(path)
print("graphs:", len(graphs))
# custom events (RPCs) across all graphs -- name + any net flags in the node text
for g in graphs:
    txt = g["text"]
    for m in re.finditer(r'Begin Object Class=/Script/BlueprintGraph\.K2Node_CustomEvent.*?CustomFunctionName="([^"]+)"', txt, re.S):
        # grab the flags blob near this node
        seg = txt[m.start():m.start()+600]
        flags = re.search(r'FunctionFlags=(\d+)', seg)
        netf = [k for k in ("Multicast","NetMulticast","NetReliable","BlueprintAuthorityOnly","Net ") if k in seg]
        print("CustomEvent: %-32s flags=%s hints=%s" % (m.group(1), flags.group(1) if flags else "?", netf))
    # function-call nodes that mention emote/multicast/server
    for m in re.finditer(r'MemberName="([^"]*(?:[Mm]ulticast|[Ss]erver|[Ee]mote)[^"]*)"', txt):
        pass
# also: which member functions exist (graph identities) -- print first node class per graph
print("\n-- function-entry names --")
for i, g in enumerate(graphs):
    fe = re.search(r'K2Node_FunctionEntry.*?FunctionReference=\(MemberName="([^"]+)"', g["text"], re.S)
    if fe: print("  graph[%d]: %s" % (i, fe.group(1)))
