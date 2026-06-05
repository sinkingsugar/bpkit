"""Extract a real ForEachLoop K2Node_MacroInstance verbatim from an existing BP so we
can author it (need the exact MacroGraphReference path+GUID + pin names)."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_bridge",): sys.modules.pop(_m, None)
import unreal
import bp_bridge as bp

CANDIDATES = [
    "/Game/Systems/Thrall/BP_ThrallSystemComponent.BP_ThrallSystemComponent",
    "/Game/Items/Example_modcontroller.Example_modcontroller",
]
found = False
for path in CANDIDATES:
    if found:
        break
    try:
        graphs = bp.read_blueprint(path)
    except Exception as e:
        print("skip", path, str(e).splitlines()[-1][:50]); continue
    for gr in graphs:
        if "ForEachLoop" not in gr["text"]:
            continue
        # print the first macro-instance node block that mentions ForEachLoop
        import re
        for blk in re.split(r'(?=Begin Object Class=)', gr["text"]):
            if "K2Node_MacroInstance" in blk and "ForEachLoop" in blk:
                print("FOUND in", path, "graph", gr["index"])
                for line in blk.splitlines():
                    s = line.strip()
                    if s.startswith("MacroGraphReference") or "PinName=" in s or s.startswith("Begin Object") or s.startswith("End Object"):
                        print("  ", s[:170])
                found = True
                break
        if found:
            break
if not found:
    print("no ForEachLoop found in candidates")
