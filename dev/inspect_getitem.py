import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
for _m in ("bp_ir", "bp_bridge"): sys.modules.pop(_m, None)
import bp_bridge as bp
import re
FULL = "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager"
bp_ptr, gp = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(gp))
blocks = re.split(r'(?=Begin Object Class=)', txt)

def pin_links(blk, pinname):
    for pin in re.findall(r'CustomProperties Pin \((.*)\)', blk):
        if 'PinName="%s"' % pinname in pin:
            m = re.search(r'LinkedTo=\(([^)]*)\)', pin)
            return m.group(1).strip() if m and m.group(1).strip() else "** NOT LINKED **"
    return "(no such pin)"

# GetArrayItem: full Output link
for blk in blocks:
    if "K2Node_GetArrayItem" in blk:
        nm = re.search(r'Name="([^"]+)"', blk).group(1)
        print("GetArrayItem %s : Output ->" % nm, pin_links(blk, "Output"))
        outlink = pin_links(blk, "Output")

# every IsValid CallFunction: what feeds its Object pin
print("\n--- IsValid nodes (Object pin source) ---")
for blk in blocks:
    if 'MemberName="IsValid"' in blk:
        nm = re.search(r'Name="([^"]+)"', blk).group(1)
        print("  %s : Object <-" % nm, pin_links(blk, "Object"), "| ReturnValue ->", pin_links(blk, "ReturnValue")[:50])
