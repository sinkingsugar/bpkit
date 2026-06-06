import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:45]
def rd(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR"
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    anim = mesh.get_anim_instance()
    idle = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_BLUEPRINT)
    r = call(anim, "play_slot_animation_as_dynamic_montage", idle, "Fullbody3rd", 0.1, 0.1, 0.2, 10)
    print("played:", r)
    print("is_any_montage_playing:", call(anim, "is_any_montage_playing"))
    print("get_current_active_montage:", call(anim, "get_current_active_montage"))
    print("montage_is_playing(r):", call(anim, "montage_is_playing", r) if r and "ERR" not in str(r) else "?")
    print("--- mesh tick/visibility ---")
    print("mesh class:", mesh.get_class().get_name())
    print("visible:", call(mesh, "is_visible"), "| tick_enabled:", call(mesh, "is_component_tick_enabled"))
    print("VisibilityBasedAnimTickOption:", rd(mesh, "visibility_based_anim_tick_option"))
    print("comp significance/budget props:", [p for p in dir(mesh) if any(k in p.lower() for k in ("significance","budget","tick_pose","update_rate"))][:8])
