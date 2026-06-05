import unreal, os
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
mgr = next((a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if "MountedFollowerManager" in a.get_class().get_name()), None)
print("manager:", mgr.get_name() if mgr else None)
if mgr:
    print("  Initialized:", mgr.get_editor_property("Initialized"),
          "| WasMounted:", mgr.get_editor_property("WasMounted"))
print("player mounted now:", pawn.get_mount() is not None)
tsc = pawn.get_thrall_system_component()
chars = tsc.get_following_thrall_characters()
print("following (count %d):" % len(chars),
      [(c.get_class().get_name()[:24], c.get_editor_property("is_mount")) for c in chars])

# recent manager log lines
ld = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
with open(os.path.join(ld, "ConanSandbox.log"), "r", errors="ignore") as f:
    lines = f.readlines()
mgr_lines = [l.rstrip() for l in lines[-3000:]
             if "MountedFollowerManager" in l and "LogBlueprintUserMessages" in l]
print("\nlast manager print lines:")
for l in mgr_lines[-8:]:
    print("  ", l.split("]")[-1].strip(), "@", l[1:18])
