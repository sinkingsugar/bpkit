"""Read-only: raw FunctionFlags of the hidden WebSocketConnectionManager UFunctions.

The DLL exports show exec thunks for OnReceiveData / OnConnectionComplete /
OnConnectionClosed / OnConnectionError -- reflected UFunctions invisible to the
Python/BP layer. Read their EFunctionFlags directly: calibrate the FunctionFlags
offset inside UFunction against three knowns with distinct flag patterns
(a BlueprintImplementableEvent, a static BlueprintCallable lib func, and a
BlueprintNativeEvent), then decode the targets.
"""
import sys
for k in [k for k in list(sys.modules) if k == "bpkit" or k.startswith("bpkit.")]:
    sys.modules.pop(k)
import ctypes, unreal
from bpkit import bridge

print("PIE active:", unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor())

PATHS = [
  ("known_BIE  Actor:ReceiveBeginPlay",         "/Script/Engine.Actor:ReceiveBeginPlay"),
  ("known_LIB  KSL:PrintString",                "/Script/Engine.KismetSystemLibrary:PrintString"),
  ("known_BNE  WSCM:SendMessage",               "/Script/FuncomLiveServices.WebSocketConnectionManager:SendMessage"),
  ("target     WSCM:OnReceiveData",             "/Script/FuncomLiveServices.WebSocketConnectionManager:OnReceiveData"),
  ("target     WSCM:OnConnectionComplete",      "/Script/FuncomLiveServices.WebSocketConnectionManager:OnConnectionComplete"),
  ("target     WSCM:OnConnectionClosed",        "/Script/FuncomLiveServices.WebSocketConnectionManager:OnConnectionClosed"),
  ("target     WSCM:OnConnectionError",         "/Script/FuncomLiveServices.WebSocketConnectionManager:OnConnectionError"),
  ("base       CM:Init",                        "/Script/FuncomLiveServices.ConnectionManager:Init"),
  ("base       CM:OnReceiveData?",              "/Script/FuncomLiveServices.ConnectionManager:OnReceiveData"),
]
ptrs = {}
for label, p in PATHS:
    a = bridge.find_object(p)
    ptrs[label] = a
    print("  %-44s %s" % (label, hex(a) if a else "NOT FOUND"))

def u32(addr):
    return ctypes.cast(ctypes.c_void_p(addr), ctypes.POINTER(ctypes.c_uint32)).contents.value

F_NATIVE = 0x400; F_EVENT = 0x800; F_STATIC = 0x2000; F_BPCALL = 0x4000000; F_BPEVENT = 0x8000000
conds = [
  ("known_BIE  Actor:ReceiveBeginPlay",  lambda v: not v & F_NATIVE and v & F_EVENT and v & F_BPEVENT),
  ("known_LIB  KSL:PrintString",         lambda v: v & F_NATIVE and v & F_STATIC and v & F_BPCALL and not v & F_BPEVENT),
  ("known_BNE  WSCM:SendMessage",        lambda v: v & F_NATIVE and v & F_BPEVENT),
]
cands = []
for off in range(0x60, 0x200, 4):
    try:
        if all(c(u32(ptrs[l] + off)) for l, c in conds if ptrs[l]):
            cands.append(off)
    except Exception:
        pass
print("candidate FunctionFlags offsets:", [hex(o) for o in cands])

NAMES = {0x1: "Final", 0x4: "BlueprintAuthorityOnly", 0x8: "BlueprintCosmetic", 0x40: "Net",
 0x80: "NetReliable", 0x200: "Exec", 0x400: "Native", 0x800: "Event", 0x2000: "Static",
 0x4000: "NetMulticast", 0x10000: "MulticastDelegate", 0x20000: "Public", 0x40000: "Private",
 0x80000: "Protected", 0x100000: "Delegate", 0x400000: "HasOutParms", 0x800000: "HasDefaults",
 0x4000000: "BlueprintCallable", 0x8000000: "BlueprintEvent", 0x10000000: "BlueprintPure",
 0x40000000: "Const"}
for off in cands:
    print("---- decoding at offset", hex(off))
    for label, a in ptrs.items():
        if not a:
            continue
        v = u32(a + off)
        fl = "|".join(n for b, n in sorted(NAMES.items()) if v & b)
        print("  %-44s 0x%08X  %s" % (label, v, fl))
print("DONE")
