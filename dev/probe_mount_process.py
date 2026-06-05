import unreal
cc = unreal.ConanCharacter
for fn in ["bp_start_mount_process_client","uncrouch_before_try_mount","mount_after_uncrouch",
           "bp_pre_mount_server_client","bp_mount_server","replicate_mount","get_closest_mounting_spot"]:
    f = getattr(cc, fn, None)
    print("== %s ==" % fn)
    print("  ", ((f.__doc__ or "").strip().split("\n")[0]) if f else "MISSING")
# Player pawn: any try/request/interact mount entry?
import unreal as u
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
player = u.GameplayStatics.get_player_pawn(world, 0)
print("\nplayer mount/try/interact/request methods:")
for m in sorted(dir(player)):
    if any(k in m.lower() for k in ("mount","try_mount","interact","request_mount","start_mount")):
        print("  ", m)
