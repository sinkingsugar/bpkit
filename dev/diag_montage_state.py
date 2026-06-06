import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    par = hum.get_attach_parent_actor()
    cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
    print("humanoid:", hum.get_name())
    print("  attach_parent:", par.get_name() if par else "** DETACHED **")
    print("  movement_mode:", call(cm, "get_movement_mode") if cm else "?")
    print("  location:", hum.get_actor_location())
    mesh = hum.get_editor_property("Mesh")
    print("  anim_mode:", call(mesh, "get_animation_mode"))
    ai = hum.get_controller() if hasattr(hum, "get_controller") else None
    print("  AI controller:", ai.get_class().get_name() if ai else None)
    # is the montage still playing?
    print("  current montage:", call(hum, "get_current_montage"))
