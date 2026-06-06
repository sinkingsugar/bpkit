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
    ai = call(hum, "get_controller")
    print("stop_emote:", call(ai, "stop_emote"))
    brain = ai.get_editor_property("brain_component") if ai and "ERR" not in str(ai) else None
    print("brain:", brain.get_class().get_name() if brain else None)
    if brain:
        print("brain.stop_logic:", call(brain, "stop_logic", "stowed"))
    cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
    if cm:
        call(cm, "stop_movement_immediately")
        call(cm, "set_movement_mode", unreal.MovementMode.MOVE_NONE, 0)
    hum.set_actor_enable_collision(False)
    R = unreal.AttachmentRule.SNAP_TO_TARGET
    call(hum, "attach_to_component", horse.get_editor_property("Mesh"), "attachrider", R, R, R, False)
    hum.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
    mesh = hum.get_editor_property("Mesh")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mtg = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
    call(hum, "play_anim_montage", mtg, 1.0, "")
    print("loc:", hum.get_actor_location(), "| vel:", call(hum, "get_velocity"))
    print(">> watch several seconds: stable + seated now?")
