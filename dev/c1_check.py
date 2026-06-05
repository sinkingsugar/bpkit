import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp

FULL = "/Game/_Scratch/BP_MF_Recipe.BP_MF_Recipe"

# 1) recompile + confirm the custom events exist on the generated class
bp_obj = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
gc = unreal.load_object(None, FULL + "_C")
cdo = unreal.get_default_object(gc)
print("generated class:", gc.get_name() if gc else None)
print("has 'stow' method:", hasattr(cdo, "stow"))
print("has 'restore' method:", hasattr(cdo, "restore"))

# 2) confirm enum/byte pin defaults survived the import (not blanked by schema)
bp_ptr, graph_ptr = bp.find_graph(FULL, "EventGraph")
txt = bp.export_nodes(bp.graph_nodes(graph_ptr))
import re
print("\n-- enum/byte pin defaults as stored after compile --")
for pin in ("LocationRule", "RotationRule", "ScaleRule", "InAnimationMode",
            "NewMovementMode", "InSocketName"):
    for m in re.finditer(r'PinName="%s"[^)]*?DefaultValue="([^"]*)"' % pin, txt):
        print("   %s = %r" % (pin, m.group(1)))
