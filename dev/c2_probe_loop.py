"""Check the data paths for Step C: can I get pre-split arrays (horses vs followers)
without filtering loops? + array/util fn availability."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

print("group counts:", tsc.get_follower_group_counts())
print("\nget_following_thralls_of_group sig:",
      (tsc.get_following_thralls_of_group.__doc__ or "?").split("\n\n")[0])
print("get_following_thrall_characters sig:",
      (tsc.get_following_thrall_characters.__doc__ or "?").split("\n\n")[0])

# what do they actually return for Mount vs a combat group?
try:
    mounts = tsc.get_following_thralls_of_group("Mount")
    print("\nMount group ->", [type(x).__name__ for x in mounts], [getattr(x,'get_name',lambda:'?')() for x in mounts])
except Exception as e:
    print("mount group err:", str(e).splitlines()[-1][:80])
try:
    chars = tsc.get_following_thrall_characters()
    print("all chars ->", [(c.get_class().get_name(), c.is_mount()) for c in chars])
except Exception as e:
    print("chars err:", str(e).splitlines()[-1][:80])

print("\nis_mount on ConanCharacter:", hasattr(unreal.ConanCharacter, "is_mount"))
print("KismetMathLibrary.vector_distance:", hasattr(unreal.KismetMathLibrary, "vector_distance"))
print("SpawnActorFromClass on GameplayStatics:", hasattr(unreal.GameplayStatics, "begin_deferred_actor_spawn_from_class") or hasattr(unreal.GameplayStatics, "finish_spawning_actor"))
