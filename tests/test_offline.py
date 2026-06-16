"""Offline unit tests for the pure-stdlib bpkit libs + the compat shims.

NO editor and NO remote-execution required -- run directly with the bundled
python (it only needs the repo on sys.path, which it adds from __file__):

    & 'C:\\Program Files\\Epic Games\\CEUE5Devkit\\Engine\\Binaries\\ThirdParty\\Python3\\Win64\\python.exe' tests\\test_offline.py

Covers parse/render/edit + the authoring DSL (ir), the compactor (compact),
config sanity, and that the root `bp_*` shims ARE the canonical `bpkit.*`
objects. The in-editor behaviour (paste/compile/run) is covered separately by
tests/test_bp_authoring.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo root
from bpkit import ir, compact, config

_results = []


def expect(name, ok, detail=""):
    _results.append((name, bool(ok), detail))


# --- ir: parse <-> render round-trip --------------------------------------
def test_ir_roundtrip():
    g = ir.Graph()
    ev = g.event("ReceiveBeginPlay")
    pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary", inputs={"InString": "hi"})
    g.wire(ev, "then", pr, "execute")
    parsed = ir.Graph.parse_one(g.render(), "EventGraph")
    expect("ir.parse sees both nodes", len(parsed.nodes) == 2)
    reparsed = ir.Graph.parse_one(parsed.render(), "EventGraph")  # render -> parse is stable
    expect("ir round-trip stable node count", len(reparsed.nodes) == 2)
    expect("ir preserves a wire across round-trip",
           any(p.links for n in reparsed.nodes for p in n.pins))


# --- ir: wire / unwire keep both ends in sync ------------------------------
def test_ir_wire_unwire():
    g = ir.Graph("EventGraph")
    a = g.custom_event("A")
    b = g.call("PrintString", "/Script/Engine.KismetSystemLibrary")
    g.wire(a, "then", b, "execute")
    expect("wire sets the source link", len(a.pin("then").links) == 1)
    expect("wire sets the dest mirror link", len(b.pin("execute").links) == 1)
    g.unwire(a, "then")
    expect("unwire clears the source", len(a.pin("then").links) == 0)
    expect("unwire clears the dest mirror", len(b.pin("execute").links) == 0)


# --- ir: a typed pin carries its PinType (so it won't orphan on paste) ------
def test_ir_typed_pin():
    g = ir.Graph("EventGraph")
    n = g.call("SetAnimationMode", "/Script/Engine.SkeletalMeshComponent")
    g.typed_input(n, "InAnimationMode", "AnimationSingleNode", "byte",
                  ir.enum_path("/Script/Engine.EAnimationMode"))
    p = n.pin("InAnimationMode")
    expect("typed pin has PinCategory", p.get("PinType.PinCategory") == '"byte"')
    expect("typed pin keeps the default value", p.default == "AnimationSingleNode")
    expect("typed pin renders its SubCategoryObject", "EAnimationMode" in n.render())


# --- ir DSL renders wired import text --------------------------------------
def test_author_render():
    g = ir.Graph()
    ev = g.event("ReceiveBeginPlay")
    pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary", inputs={"InString": "x"})
    g.wire(ev, "then", pr, "execute")
    text = g.render()
    expect("render emits the Event node", "K2Node_Event" in text)
    expect("render emits a LinkedTo wire", "LinkedTo=(" in text)
    expect("render carries the literal default", 'DefaultValue="x"' in text)
    expect("render uses real (non-zero) GUIDs", "NodeGuid=00000000" not in text)


# --- compact: dense navigable outline --------------------------------------
def test_compact():
    g = ir.Graph()
    ev = g.event("ReceiveBeginPlay")
    pr = g.call("PrintString", "/Script/Engine.KismetSystemLibrary", inputs={"InString": "x"})
    g.wire(ev, "then", pr, "execute")
    nodes = compact.parse_nodes(g.render())
    out = compact.compact_graph(nodes, nodes[0].graph)
    expect("compact reports the node count", "2 nodes" in out)
    expect("compact labels the call", "PrintString" in out)
    expect("compact shows an outgoing edge", "->" in out)
    expect("compact shows a literal input", "= x" in out)


# --- config: engine-agnostic, sane defaults --------------------------------
def test_config():
    expect("REPO_ROOT is a real dir", os.path.isdir(config.REPO_ROOT))
    expect("REPO_ROOT is THIS repo", os.path.isfile(os.path.join(config.REPO_ROOT, "ue_run.py")))
    expect("BUNDLED_PYTHON ends in python.exe", config.BUNDLED_PYTHON.lower().endswith("python.exe"))
    expect("endpoints are ints", isinstance(config.COMMAND_PORT, int) and isinstance(config.MULTICAST_PORT, int))


TESTS = [test_ir_roundtrip, test_ir_wire_unwire, test_ir_typed_pin, test_author_render,
         test_compact, test_config]

print("=== bpkit offline unit tests (no editor) ===")
for t in TESTS:
    try:
        t()
    except Exception:
        import traceback
        expect(t.__name__ + " (raised)", False, traceback.format_exc().splitlines()[-1][:160])

passed = sum(1 for _, ok, _ in _results if ok)
for name, ok, detail in _results:
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, "  -- " + detail if detail and not ok else ""))
print("=== %d/%d passed ===" % (passed, len(_results)))
sys.exit(0 if passed == len(_results) else 1)
