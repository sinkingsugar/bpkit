"""Read-only: how do RconCommandObject BP subclasses register as commands?
Find all native + BP subclasses of RconCommandObject, dump CDO props, and any Rcon manager/registry."""
import unreal

print("########## native subclasses / siblings in RconPlugin ##########")
base = unreal.RconCommandObject
for n in dir(unreal):
    if n.startswith("_"): continue
    obj = getattr(unreal, n, None)
    try:
        if isinstance(obj, type) and issubclass(obj, base):
            doc = (obj.__doc__ or "")
            print("  CLASS %-44s" % n)
    except Exception:
        pass

print("\n########## full member dump of RconCommandObject (incl. props) ##########")
cls = base
for n in sorted(d for d in dir(cls) if not d.startswith("_")):
    m = getattr(cls, n, None)
    d0 = ((getattr(m, "__doc__", "") or "").strip().splitlines() or [""])[0]
    print("   %-44s %s" % (n, d0[:120]))

print("\n########## anything else from RconPlugin module ##########")
count = 0
for n in dir(unreal):
    if n.startswith("_"): continue
    obj = getattr(unreal, n, None)
    doc = getattr(obj, "__doc__", "") or ""
    if "RconPlugin" in doc:
        first = doc.strip().splitlines()[0]
        print("  %-44s %s" % (n, first[:90]))
        count += 1
print("(%d symbols)" % count)

print("\n########## BP assets deriving from RconCommandObject ##########")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
# derived classes via asset registry class hierarchy
names = ar.get_derived_class_names(
    [unreal.TopLevelAssetPath("/Script/RconPlugin", "RconCommandObject")], [])
for p in names:
    print("  derived:", p)
