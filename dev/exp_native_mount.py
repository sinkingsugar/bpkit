import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:70]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
horse=next((f for f in tsc.get_following_thrall_characters() if f.is_mountable() and not f.get_rider()),None)
print("follower:", hum.get_name() if hum else None, "| free horse:", horse.get_name() if horse else None)
if hum and horse:
    # clean slate: undo any manual cosmetic attach
    call(hum, "k2_detach_from_actor", unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
    print("can_mount(horse):", call(hum, "can_mount", horse))
    print("closest_mounting_spot:", call(hum, "get_closest_mounting_spot", horse))
    # try the server mount -- arg signature unknown, try a few
    for args in ((horse,), (horse, 0), ()):
        r = call(hum, "bp_mount_server", *args)
        print("bp_mount_server%s -> %s" % (args, r))
        if "ERR" not in str(r):
            break
    print("AFTER: hum.get_mount:", call(hum,"get_mount"), "| horse.get_rider:", call(horse,"get_rider"))
    print(">> is the follower NATIVELY mounted/seated on the horse, on BOTH screens?")
