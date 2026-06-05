import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import bp_compact as bc

ASSET = "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_NecromancyZombie_Main"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
OUT = r"C:\Users\sugar\devel\conan\dump_BP_NecromancyZombie_Main.txt"

graphs = bp.read_blueprint(FULL)
with open(OUT, "w", encoding="utf-8", newline="") as f:
    for g in graphs:
        f.write("\n\n##### GRAPH[%d] nodes=%d #####\n%s"
                % (g["index"], g["node_count"], g["text"]))

alltext = "".join(g["text"] for g in graphs)
nodes = bc.parse_nodes(alltext)
print(bc.summary(nodes))

# print graphs whose nodes mention variation/female/random/gender selection
import re
KEY = re.compile(r"Variation|IsFemale|Female|Random|Gender|SelectVariation|Mesh", re.I)
for gname in bc.graph_names(nodes):
    block = bc.compact_graph(nodes, gname)
    if KEY.search(block):
        print("\n########## GRAPH %s ##########" % gname)
        print(block)
