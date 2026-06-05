"""Summon a FRESH manager from the freshly-compiled class (bypassing the framework's
cached auto-spawn). If this one runs the ForEach loop, no editor restart needed."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
MGR = "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager_C"
existing = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if "MountedFollowerManager" in a.get_class().get_name()]
print("existing managers:", [a.get_name() for a in existing])
unreal.load_object(None, MGR)
unreal.SystemLibrary.execute_console_command(world, "Summon " + MGR, pc)
print("summoned a fresh manager from the current compiled class.")
print("mount a horse and watch for 'STOW A FOLLOWER' (it'll co-exist with the stale one's logs)")
