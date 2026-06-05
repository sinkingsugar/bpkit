import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
player = unreal.GameplayStatics.get_player_pawn(world, 0)
pc = unreal.GameplayStatics.get_player_controller(world, 0)

# 1) Saddle assets / item BPs
ar = unreal.AssetRegistryHelpers.get_asset_registry()
print("=== assets matching 'saddle' ===")
all_assets = ar.get_assets_by_path("/Game", recursive=True, include_only_on_disk_assets=True)
n = 0
for a in all_assets:
    nm = str(a.asset_name)
    if "saddle" in nm.lower():
        print("  ", a.package_name, nm, "| class", str(a.asset_class_path.asset_name))
        n += 1
        if n > 40:
            print("   ..."); break

# 2) Player inventory + add-item BlueprintCallable surface
print("\n=== player pawn inventory/add/give/equip methods ===")
for m in sorted(dir(player)):
    if any(k in m.lower() for k in ("inventory", "add_item", "give", "equip", "additem", "loot")):
        print("  ", m)

# 3) ConanCheatManager item-related methods
print("\n=== ConanCheatManager item/give methods ===")
for m in sorted(dir(unreal.ConanCheatManager)):
    if any(k in m.lower() for k in ("item", "give", "spawn", "loot", "equip", "inventory")):
        print("  ", m)

# 4) Any item-template / inventory function library?
print("\n=== unreal.* item/inventory libraries ===")
for nm in dir(unreal):
    low = nm.lower()
    if ("item" in low or "inventory" in low) and any(low.endswith(s) for s in ("library","functionlibrary","statics","helper")):
        print("  ", nm)
