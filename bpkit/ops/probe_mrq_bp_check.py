"""Read back the BP-side recv proof: the spawned BP_MrqRecvProbe's LastMsg var
must hold the echoed message if the BP-bound delegate fired."""
import unreal, builtins

state = getattr(builtins, "_mrq_probe", None)
assert state and state.get("inst"), "run probe_mrq_bp.py first"
inst = state["inst"]
print("python-side hits:", state["hits"])
print("BP LastMsg     :", repr(inst.get_editor_property("LastMsg")))
