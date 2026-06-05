import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
for ASSET in ["/Game/Characters/MountFunctionLibrary"]:
    FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
    OUT = r"C:\Users\sugar\devel\conan\dump_%s.txt" % ASSET.rsplit("/", 1)[1]
    graphs = bp.read_blueprint(FULL)
    print("blueprint %s -> %d graph(s)" % (ASSET, len(graphs)))
    for g in graphs:
        print("  graph[%d] nodes=%-4d chars=%d" % (g["index"], g["node_count"], len(g["text"])))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        for g in graphs:
            f.write("\n\n##### GRAPH[%d] nodes=%d #####\n%s" % (g["index"], g["node_count"], g["text"]))
    print("-> ", OUT)
