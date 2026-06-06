import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:50]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()
hum = next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()), None)
if hum:
    mesh = hum.get_editor_property("Mesh")
    for path in ("/Game/Systems/Mounts_v2/AB_Mount_Master.AB_Mount_Master",):
        abp = unreal.load_object(None, path)
        cls = abp.generated_class() if abp else None
        print("layer class:", cls.get_name() if cls else None)
        print("  target skeleton:", abp.get_editor_property("target_skeleton").get_name() if abp and abp.get_editor_property("target_skeleton") else "?")
        if cls:
            print("  link_anim_class_layers:", call(mesh, "link_anim_class_layers", cls))
            inst = call(mesh, "get_linked_anim_layer_instance_by_class", cls)
            print("  linked instance:", inst.get_class().get_name() if inst and "ERR" not in str(inst) else inst)
    print(">> is the follower now in a SEATED/mounted pose (even standing on ground)? on BOTH screens?")
