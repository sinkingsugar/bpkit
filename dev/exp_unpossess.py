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
    # list AI stop/pause/disable methods for reference
    print("AI stop-ish methods:", [m for m in dir(ai) if any(k in m.lower() for k in
          ("stop","pause","disable","unposses","deactiv","logic","brain"))][:15] if ai and "ERR" not in str(ai) else ai)
    # HAMMER: set movement mode None, stop the AI from moving the pawn
    cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
    if cm:
        call(cm, "set_movement_mode", unreal.MovementMode.MOVE_NONE, 0)
        call(cm, "set_comp_velocity" if False else "stop_movement_immediately")
    call(ai, "stop_movement")
    if ai and "ERR" not in str(ai):
        try: ai.unpossess()
        except Exception as e: print("unpossess ERR:", e)
    hum.set_actor_enable_collision(False)
    R = unreal.AttachmentRule.SNAP_TO_TARGET
    call(hum, "attach_to_component", horse.get_editor_property("Mesh"), "attachrider", R, R, R, False)
    hum.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
    mesh = hum.get_editor_property("Mesh")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    mtg = unreal.load_object(None, "/Game/_Scratch/AM_MF_idle_HORSE.AM_MF_idle_HORSE")
    call(hum, "play_anim_montage", mtg, 1.0, "")
    print("loc:", hum.get_actor_location(), "| vel:", call(hum, "get_velocity"))
    print(">> watch a few seconds: stable on the horse now? seated?")
