import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters()
            if (not f.is_mountable()) and f.get_attach_parent_actor() is not None), None)
print("attached humanoid:", hum.get_name() if hum else None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    # montages play through the AnimBP, so restore AnimBlueprint mode (single-node won't run montages)
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mtg = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/AM_human_mounted_movement_HORSE.AM_human_mounted_movement_HORSE")
    print("montage:", mtg.get_name() if mtg else None)
    # ACharacter.PlayAnimMontage replicates via the character's montage replication
    print("play_anim_montage ->", call(hum, "play_anim_montage", mtg, 1.0, ""))
    print(">> CHECK CLIENT: does the follower now show a MOUNTED pose (seated-ish) instead of standing?")
