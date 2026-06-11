"""Read-only: exact signatures + purity flags for every function the mrq-echo
mod graph calls (paste-drop / wrong-pin-name protection before authoring)."""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import ctypes, unreal
from bpkit import bridge

def doc(o):
    return ((getattr(o, "__doc__", "") or "").strip().splitlines() or [""])[0]

CHECKS = [
    (unreal.ConanCharacter, "hud_show_fifo"),
    (unreal.TextLibrary, "conv_string_to_text"),
    (unreal.StringLibrary, "concat_str_str"),
    (unreal.GameplayStatics, "spawn_object"),
    (unreal.MoviePipelinePythonHostExecutor, "connect_socket"),
    (unreal.MoviePipelinePythonHostExecutor, "send_socket_message"),
    (unreal.MoviePipelinePythonHostExecutor, "is_socket_connected"),
    (unreal.MoviePipelinePythonHostExecutor, "disconnect_socket"),
]
for cls, name in CHECKS:
    ok = hasattr(cls, name)
    print("%-28s.%-24s %s  %s" % (cls.__name__, name, "OK " if ok else "MISSING",
                                  doc(getattr(cls, name, None))[:100]))

print("\nModController:", doc(unreal.ModController)[:80],
      "|", (unreal.ModController.__doc__ or "").count("DreamworldMods") and "DreamworldMods" or "?")

# purity (FUNC_BlueprintPure=0x10000000) at the calibrated 0xd0 offset
def flags(path):
    a = bridge.find_object(path)
    return ctypes.cast(ctypes.c_void_p(a + 0xD0), ctypes.POINTER(ctypes.c_uint32)).contents.value if a else None

sanity = flags("/Script/Engine.KismetSystemLibrary:PrintString")
assert sanity and sanity & 0x400, "0xd0 offset sanity failed: %r" % sanity
for f in ("IsSocketConnected", "ConnectSocket", "SendSocketMessage", "OnBeginFrame"):
    v = flags("/Script/MovieRenderPipelineCore.MoviePipelineExecutorBase:%s" % f)
    print("%-20s flags=0x%08X  pure=%s callable=%s" % (
        f, v or 0, bool(v and v & 0x10000000), bool(v and v & 0x4000000)))
v = flags("/Script/ConanSandbox.ConanCharacter:HUDShowFIFO")
print("%-20s flags=0x%08X  static=%s" % ("HUDShowFIFO", v or 0, bool(v and v & 0x2000)))
print("DONE")
