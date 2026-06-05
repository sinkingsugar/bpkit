"""Native DreamworldMods.ModController lifecycle surface + raw graph text of the
example controller, to find the canonical persistent-mod entry point (BeginPlay/
Tick/OnModLoaded/registration) our polling manager will hook.
Run: python ue_run.py dev/probe_modcontroller_api.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp

print("=== ModController reflected methods (lifecycle/registration) ===")
mc = unreal.ModController
KW = ("begin", "tick", "mod", "load", "init", "register", "spawn", "construct",
      "start", "setup", "controller", "enable", "activ")
seen = set()
for m in sorted(dir(mc)):
    if m.startswith("__"):
        continue
    if any(k in m.lower() for k in KW):
        print("   ", m)
        seen.add(m)
print("   ...total non-dunder members:", len([m for m in dir(mc) if not m.startswith('__')]))

# Is it an Actor (has tick/world) or a UObject?
print("\nis subclass of Actor:", issubclass(mc, unreal.Actor) if hasattr(unreal, 'Actor') else "?")
try:
    print("is subclass of Info:", issubclass(mc, unreal.Info))
except Exception:
    pass

print("\n=== Example_modcontroller raw graph text (populated graphs) ===")
full = "/Game/Items/Example_modcontroller.Example_modcontroller"
graphs = bp.read_blueprint(full)
for g in graphs:
    if g["node_count"] == 0:
        continue
    print("\n--- graph%d (%d nodes) ---" % (g["index"], g["node_count"]))
    # print just the node headers + member refs, not full pin dumps
    for line in g["text"].splitlines():
        s = line.strip()
        if s.startswith("Begin Object") or "MemberName" in s or "FunctionReference" in s \
           or "CustomFunctionName" in s or "EventReference" in s or s.startswith("End Object"):
            print("   ", s[:160])
