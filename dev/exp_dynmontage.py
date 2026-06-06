import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:45]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
horse = next((f for f in tsc.get_following_thrall_characters() if f.is_mountable()), None)
if hum and horse:
    ai = call(hum, "get_controller"); call(ai, "stop_emote")
    brain = ai.get_editor_property("brain_component") if ai and "ERR" not in str(ai) else None
    if brain: call(brain, "stop_logic", "stowed")
    cm = hum.get_component_by_class(unreal.CharacterMovementComponent)
    if cm: call(cm, "disable_movement")
    hum.set_actor_enable_collision(False)
    R = unreal.AttachmentRule.SNAP_TO_TARGET
    call(hum, "attach_to_component", horse.get_editor_property("Mesh"), "attachrider", R, R, R, False)
    hum.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
    mesh = hum.get_editor_property("Mesh")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    anim = mesh.get_anim_instance()
    # play the sequence directly on DefaultSlot, looping (loop_count 0 = infinite)
    r = call(anim, "play_slot_animation_as_dynamic_montage", idle, "DefaultSlot", 0.2, 0.2, 1.0, 0)
    print("play_slot DefaultSlot ->", r)
    print(">> is the follower SEATED full-body now (looping), on BOTH screens? stable?")
