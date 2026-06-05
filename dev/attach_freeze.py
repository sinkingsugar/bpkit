"""Re-attach the rider to the 'attachrider' socket and FULLY freeze it so it can't
push the horse: kill collision + physics on capsule & mesh, stop & disable the
movement component, disable tick, unpossess. Non-destructive (no kill)."""
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
rider = by_tag("TEST_RIDER")
horse = by_tag("TEST_HORSE")
if not horse:
    for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter):
        if "horse" in c.get_class().get_name().lower():
            horse = c; horse.tags = ["TEST_HORSE"]; break
print("horse:", horse.get_name() if horse else None, "rider:", rider.get_name() if rider else None)
if not (horse and rider):
    print("!! missing"); raise SystemExit

NONE_COLL = unreal.CollisionEnabled.NO_COLLISION

# 1) Unpossess so the AI can't issue movement
ctrl = rider.get_controller()
if ctrl:
    try:
        ctrl.unpossess(); print("unpossessed (was", ctrl.get_class().get_name(), ")")
    except Exception as e:
        print("unpossess err:", e)

# 2) Kill collision + physics on every primitive component
caps = rider.get_editor_property("capsule_component")
mesh = rider.get_editor_property("mesh")
for comp, nm in ((caps, "capsule"), (mesh, "mesh")):
    if not comp:
        continue
    try: comp.set_collision_enabled(NONE_COLL)
    except Exception as e: print(nm, "coll err:", e)
    try: comp.set_simulate_physics(False)
    except Exception as e: print(nm, "phys err:", e)
    try: comp.set_component_tick_enabled(False)
    except Exception: pass
try:
    mesh.set_all_bodies_simulate_physics(False)
    mesh.put_all_rigid_bodies_to_sleep()
    print("mesh bodies -> no physics, asleep")
except Exception as e:
    print("mesh bodies err:", e)
rider.set_actor_enable_collision(False)

# 3) Stop + disable the movement component
mc = rider.get_editor_property("character_movement")
try:
    mc.stop_movement_immediately()
    mc.disable_movement()
    mc.set_component_tick_enabled(False)
    mc.set_active(False, False)
    print("movement stopped + disabled + tick off")
except Exception as e:
    print("movement err:", e)

# 4) Disable the actor's own tick
rider.set_actor_tick_enabled(False)

# 5) Re-attach to the dedicated rider socket
horse_mesh = horse.get_editor_property("mesh")
socket = "attachrider" if horse_mesh.does_socket_exist("attachrider") else "saddleSocket"
rider.detach_from_actor(unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD, unreal.DetachmentRule.KEEP_WORLD)
rider.attach_to_component(horse_mesh, socket,
    unreal.AttachmentRule.SNAP_TO_TARGET, unreal.AttachmentRule.SNAP_TO_TARGET,
    unreal.AttachmentRule.KEEP_WORLD, False)
print("re-attached to socket:", socket, "| parent:", rider.get_attach_parent_actor())
print("rider loc:", rider.get_actor_location(), "horse loc:", horse.get_actor_location())
print("DONE — rider frozen + welded to 'attachrider'. Horse should move freely now.")
