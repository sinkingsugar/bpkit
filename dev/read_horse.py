import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
for ASSET in ["/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse",
              "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Wildlife_Hooved"]:
    FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
    OUT = r"C:\Users\sugar\devel\conan\dump_%s.txt" % ASSET.rsplit("/", 1)[1]
    try:
        graphs = bp.read_blueprint(FULL)
    except Exception as e:
        print("ERR", ASSET, e); continue
    print("%s -> %d graphs, %d nodes" % (ASSET.rsplit('/',1)[1], len(graphs), sum(g['node_count'] for g in graphs)))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        for g in graphs:
            f.write("\n\n##### GRAPH[%d] nodes=%d #####\n%s" % (g["index"], g["node_count"], g["text"]))
