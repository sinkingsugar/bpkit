"""Read-only deep probe: is there ANY BP-reachable websocket RECV path in this build?

Stages:
  S1  ground truth -- does the Python reflection layer expose BP-overridable events
      (BlueprintImplementable/NativeEvent)?  Checked against rcon_command, which we
      KNOW is one (we override it in mods/rcon-echo).
  S2  WebSocketConnectionManager deep dump (full class doc + every non-Object attr,
      full MRO).
  S3  every reflected type in the FuncomLiveServices module, fully dumped.
  S4  build-wide sweep: (a) type names matching socket/ws/tcp/udp/stomp/packet,
      (b) every MulticastDelegate-typed property on every class whose name/doc is
      recv-ish, (c) every class attr (any kind) named like a receive hook.
"""
import unreal, re

def doc(o, n=1):
    d = (getattr(o, "__doc__", "") or "").strip().splitlines()
    return " | ".join(d[:n]) if d else ""

OBJ_BASE = set(dir(unreal.Object))

print("########## S1: BP-overridable-event visibility (ground truth) ##########")
print("  RconCommandObject rcon-ish attrs:",
      [n for n in dir(unreal.RconCommandObject) if "rcon" in n.lower()])
for probe in ("receive_begin_play", "receive_tick", "receive_destroyed"):
    print("  Actor.%s exposed: %s" % (probe, hasattr(unreal.Actor, probe)))

print("\n########## S2: WebSocketConnectionManager deep dump ##########")
cls = getattr(unreal, "WebSocketConnectionManager", None)
if cls is None:
    print("  !! unreal.WebSocketConnectionManager NOT FOUND")
else:
    print("  MRO:", " -> ".join(c.__name__ for c in cls.__mro__))
    print("  ---- full class __doc__ ----")
    print(cls.__doc__)
    print("  ---- attrs (minus unreal.Object baseline) ----")
    for n in sorted(set(dir(cls)) - OBJ_BASE):
        if n.startswith("_"): continue
        print("   %-42s %s" % (n, doc(getattr(cls, n, None))[:160]))
    # ConnectionSettings struct too
    cs = getattr(unreal, "ConnectionSettings", None)
    if cs is not None:
        print("  ---- ConnectionSettings struct ----")
        print(cs.__doc__)

print("\n########## S3: ALL FuncomLiveServices reflected types ##########")
fls = []
for n in dir(unreal):
    if n.startswith("_"): continue
    t = getattr(unreal, n, None)
    if isinstance(t, type) and "FuncomLiveServices" in (t.__doc__ or ""):
        fls.append((n, t))
print("  (%d types)" % len(fls))
for n, t in fls:
    print("  ---- %s :: %s" % (n, doc(t)[:120]))
    base = OBJ_BASE if issubclass(t, unreal.Object) else set(dir(type("x", (object,), {})))
    try:
        base = base | set(dir(unreal.StructBase)) if issubclass(t, unreal.StructBase) else base
    except Exception:
        pass
    for a in sorted(set(dir(t)) - base):
        if a.startswith("_"): continue
        print("       %-40s %s" % (a, doc(getattr(t, a, None))[:150]))

print("\n########## S4a: type-name sweep (socket/ws/stomp/tcp/udp/packet) ##########")
pat = re.compile(r"websock|socket|stomp|tcp|udp|packet", re.I)
for n in dir(unreal):
    if n.startswith("_"): continue
    if pat.search(n):
        print("  %-52s %s" % (n, doc(getattr(unreal, n, None))[:110]))

print("\n########## S4b+c: build-wide attr sweep (delegates + recv-ish names) ##########")
recvish = re.compile(r"recv|received|receive|on_message|message_|incoming|inbound|listen", re.I)
netish  = re.compile(r"websock|socket|stomp|tcp|udp|packet|wss", re.I)
n_cls = n_attr = n_dlg = 0
hits = []
for n in dir(unreal):
    if n.startswith("_"): continue
    t = getattr(unreal, n, None)
    if not isinstance(t, type):
        continue
    n_cls += 1
    for a in dir(t):
        if a.startswith("_"): continue
        n_attr += 1
        m = getattr(t, a, None)
        d = getattr(m, "__doc__", "") or ""
        is_dlg = "MulticastDelegate" in d[:60] or d.startswith("(Delegate")
        if is_dlg:
            n_dlg += 1
        # report: any delegate that smells net/recv-ish, OR any attr on any class
        # whose NAME smells websocket-ish, OR recv-ish delegate
        if (is_dlg and (recvish.search(a) or netish.search(a) or netish.search(d[:200]))) \
           or (netish.search(a)):
            hits.append("  %-38s . %-40s %s%s" % (n, a, "[DELEGATE] " if is_dlg else "", d[:110].replace("\n", " ")))
seen = set()
for h in hits:
    if h in seen: continue
    seen.add(h)
    print(h)
print("  (swept %d classes / %d attrs; %d delegate props total in build; %d hits)"
      % (n_cls, n_attr, n_dlg, len(hits)))
print("DONE")
