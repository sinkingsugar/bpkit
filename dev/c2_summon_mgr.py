"""Summon the mounted-follower manager into PIE (its BeginPlay raises the Mount cap)."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
if not pc:
    print("!! no player (PIE not ready)"); raise SystemExit
MGR = "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager_C"
# already present?
existing = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if "MountedFollowerManager" in a.get_class().get_name()]
if existing:
    print("manager already present:", existing[0].get_name()); raise SystemExit
unreal.load_object(None, MGR)
unreal.SystemLibrary.execute_console_command(world, "Summon " + MGR, pc)
print("summoned manager (BeginPlay raises Mount cap). give it a frame.")
