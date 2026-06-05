import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp

FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))

# print full node blocks for the nodes whose enum/name defaults matter
WANT = ("K2_AttachToComponent", "SetAnimationMode", "PlayAnimation")
cur = []
emit = False
for line in txt.splitlines():
    s = line.rstrip()
    if s.strip().startswith("Begin Object"):
        cur = [s]
        emit = any(w in s for w in WANT)  # header doesn't name fn; decide after FunctionReference
        continue
    cur.append(s)
    if "FunctionReference" in s:
        emit = any(w in s for w in WANT)
    if s.strip().startswith("End Object"):
        if emit:
            # only the first occurrence of each
            block = "\n".join(cur)
            fn = next((w for w in WANT if w in block), "?")
            print("\n##### %s #####" % fn)
            for b in cur:
                if b.strip().startswith("CustomProperties Pin") and "exec" not in b:
                    print(b.strip())
            WANT = tuple(w for w in WANT if w != fn)  # one each
        cur = []
        emit = False
    if not WANT:
        break
