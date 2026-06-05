"""Targeted probe: structural Blueprints + native classes for mount/follower.

Filters to Blueprint/BlueprintGeneratedClass assets only, precise name matching,
excludes anim/material/sound/texture/mesh. Also reflects loaded native UClasses
whose name hints at the mount or thrall system.

    python ue_run.py dev/probe_mount2.py
"""
import unreal

ar = unreal.AssetRegistryHelpers.get_asset_registry()

EXCLUDE_PREFIX = ("A_", "AM_", "AB_", "BS", "M_", "MI_", "MF_", "T_", "TEN_", "SM_",
                  "SK_", "SKM_", "S_", "Cue", "ABP_", "PA_", "NS_", "P_")
NAME_KW = ["mount", "ride", "rider", "saddle", "horse", "rhino", "camel",
           "thrall", "follower", "pet", "companion", "tame", "stable"]

print("=== Blueprint-class assets matching mount/follower keywords ===")
bp_assets = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), search_sub_classes=True)
print("blueprint assets total:", len(bp_assets))
rows = []
for a in bp_assets:
    name = str(a.asset_name)
    low = name.lower()
    if any(low.startswith(p.lower()) for p in EXCLUDE_PREFIX):
        continue
    if any(kw in low for kw in NAME_KW):
        rows.append(str(a.package_name) + "." + name)
for r in sorted(set(rows)):
    print("  BP", r)

print("\n=== Native/loaded UClasses hinting mount/ride/saddle/thrall/follower ===")
CLASS_KW = ["mount", "ride", "saddle", "thrall", "follower", "tame", "companion", "rein"]
seen = set()
for cls in unreal.UClass.static_class().__class__ and []:
    pass
# enumerate via the editor's loaded objects of type Class
import_count = 0
for obj in unreal.find_all_objects(unreal.Class) if hasattr(unreal, "find_all_objects") else []:
    pass

# Reliable enumeration: scan known class names through get_class_default_object isn't enumerable.
# Use the asset registry's class list + try to load a few well-known native class paths.
CANDIDATES = [
    "/Script/Conan.MountComponent",
    "/Script/Conan.RidingComponent",
    "/Script/Conan.MountedPawn",
    "/Script/Conan.ThrallComponent",
    "/Script/ConanSandbox.MountComponent",
    "/Script/ConanSandbox.RidingComponent",
]
for cp in CANDIDATES:
    c = unreal.load_object(None, cp)
    print("  try", cp, "->", c)
