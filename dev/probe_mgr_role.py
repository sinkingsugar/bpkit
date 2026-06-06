import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
cls = unreal.load_object(None, "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager_C")
mgrs = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
for m in mgrs:
    print("manager:", m.get_name())
    print("  local_role :", m.get_local_role())     # AUTHORITY on server
    print("  REMOTE_role:", m.get_remote_role())     # SimulatedProxy => a CLIENT instance exists; None => server-only
    print("  actor_tick_enabled:", m.is_actor_tick_enabled())
    print("  net_mode(world):", unreal.SystemLibrary.get_net_mode(m) if hasattr(unreal.SystemLibrary,"get_net_mode") else "?")
