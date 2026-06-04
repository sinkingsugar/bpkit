"""In-editor payload: validate the hand-built-TSet reader on a CONTROLLED graph
(BP_RoundTrip's single comment) before reading any real asset. Cross-checks that
GetObjectsWithOuter + make_tset + ExportNodesToText reproduces the known marker."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan\tools")
import importlib, ue_bp_inject as bpi
importlib.reload(bpi)

# BP_RoundTrip already holds a comment node with this marker (from verify_roundtrip).
bp, full = bpi.scratch_blueprint(name="BP_RoundTrip")
bp_ptr = bpi.find_object(full)
graph_ptr = bpi.find_object("EventGraph", outer=bp_ptr)
print("bp_ptr=%s graph_ptr=%s" % (hex(bp_ptr or 0), hex(graph_ptr or 0)))

# 1) enumerate the graph's node objects directly
nodes = bpi.objects_with_outer(graph_ptr, include_nested=False)
print("objects_with_outer(graph) -> %d node(s): %s" % (len(nodes), [hex(n) for n in nodes]))

# 2) hand-built TSet -> Export
text = bpi.export_pointers(nodes)
print("=== hand-built-TSet Export (%d chars) ===" % len(text))
print(text)
print("=== contains ROUNDTRIP-MARKER-7F3A? ->", "ROUNDTRIP-MARKER-7F3A" in text, "===")

# 3) also exercise GetAllGraphs on this blueprint
graphs = bpi.get_all_graphs(bp_ptr)
print("GetAllGraphs -> %d graph(s): %s" % (len(graphs), [hex(g) for g in graphs]))
