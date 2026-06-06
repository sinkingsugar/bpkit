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
    mesh = hum.get_editor_property("Mesh"); anim = mesh.get_anim_instance()
    idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    for s in ("DefaultGroup", "Body", "Locomotion", "MountedSlot"):
        call(anim, "stop_slot_animation", 0.0, s)
    r = call(anim, "play_slot_animation_as_dynamic_montage", idle, "Body", 0.25, 0.25, 1.0, 0)
    print("play on Body slot (looping) ->", r)
    print("is_slot_active('Mounted'):", call(anim, "is_slot_active", "Body"))
    print(">> SEATED full-body now on BOTH screens? stable + looping?")
