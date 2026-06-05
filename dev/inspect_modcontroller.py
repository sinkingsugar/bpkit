"""Inspect /Game/Items/Example_modcontroller — Conan's mod-controller template.
Run: python ue_run.py dev/inspect_modcontroller.py
"""
import sys
sys.path.insert(0, r"C:\Users\sugar\devel\conan")
import unreal
import bp_bridge as bp
import bp_compact as bc

PATH = "/Game/Items/Example_modcontroller"
full = PATH + "." + PATH.rsplit("/", 1)[1]

obj = unreal.EditorAssetLibrary.load_asset(PATH)
print("loaded:", obj.get_name() if obj else None, "| class:", obj.get_class().get_name() if obj else None)

# parent class via asset-registry tags (robust)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
try:
    pkg = unreal.Name(PATH)
    ads = ar.get_assets_by_package_name(pkg)
    for ad in ads:
        for tag in ("ParentClass", "NativeParentClass", "GeneratedClass"):
            try:
                v = ad.get_tag_value(tag)
                if v:
                    print("  tag %s = %s" % (tag, v))
            except Exception:
                pass
except Exception as e:
    print("registry err:", e)

# parent via generated class CDO super
try:
    gc = unreal.load_object(None, full + "_C")
    if gc:
        print("generated class:", gc.get_name())
except Exception as e:
    print("genclass err:", e)

# variables
try:
    print("\n-- variables --")
    for v in obj.get_editor_property("new_variables"):
        vt = v.get_editor_property("var_type")
        print("   ", v.get_editor_property("var_name"), ":", vt.pin_category)
except Exception as e:
    print("vars err:", e)

# functions list (graph names)
print("\n-- graphs --")
graphs = bp.read_blueprint(full)
print("total graphs:", len(graphs))
for g in graphs:
    nc = g["node_count"]
    label = "graph%d" % g["index"]
    print("\n### %s | nodes: %d" % (label, nc))
    if nc == 0:
        continue
    try:
        print(bc.compact_graph(bc.parse_nodes(g["text"]), label))
    except Exception as e:
        print("   compact err:", e, "-- raw head:")
        print(g["text"][:1200])
