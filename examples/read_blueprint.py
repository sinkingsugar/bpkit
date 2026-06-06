"""Example: read every graph of a blueprint to copy/paste node text.

    python ue_run.py examples/read_blueprint.py

Edit ASSET to point at your blueprint. The full node text is written to a
gitignored dump_*.txt at the repo root (it can be large). ue_run injects the
repo root onto the editor's sys.path, so no hardcoded path is needed here."""
import os
from bpkit import bridge as bp
from bpkit import config

# asset path from `/bp-read <asset>` (ue_run forwards it), else this default:
ASSET = (config.argv() or ["/Game/Sorcery/Glider/BP_BatDemonGlider"])[0]
FULL = ASSET + "." + ASSET.rsplit("/", 1)[1]
OUT = os.path.join(config.REPO_ROOT, "dump_%s.txt" % ASSET.rsplit("/", 1)[1])

graphs = bp.read_blueprint(FULL)
print("blueprint %s -> %d graph(s)" % (ASSET, len(graphs)))
for g in graphs:
    print("  graph[%d] nodes=%-4d chars=%d" % (g["index"], g["node_count"], len(g["text"])))

# newline="" so UE's own \r\n line endings pass through untouched; in Windows
# text mode they'd each become \r\r\n, which re-parses into junk blank lines.
with open(OUT, "w", encoding="utf-8", newline="") as f:
    for g in graphs:
        f.write("\n\n##### GRAPH[%d] nodes=%d #####\n%s"
                % (g["index"], g["node_count"], g["text"]))
print("total: %d nodes, %d chars -> %s"
      % (sum(g["node_count"] for g in graphs),
         sum(len(g["text"]) for g in graphs), OUT))
