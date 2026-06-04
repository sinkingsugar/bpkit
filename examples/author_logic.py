"""Example: author wired logic declaratively with bp_author, inject + compile,
and read it back through the compactor.

    python ue_run.py examples/author_logic.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import bp_compact as bc
from bp_author import Graph

bp_obj, full = bp.scratch_blueprint(name="BP_AuthorDSL")
bp_ptr, graph_ptr = bp.find_graph(full, "EventGraph")

# describe the graph: BeginPlay -> PrintString("...")
g = Graph()
ev = g.event("ReceiveBeginPlay")
pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary",
            inputs={"InString": "authored via bp_author DSL"}, pos=(320, 0))
g.wire(ev, "then", pr, "execute")

text = g.render()
print("=== rendered import text ===")
print(text)

print("=== inject ->", bp.inject(full, text), "===")

rb = bp.export_nodes(bp.objects_with_outer(graph_ptr))
print("=== readback (compact) ===")
print(bc.compact_graph(bc.parse_nodes(rb), "EventGraph"))
