"""In-editor payload: validate graph_nodes (UEdGraph::Nodes reader) against
objects_with_outer on a freshly-loaded BP (no edits -> no orphans -> identical
sets). Pure pointer comparison; nothing exported, so a wrong offset can't crash."""
import sys, importlib
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge
importlib.reload(bp_bridge)
bp = bp_bridge
import unreal

ASSET = "/Game/Sorcery/Glider/BP_BatDemonGlider"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
unreal.EditorAssetLibrary.load_asset(ASSET)
graphs = bp.get_all_graphs(bp.find_object(FULL))

print("discovered Nodes offset:", hex(bp._find_nodes_offset(graphs[0]) or 0))
allmatch = True
for i, g in enumerate(graphs):
    owo = set(bp.objects_with_outer(g))
    gn = set(bp.graph_nodes(g))
    same = owo == gn
    allmatch &= same
    print("graph[%2d] objects_with_outer=%3d  graph_nodes=%3d  %s"
          % (i, len(owo), len(gn), "OK" if same else "MISMATCH"))
print("\nALL MATCH:", allmatch)
