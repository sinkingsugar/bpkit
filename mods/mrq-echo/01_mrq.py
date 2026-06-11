"""mrq-echo build: BP_MrqEchoController : DreamworldMods.ModController.

The cooked-game proof of the MRQ TCP push channel (docs/CONAN-NOTES.md §Network):
  BeginPlay : Construct MoviePipelinePythonHostExecutor -> Ex var -> Bind Event
              (SocketMessageRecievedDelegate -> OnSockMsg)
  Tick      : if not Ex.IsSocketConnected (pure) -> ConnectSocket(127.0.0.1:9777)
              -> on success SendSocketMessage(hello) + HUD banner
              (per-tick retry; localhost refused fails sub-ms, fine for a probe)
  OnSockMsg : SendSocketMessage("ack:"+Message) + HUDShowFIFO("MRQ RECV: "+Message)
              (HUD is the Shipping-safe diagnostic; PrintString is compiled out)

Authoring notes:
 - one wired set pasted via inject (wired sets paste whole; count asserted);
   ONLY the CustomEvent.OutputDelegate -> AddDelegate.Delegate wire is made live
   post-paste (bridge.connect_pins) -- delegate PinTypes don't merge from text.
 - GameplayStatics.SpawnObject is NOT BP-exposed in this build -> the construct
   step is a real K2Node_ConstructObjectFromClass (Class pin default = quoted
   class path + bIsUObjectWrapper, the GetAllActorsOfClass lesson).
 - IsSocketConnected is PURE (flags 0x54080401) -> no exec pins on it.

Run with Play STOPPED:  python ue_run.py mods/mrq-echo/01_mrq.py
Falls back to /Game/_Scratch (DRY RUN) when /Game/Mods/MrqEcho isn't mounted.
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
import os
import re as _re
from bpkit import bridge as bp, ir, compact as bc, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "mrq-echo"))
sys.modules.pop("me_config", None)
import me_config as MOD

MRQ_CLS = "/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor"
MRQ_BASE = "/Script/MovieRenderPipelineCore.MoviePipelineExecutorBase"
KSL = "/Script/Engine.KismetStringLibrary"
KTL = "/Script/Engine.KismetTextLibrary"
CONAN = "/Script/ConanSandbox.ConanCharacter"

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
assert not les.is_in_play_in_editor(), "Play is running -- stop PIE before building"

# paste-drop protection: every called function must reflect on this build
for cls, fn in [(unreal.StringLibrary, "concat_str_str"),
                (unreal.TextLibrary, "conv_string_to_text"),
                (unreal.ConanCharacter, "hud_show_fifo"),
                (unreal.MoviePipelinePythonHostExecutor, "connect_socket"),
                (unreal.MoviePipelinePythonHostExecutor, "send_socket_message"),
                (unreal.MoviePipelinePythonHostExecutor, "is_socket_connected")]:
    assert hasattr(cls, fn), "missing on this build: %s.%s" % (cls.__name__, fn)

# mod root if mounted+writable, else scratch dry-run
if unreal.EditorAssetLibrary.does_directory_exist(MOD.OUTPUT_PKG):
    PKG = MOD.OUTPUT_PKG
else:
    PKG = MOD.SCRATCH_PKG
    print("#" * 68)
    print("##  DRY RUN: %s not mounted (MrqEcho mod not active)" % MOD.OUTPUT_PKG)
    print("##  building into %s -- NOT shippable from there" % PKG)
    print("#" * 68)

PATH = PKG + "/" + MOD.CONTROLLER
FULL = MOD.full(PKG, MOD.CONTROLLER)

if unreal.EditorAssetLibrary.does_asset_exist(PATH):
    unreal.EditorAssetLibrary.delete_asset(PATH)
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=MOD.CONTROLLER, parent=unreal.ModController)
print("controller BP:", FULL)

bel = unreal.BlueprintEditorLibrary
objt = bel.get_object_reference_type(unreal.MoviePipelinePythonHostExecutor.static_class())
assert bel.add_member_variable(bp_obj, "Ex", objt), "add Ex failed"
bel.compile_blueprint(bp_obj)

# ---------------------------------------------------------------- the graph
EXP = ir.obj_path(MRQ_CLS)
g = ir.Graph("EventGraph")

# BeginPlay: construct -> Ex -> bind
ev_bp = g.event("ReceiveBeginPlay", pos=(-1500, -400))
mk = g.node("K2Node_GenericCreateObject", [], base="ConstructObject", pos=(-1220, -400))
cp = mk.pin("Class"); cp.dir = "EGPD_Input"
cp.set("PinType.PinCategory", '"class"')
cp.set("PinType.PinSubCategoryObject", ir.obj_path("/Script/CoreUObject.Object"))
cp.set("PinType.bIsUObjectWrapper", "True")
cp.set("DefaultObject", '"%s"' % MRQ_CLS)   # MUST be quoted, else Class=null
mk.pin("ReturnValue").typed("object", EXP, direction="EGPD_Output")
selfn = g.node("K2Node_Self", [], base="Self", pos=(-1420, -240))
g.wire(ev_bp, "then", mk, "execute")
g.wire(selfn, "self", mk, "Outer", exec=False)
setex = g.var_set("Ex", "object", EXP, pos=(-900, -400))
g.wire(mk, "then", setex, "execute")
g.wire(mk, "ReturnValue", setex, "Ex", exec=False)
getex_b = g.var_get("Ex", "object", EXP, pos=(-900, -220))
bind = g.node("K2Node_AddDelegate",
              ['DelegateReference=(MemberParent="%s",MemberName="SocketMessageRecievedDelegate")'
               % ir.obj_path(MRQ_BASE)], base="AddDelegate", pos=(-600, -400))
g.wire(setex, "then", bind, "execute")
g.wire(getex_b, "Ex", bind, "self", exec=False)
# bind.Delegate <- OnSockMsg.OutputDelegate is wired LIVE post-paste

# OnSockMsg(Message): ack back + HUD
onsock = g.custom_event("OnSockMsg", pos=(-1500, 200))
onsock.set('CustomProperties UserDefinedPin (PinName="Message",PinType=(PinCategory="string"),DesiredPinDirection=EGPD_Output)')
onsock.pin("Message").typed("string", direction="EGPD_Output")
getex_a = g.var_get("Ex", "object", EXP, pos=(-1500, 430))
cat_ack = g.call("Concat_StrStr", KSL, pos=(-1220, 340))
g.typed_input(cat_ack, "A", "ack:", "string")
g.wire(onsock, "Message", cat_ack, "B", exec=False)
send_ack = g.call("SendSocketMessage", MRQ_BASE, pos=(-950, 200))
g.wire(onsock, "then", send_ack, "execute")
g.wire(getex_a, "Ex", send_ack, "self", exec=False)
g.wire(cat_ack, "ReturnValue", send_ack, "InMessage", exec=False)
cat_hud = g.call("Concat_StrStr", KSL, pos=(-1220, 500))
g.typed_input(cat_hud, "A", "MRQ RECV: ", "string")
g.wire(onsock, "Message", cat_hud, "B", exec=False)
conv_hud = g.call("Conv_StringToText", KTL, pos=(-950, 500))
g.wire(cat_hud, "ReturnValue", conv_hud, "InString", exec=False)
hud = g.call("HUDShowFIFO", CONAN, pos=(-650, 200))
g.wire(send_ack, "then", hud, "execute")
g.wire(conv_hud, "ReturnValue", hud, "Text", exec=False)

# Tick: not connected -> connect -> hello + banner
ev_tk = g.event("ReceiveTick", pos=(-1500, 800))
getex_t = g.var_get("Ex", "object", EXP, pos=(-1500, 1030))
isconn = g.call("IsSocketConnected", MRQ_BASE, pos=(-1300, 950))   # PURE: no exec pins
g.wire(getex_t, "Ex", isconn, "self", exec=False)
br = g.branch(pos=(-1100, 800))
g.wire(ev_tk, "then", br, "execute")
g.wire(isconn, "ReturnValue", br, "Condition", exec=False)
conn = g.call("ConnectSocket", MRQ_BASE, pos=(-860, 800))
g.typed_input(conn, "InHostName", MOD.HOST, "string")
g.typed_input(conn, "InPort", str(MOD.PORT), "int")
g.wire(br, "else", conn, "execute")
g.wire(getex_t, "Ex", conn, "self", exec=False)
br2 = g.branch(pos=(-560, 800))
g.wire(conn, "then", br2, "execute")
g.wire(conn, "ReturnValue", br2, "Condition", exec=False)
hello = g.call("SendSocketMessage", MRQ_BASE, pos=(-320, 800))
g.typed_input(hello, "InMessage", MOD.HELLO, "string")
g.wire(br2, "then", hello, "execute")
g.wire(getex_t, "Ex", hello, "self", exec=False)
conv2 = g.call("Conv_StringToText", KTL, pos=(-320, 1030))
g.typed_input(conv2, "InString", "MRQ: gateway connected", "string")
hud2 = g.call("HUDShowFIFO", CONAN, pos=(-40, 800))
g.wire(hello, "then", hud2, "execute")
g.wire(conv2, "ReturnValue", hud2, "Text", exec=False)

text = g.render()
authored = text.count("Begin Object Class=")

# ---------------------------------------------------------------- inject
bp_ptr, g_ptr = bp.find_graph(FULL, "EventGraph")
bp.clear_graph(bp_ptr, g_ptr)
bel.compile_blueprint(bp_obj)   # flush stale func map before re-pasting events
res = bp.inject(FULL, text, graph_name="EventGraph", compile=False, save=False)
assert res["ok"], res
assert res["pasted"] == authored, "paste dropped nodes: %d/%d" % (res["pasted"], authored)
print("pasted %d/%d nodes" % (res["pasted"], authored))

# live wire: OnSockMsg.OutputDelegate -> AddDelegate.Delegate
bind_ptr = sock_ptr = None
for p in bp.graph_nodes(g_ptr):
    t = bp.export_nodes([p])
    if "K2Node_AddDelegate" in t.splitlines()[0]:
        bind_ptr = p
    elif 'CustomFunctionName="OnSockMsg"' in t:
        sock_ptr = p
assert bind_ptr and sock_ptr, "AddDelegate/OnSockMsg not found post-paste"
a = bp.find_pin(sock_ptr, "OutputDelegate", 1)
b = bp.find_pin(bind_ptr, "Delegate", 0)
assert a and b, "delegate pins missing"
assert bp.connect_pins(a, b), "schema refused the delegate wire"

bp.mark_structurally_modified(bp_ptr)
bel.compile_blueprint(bp_obj)

# ---------------------------------------------------------------- verify
txt = bp.export_nodes(bp.graph_nodes(g_ptr))
errs = _re.findall(r'ErrorMsg="([^"]+)"', txt)
orph = _re.findall(r'PinName="([^"]+)"[^)]*?bOrphanedPin=True', txt)
print("compile errors:", errs if errs else "(none)")
print("orphans:", orph if orph else "(none)")
assert not errs and not orph, "graph not clean"
assert unreal.EditorAssetLibrary.save_asset(PATH), "save failed"
print(bc.compact_graph(bc.parse_nodes(txt), "EventGraph"))
print("BUILD OK: mrq-echo v%d -> %s%s" % (
    MOD.VERSION, FULL, "  [DRY RUN -- not shippable]" if PKG != MOD.OUTPUT_PKG else ""))
