"""One-shot: summon a rider, attach it to the horse's back, disable its AI/movement
(without killing it). Re-finds the horse by class. Approach-C core demo."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)

# Find the horse by class
horse = None
for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    cn = c.get_class().get_name().lower()
    if "mounts_horse" in cn or "horse" in cn:
        horse = c; break
print("horse:", horse.get_name() if horse else None)
if not horse:
    print("!! no horse"); raise SystemExit
horse.tags = ["TEST_HORSE"]

# Summon a fresh rider and grab it
RIDER = "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall_C"
before = {a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)}
unreal.SystemLibrary.execute_console_command(world, "Summon " + RIDER, pc)
rider = None
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
    if a.get_name() not in before:
        rider = a; break
print("rider:", rider.get_name() if rider else None)
if not rider:
    print("!! summon failed"); raise SystemExit
rider.tags = ["TEST_RIDER"]

# Attach to horse back
mesh = horse.get_editor_property("mesh")
sockets = [str(s) for s in mesh.get_all_socket_names()]
print("horse sockets:", sockets[:30])
socket = ""
for kw in ("saddle", "seat", "rider", "spine_03", "spine_02", "spine", "pelvis"):
    for s in sockets:
        if kw in s.lower():
            socket = s; break
    if socket: break
if not socket:
    for b in ("spine_03", "spine_02", "pelvis", "Bip01Spine1", "Bip01_Spine2"):
        if mesh.does_socket_exist(b):
            socket = b; break
print("attach socket/bone:", repr(socket))

rider.attach_to_component(mesh, socket,
    unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
    unreal.AttachmentRule.KEEP_WORLD, False)
if not socket:
    rider.set_actor_relative_location(unreal.Vector(-10, 0, 120), False, False)
print("attach parent:", rider.get_attach_parent_actor())

# Disable AI brain + movement + collision (NOT destroy)
ctrl = rider.get_controller()
if not ctrl:
    unreal.load_object(None, "/Game/Systems/AI/NewAI/HumanAIController.HumanAIController_C")
    b2 = {c.get_name() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController)}
    unreal.SystemLibrary.execute_console_command(world, "Summon /Game/Systems/AI/NewAI/HumanAIController.HumanAIController_C", pc)
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.AIController):
        if c.get_name() not in b2:
            c.possess(rider); break
    ctrl = rider.get_controller()
print("rider ctrl:", ctrl.get_class().get_name() if ctrl else None)
if isinstance(ctrl, unreal.AIController):
    bc = ctrl.get_editor_property("brain_component")
    if bc:
        bc.stop_logic("stowed_on_mount"); print("brain logic stopped")
mc = rider.get_editor_property("character_movement")
try:
    mc.set_movement_mode(unreal.MovementMode.MOVE_NONE); print("movement -> NONE")
except Exception as e:
    print("move err:", e)
rider.set_actor_enable_collision(False)
print("collision off; rider loc:", rider.get_actor_location(), "horse loc:", horse.get_actor_location())
print("DONE — rider welded to horse back, AI/movement disabled, still alive.")
