"""Summon a horse + a humanoid NPC into the LIVE game world via the engine
`Summon` console command (proper game-world spawn). No user interaction needed.

    python ue_run.py dev/summon_actors.py
"""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_game_world()
if not world:
    print("!! no game world"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
print("world:", world.get_path_name(), "pc:", pc.get_name() if pc else None)

# Pick a humanoid fighter NPC class path from the registry (stable, spawnable).
ar = unreal.AssetRegistryHelpers.get_asset_registry()
bps = ar.get_assets_by_path("/Game/Characters/NPCs/Humanoid", recursive=True, include_only_on_disk_assets=True)
humanoid = None
for a in bps:
    n = str(a.asset_name)
    nl = n.lower()
    if nl.startswith("bp_npc") and not any(k in nl for k in ("weapon", "dialogue", "cinematic", "companion", "boss")):
        humanoid = str(a.package_name) + "." + n + "_C"
        break
print("humanoid rider class:", humanoid)

HORSE = "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse_C"

before = set(a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter))

for path in [HORSE, humanoid]:
    if not path:
        continue
    cmd = "Summon " + path
    unreal.SystemLibrary.execute_console_command(world, cmd, pc)
    print("executed:", cmd)

after = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
print("ConanCharacters now:", len(after))
for a in after:
    if a.get_name() not in before:
        print("  NEW:", a.get_name(), "class=", a.get_class().get_name())
