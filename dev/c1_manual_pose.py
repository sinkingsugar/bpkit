"""Apply the exact §8 manual sequence on the stowed dancer: unpossess (kill AI so it
can't re-assert AnimBP) -> single-node -> play mounted idle. Then user eyeballs."""
import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def find(cn):
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if cn in a.get_class().get_name(): return a
def tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
mgr, rider = find("BP_MF_Recipe"), tag("TEST_RIDER")
rmesh = rider.get_editor_property("mesh")
anim = mgr.get_editor_property("MountIdleAnim")

# ensure stowed (attached) first
mgr.call_method("Stow")

# 1) stop the AI brain so it can't re-drive animation
ctrl = rider.get_controller()
print("controller:", ctrl.get_class().get_name() if ctrl else None)
if ctrl:
    bc = ctrl.get_editor_property("brain_component")
    if bc:
        try: bc.stop_logic("stow"); print("brain stopped")
        except Exception as e: print("brain err:", str(e).splitlines()[-1][:60])

# 2) stop montages, force single-node, play
ai = rmesh.get_anim_instance()
if ai and hasattr(ai, "stop_all_montages"):
    try: ai.stop_all_montages(0.0)
    except Exception: pass
rmesh.set_component_tick_enabled(True)
rmesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
rmesh.play_animation(anim, True)
print("played:", anim.get_name())
ad = rmesh.get_editor_property("animation_data")
print("anim_to_play now:", ad.get_editor_property("anim_to_play"))
print(">>> LOOK at the dancer now — is she SEATED in a riding pose (not A-pose)?")
