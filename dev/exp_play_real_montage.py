import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
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
    real = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")  # now on Fullbody3rd
    # PlayAnimMontage on the CHARACTER replicates via ACharacter montage replication
    print("play_anim_montage ->", call(hum, "play_anim_montage", real, 0.15, ""))  # ~27s
    print(">> SEATED full-body on BOTH screens now? (real montage = should replicate)")
