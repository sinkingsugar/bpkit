import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
# the humanoid currently actor-attached to a horse
hum = None
for f in tsc.get_following_thrall_characters():
    if (not f.is_mountable()) and f.get_attach_parent_actor() is not None:
        hum = f; break
print("attached humanoid:", hum.get_name() if hum else None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    anim = unreal.load_object(None, "/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")
    print("anim:", anim.get_name() if anim else None)
    mesh.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    call(mesh, "play_animation", anim, True)
    # seated bodies sit lower than the +90 standing offset; drop it a bit
    hum.set_actor_relative_location(unreal.Vector(0, 0, 20), False, False)
    print(">> CHECK CLIENT: does the follower now SIT (mounted idle pose) instead of standing?")
