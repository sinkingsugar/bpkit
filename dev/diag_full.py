import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]
def rd(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR"
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if not hum:
    print("no humanoid"); raise SystemExit
print("humanoid:", hum.get_name(), "class:", hum.get_class().get_name())
par = hum.get_attach_parent_actor()
print("attach_parent:", par.get_name() if par else "DETACHED")
print("location:", hum.get_actor_location())
print("velocity:", call(hum, "get_velocity"))
cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
print("movement_mode:", rd(cm, "movement_mode") if cm else "?")
mesh = hum.get_editor_property("Mesh")
print("anim_mode:", call(mesh, "get_animation_mode"))
print("is_playing_montage:", call(hum, "is_playing_root_motion") if hasattr(hum, "is_playing_root_motion") else "?",
      "| current_montage:", call(hum, "get_current_montage"))
ai = call(hum, "get_controller")
print("AI:", ai.get_class().get_name() if ai and "ERR" not in str(ai) else ai)
print("  is_following:", rd(ai, "is_following") if ai and "ERR" not in str(ai) else "?")
# brain / behavior tree
brain = call(ai, "get_brain_component") if ai and "ERR" not in str(ai) else None
print("  brain:", brain.get_class().get_name() if brain and "ERR" not in str(brain) else brain)
# what anim is on the mesh right now (active montages on the anim instance)
ai2 = call(mesh, "get_anim_instance")
if ai2 and "ERR" not in str(ai2):
    print("  anim_instance:", ai2.get_class().get_name())
    print("  is_any_montage_playing:", call(ai2, "is_any_montage_playing"))
