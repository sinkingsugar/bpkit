"""Example: inject a node into a scratch blueprint, then compile + save.

    python ue_run.py examples/inject_and_compile.py

A comment node is schema-trivial (no pins) so it isolates the paste mechanism.
Replace TEXT with real node text (e.g. captured via read_blueprint) to author
actual logic; inject() runs the schema pre-check, paste, mark-modified, compile
(the validator) and save."""
from bpkit import bridge as bp

bp_obj, full = bp.scratch_blueprint(name="BP_Example")
print("scratch blueprint:", full)

TEXT = ('Begin Object Class=/Script/UnrealEd.EdGraphNode_Comment Name="Hello"\n'
        '   NodeComment="injected by bpkit.bridge"\n'
        '   NodePosX=80\n   NodePosY=80\nEnd Object\n')

result = bp.inject(full, TEXT, graph_name="EventGraph")
print("inject ->", result)
