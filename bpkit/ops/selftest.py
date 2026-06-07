"""In-editor bridge self-test: resolve every native symbol the ctypes bridge needs
against THIS editor build, and make one read-only native call. Non-mutating.

    & $py ue_run.py bpkit/ops/selftest.py

A FAIL means a symbol's decorated name differs on this build (or it isn't an editor
build that exports it) -- re-derive the name with bpkit.pe and patch SYM (see the
/setup skill). Don't assume the bridge is broken: most of it is stable across UE5
and failures are loud + localized to one symbol.
"""
from bpkit import bridge

r = bridge.selftest()
for k, a in r["resolved"].items():
    print("  ok    %-34s %s" % (k, a))
for k, e in r["failed"].items():
    print("  FAIL  %-34s %s" % (k, e))
print("functional native call (StaticFindObject /Script/Engine.Actor):", r["functional"])
print("BRIDGE OK" if r["ok"]
      else "BRIDGE NEEDS ATTENTION: %d symbol(s) to re-derive with bpkit.pe" % len(r["failed"]))
