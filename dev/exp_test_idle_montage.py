import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE -- press Play"); raise SystemExit
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
fols = tsc.get_following_thrall_characters()
hum = next((f for f in fols if not f.is_mountable()), None)
horse = next((f for f in fols if f.is_mountable()), None)
print("humanoid:", hum.get_name() if hum else None, "| horse:", horse.get_name() if horse else None)
if hum and horse:
    R = unreal.AttachmentRule.SNAP_TO_TARGET
    hum.set_actor_enable_collision(False)
    cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
    if cm: call(cm, "disable_movement")
    call(hum, "attach_to_component", horse.get_editor_property("Mesh"), "attachrider", R, R, R, False)
    hum.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
    # play the created IDLE montage (replicating, full-body if the slot is right)
    mesh = hum.get_editor_property("Mesh")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mtg = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
    print("montage:", mtg.get_name() if mtg else None)
    print("play_anim_montage ->", call(hum, "play_anim_montage", mtg, 1.0, ""))
    print(">> CHECK: is %s now seated FULL-BODY on %s (legs too, not standing)? (and on the client)" % (
        hum.get_class().get_name(), horse.get_class().get_name()))
