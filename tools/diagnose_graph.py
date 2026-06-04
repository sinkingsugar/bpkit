"""In-editor payload: localize export faults in specific graphs of the real BP.
For each suspect graph, export every node individually (trivial 1-word inline set)
to separate node-content faults from bit-array-at-scale faults."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)
import unreal

ASSET = "/Game/Sorcery/Glider/BP_BatDemonGlider"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
unreal.EditorAssetLibrary.load_asset(ASSET)
bp = bpi.find_object(FULL)
graphs = bpi.get_all_graphs(bp)

for gi in (5, 12):
    g = graphs[gi]
    nodes = bpi.objects_with_outer(g, include_nested=False)
    print("=== graph[%d] ptr=%s : %d nodes ===" % (gi, hex(g), len(nodes)))
    bad = []
    for i, n in enumerate(nodes):
        try:
            bpi.export_pointers([n])
        except OSError:
            bad.append(i)
    print("  per-node export faults: %d / %d  indices=%s"
          % (len(bad), len(nodes), bad[:30]))
    # try increasing prefixes to find the count threshold where it breaks
    thresh = None
    for k in (16, 32, 64, 96, 128, 160, 256, len(nodes)):
        if k > len(nodes):
            continue
        try:
            bpi.export_pointers(nodes[:k])
            ok = True
        except OSError:
            ok = False
        print("  prefix[:%d] -> %s" % (k, "OK" if ok else "FAULT"))
        if not ok and thresh is None:
            thresh = k
    print("  first faulting prefix size:", thresh)
