"""End-to-end BP recv proof: author a scratch Actor BP that binds
MoviePipelineExecutorBase.SocketMessageRecievedDelegate via K2Node_AddDelegate
(the BP 'Bind Event to' node), compile it, spawn it, point it at the LIVE
executor from probe_mrq_socket.py, and send a message so the echo fires the
BP event, which stores the payload in a LastMsg variable.

Run with Play STOPPED, AFTER probe_mrq_socket.py (needs builtins._mrq_probe and
the examples/mrq_tcp_probe_server.py echo server on 9777).
Then verify with probe_mrq_bp_check.py after ~2s.
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal, builtins
import re as _re
from bpkit import bridge as bp, ir

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert not les.is_in_play_in_editor(), "Play is running -- stop PIE first"

state = getattr(builtins, "_mrq_probe", None)
assert state, "run bpkit/ops/probe_mrq_socket.py first (need the live executor)"
ex = state["ex"]
assert ex.is_socket_connected(), "executor socket not connected -- restart probe chain"

MRQ_CLS = "/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor"
MRQ_BASE = "/Script/MovieRenderPipelineCore.MoviePipelineExecutorBase"

bp_obj, full = bp.scratch_blueprint(name="BP_MrqRecvProbe")
print("scratch:", full)

bel = unreal.BlueprintEditorLibrary
gen0 = bel.generated_class(bp_obj)
cdo0 = unreal.get_default_object(gen0)
if not hasattr(cdo0, "ex"):
    objt = bel.get_object_reference_type(unreal.MoviePipelinePythonHostExecutor.static_class())
    assert bel.add_member_variable(bp_obj, "Ex", objt), "add Ex failed"
    strt = bel.get_basic_type_by_name("string")
    assert bel.add_member_variable(bp_obj, "LastMsg", strt), "add LastMsg failed"
    bel.compile_blueprint(bp_obj)
# vars must be instance-editable for set_editor_property on the spawned actor
bel.set_blueprint_variable_instance_editable(bp_obj, "Ex", True)
bel.set_blueprint_variable_instance_editable(bp_obj, "LastMsg", True)
bel.compile_blueprint(bp_obj)

bp_ptr, g_ptr = bp.find_graph(full, "EventGraph")
assert g_ptr, "no EventGraph"
bp.clear_graph(bp_ptr, g_ptr)
# recompile NOW or the stale class function map makes the paste uniquify
# colliding custom-event names (MRQBindNow -> MRQBindNow_0)
bel.compile_blueprint(bp_obj)

# ---- paste one node per import (unwired multi-node sets drop nodes silently)
def paste_one(g_build):
    text = g_build.render()
    n = bp.import_nodes(g_ptr, text)
    assert n == len(g_build.nodes), "paste dropped: %d/%d\n%s" % (n, len(g_build.nodes), text)

g = ir.Graph(); g.custom_event("MRQBindNow", pos=(-400, 0)); paste_one(g)

g = ir.Graph()
g.var_get("Ex", "object", ir.obj_path(MRQ_CLS), pos=(-400, 200)); paste_one(g)

g = ir.Graph()
g.node("K2Node_AddDelegate",
       ['DelegateReference=(MemberParent="%s",MemberName="SocketMessageRecievedDelegate")'
        % (ir.obj_path(MRQ_BASE))], base="AddDelegate", pos=(-80, 0))
paste_one(g)

g = ir.Graph()
ce = g.custom_event("OnSockMsg", pos=(-400, 420))
# editor-world actors drop BP script unless the function carries CallInEditor
# (AActor::ProcessEvent gate); irrelevant in a begun-play game world
ce.set("bCallInEditor", "True")
ce.set('CustomProperties UserDefinedPin (PinName="Message",PinType=(PinCategory="string"),DesiredPinDirection=EGPD_Output)')
paste_one(g)

g = ir.Graph(); g.var_set("LastMsg", "string", pos=(-80, 420)); paste_one(g)

# ---- classify live nodes (event names may have been uniquified -> capture them)
ptr_of, ev_name = {}, {}
for p in bp.graph_nodes(g_ptr):
    t = bp.export_nodes([p])
    first = t.splitlines()[0]
    m = _re.search(r'CustomFunctionName="([^"]+)"', t)
    if "K2Node_AddDelegate" in first:                ptr_of["bind"] = p
    elif m and m.group(1).startswith("MRQBindNow"):  ptr_of["go"] = p;   ev_name["go"] = m.group(1)
    elif m and m.group(1).startswith("OnSockMsg"):   ptr_of["sock"] = p; ev_name["sock"] = m.group(1)
    elif "K2Node_VariableGet" in first:              ptr_of["getex"] = p
    elif "K2Node_VariableSet" in first:              ptr_of["setmsg"] = p
assert len(ptr_of) == 5, "classification incomplete: %s" % sorted(ptr_of)
print("event names:", ev_name)

# the custom event must actually carry the user pin
assert bp.find_pin(ptr_of["sock"], "Message", 1), "OnSockMsg lost its Message pin"

def wire(sk, sp, dk, dp):
    a = bp.find_pin(ptr_of[sk], sp)
    b = bp.find_pin(ptr_of[dk], dp)
    assert a and b, "pin missing: %s.%s / %s.%s" % (sk, sp, dk, dp)
    assert bp.connect_pins(a, b), "schema REFUSED: %s.%s -> %s.%s" % (sk, sp, dk, dp)

wire("go",    "then",           "bind",   "execute")
wire("getex", "Ex",             "bind",   "self")
wire("sock",  "OutputDelegate", "bind",   "Delegate")   # the BlueprintAssignable test
wire("sock",  "then",           "setmsg", "execute")
wire("sock",  "Message",        "setmsg", "LastMsg")

bp.mark_structurally_modified(bp_ptr)
bel.compile_blueprint(bp_obj)

txt = bp.export_nodes(bp.graph_nodes(g_ptr))
errs = _re.findall(r'ErrorMsg="([^"]+)"', txt)
assert not errs, "compile errors: %s" % errs[:3]
assert "bOrphanedPin=True" not in txt, "orphaned pin"
print("BP compiled clean: AddDelegate on SocketMessageRecievedDelegate ACCEPTED")

# ---- spawn + live-fire (sweep strays from previous failed runs first)
gen = bel.generated_class(bp_obj)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    if a.get_class().get_name().startswith("BP_MrqRecvProbe"):
        print("destroying stray:", a.get_name())
        a.destroy_actor()
inst = eas.spawn_actor_from_class(gen, unreal.Vector(0.0, 0.0, -100000.0))
assert inst, "spawn failed"
inst.set_editor_property("Ex", ex)
inst.call_method(ev_name["go"])
state["inst"] = inst
print("spawned + bound:", inst.get_name())

sent = ex.send_socket_message("bp-recv-proof")
print("send_socket_message('bp-recv-proof') ->", sent)
print("now wait ~1s for the echo, then run probe_mrq_bp_check.py")
