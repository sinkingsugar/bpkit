import unreal
ar = unreal.AssetRegistryHelpers.get_asset_registry()
# AnimBlueprints + AnimLayerInterfaces with mounted/horse/ride in the name
for cls in ("AnimBlueprint",):
    far = unreal.ARFilter(class_names=[cls], recursive_classes=True)
    assets = ar.get_assets(far)
    hits = [a for a in assets if any(k in str(a.asset_name).lower() for k in ("mount", "horse", "ride", "rider", "saddle"))]
    print("%s with mount-name (%d):" % (cls, len(hits)))
    for a in hits[:40]:
        print("   ", str(a.package_name) + "." + str(a.asset_name))

# live: inspect a mounted character's mesh linked anim layers (player if mounted)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world:
    def call(o, n, *a):
        try: return getattr(o, n)(*a)
        except Exception as e: return "ERR(%s)" % str(e)[:40]
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    host = pc.get_controlled_pawn() if pc else None
    if host:
        mesh = host.get_editor_property("Mesh")
        print("\nPLAYER mesh anim class:", call(mesh, "get_anim_instance").get_class().get_name() if call(mesh,"get_anim_instance") and "ERR" not in str(call(mesh,"get_anim_instance")) else None)
        print("  linked anim layer methods:", [m for m in dir(mesh) if "link" in m.lower()][:8])
        li = call(mesh, "get_linked_anim_instances" if hasattr(mesh, "get_linked_anim_instances") else "k2_get_anim_instance")
        print("  linked instances:", [x.get_class().get_name() for x in li] if isinstance(li, (list, tuple)) else li)
