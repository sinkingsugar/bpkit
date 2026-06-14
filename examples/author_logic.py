"""Example: author wired logic declaratively with bpkit.ir, inject + compile,
and read it back through the compactor.

    python ue_run.py examples/author_logic.py
"""
from bpkit import bridge as bp
from bpkit import compact as bc
from bpkit import ir

bp_obj, full = bp.scratch_blueprint(name="BP_AuthorDSL")
bp_ptr, graph_ptr = bp.find_graph(full, "EventGraph")

# describe the graph: BeginPlay -> PrintString("...")
g = ir.Graph()
ev = g.event("ReceiveBeginPlay")
pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary",
            inputs={"InString": "authored via bpkit.ir DSL"}, pos=(320, 0))
g.wire(ev, "then", pr, "execute")

text = g.render()
print("=== rendered import text ===")
print(text)

print("=== inject ->", bp.inject(full, text), "===")

rb = bp.export_nodes(bp.objects_with_outer(graph_ptr))
print("=== readback (compact) ===")
print(bc.compact_graph(bc.parse_nodes(rb), "EventGraph"))
