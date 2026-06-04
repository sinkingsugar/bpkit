"""In-editor payload: SAFE full read of the real blueprint using per-node
(set-of-1) export. Writes the complete dump to disk with a summary."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)
import unreal

ASSET = "/Game/Sorcery/Glider/BP_BatDemonGlider"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
OUT = r"C:\Users\sugar\devel\conan\tools\dump_BatDemonGlider.txt"

unreal.EditorAssetLibrary.load_asset(ASSET)
bp = bpi.find_object(FULL)
graphs = bpi.get_all_graphs(bp)
print("GetAllGraphs -> %d graph(s)" % len(graphs))

chunks = []
total_nodes = 0
for i, g in enumerate(graphs):
    nodes = bpi.objects_with_outer(g, include_nested=False)
    text = bpi.export_pointers_individually(nodes)
    total_nodes += len(nodes)
    print("  graph[%d] nodes=%-4d chars=%d" % (i, len(nodes), len(text)))
    chunks.append("\n\n##### GRAPH[%d] ptr=%s nodes=%d #####\n%s"
                  % (i, hex(g), len(nodes), text))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("".join(chunks))
print("wrote %s : %d graphs, %d nodes, %d chars"
      % (OUT, len(graphs), total_nodes, sum(len(c) for c in chunks)))
