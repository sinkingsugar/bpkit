import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
print("tsc:", tsc.get_class().get_name() if tsc else None)

# group counts + total
try:
    print("get_follower_group_counts ->", tsc.get_follower_group_counts())
except Exception as e:
    print("group_counts err:", str(e).splitlines()[-1][:80])
try:
    print("get_num_following_thralls ->", tsc.get_num_following_thralls())
except Exception as e:
    print("num err:", str(e).splitlines()[-1][:80])
try:
    chars = tsc.get_following_thrall_characters()
    print("following chars:", [(c.get_class().get_name(),
           c.get_editor_property("is_pet"), c.get_editor_property("is_mount") if "is_mount" in dir(c) else "?")
           for c in chars])
except Exception as e:
    print("chars err:", str(e).splitlines()[-1][:80])

# the moddable knobs' signatures
for m in ("add_thrall_group_limit_adjustment", "is_below_thrall_limit",
          "get_number_following_thralls_in_group", "can_thrall_start_following"):
    f = getattr(tsc, m, None)
    print("\n%s:" % m, (f.__doc__ or "?").split("\n\n")[0] if f else "MISSING")
