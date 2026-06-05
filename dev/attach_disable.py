"""Approach-C core test: attach the AI rider to the horse + disable its AI/movement
(without destroying it). Cosmetic 'mounted follower'.

    python ue_run.py dev/attach_disable.py
"""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE"); rider = by_tag("TEST_RIDER")
print("horse:", horse.get_name() if horse else None, "rider:", rider.get_name() if rider else None)
if not (horse and rider):
    print("!! missing actors"); raise SystemExit

# Horse skeletal mesh (Character.Mesh)
mesh = horse.get_editor_property("mesh")
print("horse mesh:", mesh.get_name() if mesh else None)
sockets = [str(s) for s in mesh.get_all_socket_names()] if mesh else []
print("sockets (%d):" % len(sockets), sockets[:30])

# Pick a saddle/seat/rider socket; else a back/spine bone; else mesh origin + offset
def pick(names):
    for kw in ("saddle", "seat", "rider", "mount", "pelvis", "spine_03", "spine_02", "spine"):
        for s in names:
            if kw in s.lower():
                return s
    return ""
socket = pick(sockets)
# bone fallback (attach accepts bone names too)
if not socket and mesh:
    for b in ("spine_03", "spine_02", "spine_01", "pelvis", "Bip01_Spine2", "Bip01Spine1"):
        try:
            if mesh.does_socket_exist(b):
                socket = b; break
        except Exception:
            pass
print("chosen socket/bone:", repr(socket))

# Attach rider to the horse mesh
rider.attach_to_component(
    mesh, socket,
    unreal.AttachmentRule.SNAP_TO_TARGET,   # location
    unreal.AttachmentRule.SNAP_TO_TARGET,   # rotation
    unreal.AttachmentRule.KEEP_WORLD,       # scale
    False)
# Lift onto the back if we snapped to mesh origin (feet)
if not socket:
    rider.set_actor_relative_location(unreal.Vector(-10, 0, 120), False, False)
print("attached. rider attach parent:", rider.get_attach_parent_actor())

# --- Disable AI + movement (do NOT destroy / kill) ---
ctrl = rider.get_controller()
print("rider ctrl:", ctrl.get_class().get_name() if ctrl else None)
if isinstance(ctrl, unreal.AIController):
    bc = ctrl.get_editor_property("brain_component")
    try:
        if bc:
            bc.stop_logic("stowed_on_mount")
            print("stopped brain logic")
    except Exception as e:
        print("stop_logic err:", e)

mc = rider.get_editor_property("character_movement")
try:
    mc.set_movement_mode(unreal.MovementMode.MOVE_NONE)
    print("movement mode -> NONE")
except Exception as e:
    print("movement disable err:", e)

# Stop it being shoved / blocking; keep it alive
rider.set_actor_enable_collision(False)
print("collision disabled (cosmetic)")

# Confirm still alive
try:
    print("rider is in DBNO?:", rider.get_thrall_component().is_in_dbno_state() if rider.get_thrall_component() else "no thrall comp")
except Exception as e:
    print("dbno check:", e)
print("rider loc now:", rider.get_actor_location(), " horse loc:", horse.get_actor_location())
print("DONE — ride the horse around; the rider should move welded to it.")
