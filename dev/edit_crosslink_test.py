"""In-editor payload: does a FRESHLY IMPORTED node resolve a LinkedTo that points
at a PRE-EXISTING node already in the graph? Determines whether in-place editing
(add a node + wire it into existing logic) works via additive import alone."""
import sys, re
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import bp_bridge as bp
import bp_compact as bc
from bp_author import Graph

bp_obj, full = bp.scratch_blueprint(name="BP_Edit")
bp_ptr, graph = bp.find_graph(full, "EventGraph")

# --- step 1: import node A (a CustomEvent) on its own ---
g1 = Graph()
g1.custom_event("Trigger")
bp.inject(full, g1.render(), compile=False, save=False)

# read back, find A's actual name + its 'then' (exec out) pin id from the raw text
text = bp.export_nodes(bp.objects_with_outer(graph))
a_name, a_then = None, None
for blk in re.findall(r"Begin Object.*?End Object", text, re.S):
    if 'CustomFunctionName="Trigger"' in blk:
        a_name = re.search(r'Name="([^"]+)"', blk).group(1)
        m = re.search(r'PinId=([0-9A-F]{32}),PinName="then"', blk)
        a_then = m.group(1) if m else None
print("existing node A: name=%s then_pin=%s" % (a_name, a_then))

# --- step 2: import node B (PrintString) whose execute LinkedTo points at A ---
B = (
    'Begin Object Class=/Script/BlueprintGraph.K2Node_CallFunction Name="K2Node_CallFunction_X"\n'
    '   FunctionReference=(MemberParent="/Script/CoreUObject.Class\'/Script/Engine.KismetSystemLibrary\'",MemberName="PrintString")\n'
    '   NodePosX=400\n   NodeGuid=%s\n'
    '   CustomProperties Pin (PinId=%s,PinName="execute",Direction="EGPD_Input",'
    'PinType.PinCategory="exec",LinkedTo=(%s %s,))\n'
    'End Object\n' % (bp.__dict__.get("_x", "11AABB22CC33DD44EE55FF6677889900"),
                      "99FFEE88DD77CC66BB55AA4433221100", a_name, a_then))
print("can_import B:", bp.can_import(graph, B))
print("pasted:", bp.import_nodes(graph, B))
bp.mark_structurally_modified(bp_ptr)

# --- step 3: did B.execute actually wire to A.then? ---
text2 = bp.export_nodes(bp.objects_with_outer(graph))
print("\n=== readback (compact) ===")
print(bc.compact_graph(bc.parse_nodes(text2), "EventGraph"))
# explicit: does the PrintString's execute now reference A's pin id?
linked = a_then and a_then in text2 and ("LinkedTo=(%s %s" % (a_name, a_then)) in text2
print("cross-link resolved (B.execute -> A.then present):", bool(linked))
