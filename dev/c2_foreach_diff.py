"""Dump a REAL working ForEachLoop node (full) vs my authored one, to find what
makes mine inert."""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_bridge",): sys.modules.pop(_m, None)
import bp_bridge as bp, re

def dump_foreach(path, label):
    graphs = bp.read_blueprint(path)
    for gr in graphs:
        for blk in re.split(r'(?=Begin Object Class=)', gr["text"]):
            if "K2Node_MacroInstance" in blk and "ForEachLoop" in blk:
                print("\n========== %s ==========" % label)
                for line in blk.splitlines():
                    s = line.strip()
                    if s.startswith("Begin Object"):
                        print(s[:90])
                    elif s.startswith("CustomProperties Pin"):
                        # just name + category + container + linked
                        nm = re.search(r'PinName="([^"]+)"', s)
                        cat = re.search(r'PinType.PinCategory="([^"]*)"', s)
                        cont = re.search(r'PinType.ContainerType=(\w+)', s)
                        lk = "LINKED" if "LinkedTo=(" in s else ""
                        orph = "ORPHAN" if "bOrphanedPin=True" in s else ""
                        print("  PIN %-16s cat=%-8s container=%-6s %s %s" % (
                            nm.group(1) if nm else "?", cat.group(1) if cat else "-",
                            cont.group(1) if cont else "-", lk, orph))
                    elif "=" in s and not s.startswith("CustomProperties") and not s.startswith("End"):
                        print("  HDR", s[:120])
                return
    print(label, ": no ForEach found")

dump_foreach("/Game/Systems/Thrall/BP_ThrallSystemComponent.BP_ThrallSystemComponent", "REAL (works)")
dump_foreach("/Game/_Scratch/BP_LoopTest.BP_LoopTest", "MINE (inert)")
