import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]

pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
fols = tsc.get_following_thrall_characters()
hum = next((f for f in fols if not f.is_mountable()), None)
horse = next((f for f in fols if f.is_mountable()), None)
print("humanoid:", hum.get_name() if hum else None, "| horse:", horse.get_name() if horse else None)

if hum and horse:
    R = unreal.AttachmentRule.SNAP_TO_TARGET
    horse_mesh = horse.get_editor_property("Mesh")
    # freeze it so the AI doesn't walk it off, then ACTOR-attach the whole follower to the saddle
    hum.set_actor_enable_collision(False)
    cm = hum.get_character_movement() if hasattr(hum, "get_character_movement") else None
    if cm: call(cm, "disable_movement")
    print("actor attach_to_component ->", call(hum, "attach_to_component", horse_mesh, "attachrider", R, R, R, False))
    hum.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
    par = hum.get_attach_parent_actor()
    print("attach parent (actor):", par.get_name() if par else None, "| hum loc:", hum.get_actor_location())
    print("\n>> CHECK THE CLIENT WINDOW: does the joined player see %s on %s, riding along when the horse moves?" % (
        hum.get_class().get_name(), horse.get_class().get_name()))
