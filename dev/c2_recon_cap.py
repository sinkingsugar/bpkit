import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

def members(obj, kws):
    return sorted(m for m in dir(obj) if not m.startswith("_")
                  and any(k in m.lower() for k in kws))

for getter in ("get_thrall_system_component", "get_my_formation_follower_component"):
    comp = getattr(pawn, getter)() if hasattr(pawn, getter) else None
    print("==", getter, "->", comp.get_class().get_name() if comp else None)
    if comp:
        print("   cap/count/follower members:",
              members(comp, ("limit", "max", "count", "follower", "num", "active", "pet", "mount", "thrall")))

# Any global server setting for follower limit?
print("\n== scan loaded classes for follower-limit settings ==")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
for name in ("ConanGameState", "ConanPlayerState", "FollowerComponent",
             "ThrallSystemComponent", "FormationFollowerComponent"):
    if hasattr(unreal, name):
        cdo = unreal.get_default_object(getattr(unreal, name))
        m = members(cdo, ("limit", "max", "follower", "pet", "mount"))
        if m:
            print(name, ":", m[:25])
