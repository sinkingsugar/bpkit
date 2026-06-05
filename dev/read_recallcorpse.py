"""Read BP_Ritual_RecallCorpse, dump full node text + print a compact navigable view."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import bp_compact as bc

ASSET = "/Game/Sorcery/Rituals/BP_Ritual_RecallCorpse"
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
OUT = r"C:\Users\sugar\devel\conan\dump_BP_Ritual_RecallCorpse.txt"

graphs = bp.read_blueprint(FULL)
print("blueprint %s -> %d graph(s)" % (ASSET, len(graphs)))
for g in graphs:
    print("  graph[%d] nodes=%-4d chars=%d" % (g["index"], g["node_count"], len(g["text"])))

with open(OUT, "w", encoding="utf-8", newline="") as f:
    for g in graphs:
        f.write("\n\n##### GRAPH[%d] nodes=%d #####\n%s"
                % (g["index"], g["node_count"], g["text"]))
print("dump -> %s" % OUT)

# compact view, printed straight back to the caller
alltext = "".join(g["text"] for g in graphs)
nodes = bc.parse_nodes(alltext)
print("\n=== SUMMARY ===")
print(bc.summary(nodes))
for gname in bc.graph_names(nodes):
    print(bc.compact_graph(nodes, gname))
