import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
far = unreal.ARFilter(class_names=["Blueprint"], recursive_classes=True)
hits = [a for a in ar.get_assets(far) if str(a.asset_name) == "BPEmoteController"]
print("found:", [str(a.package_name) for a in hits])
if hits:
    pkg = str(hits[0].package_name)
    unreal.EditorAssetLibrary.load_asset(pkg)
    cls = unreal.load_object(None, pkg + ".BPEmoteController_C")
    cdo = unreal.get_default_object(cls)
    t = type(cdo)
    for fn in ("start_emote", "learn_emote", "give_startup_emotes", "can_perform_emote"):
        m = getattr(t, fn, None)
        doc = (m.__doc__ if m else "NOT FOUND")
        print("=== %s ===\n%s" % (fn, doc))
