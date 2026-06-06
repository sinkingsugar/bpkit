import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:50]
pc=unreal.GameplayStatics.get_player_controller(world,0); host=pc.get_controlled_pawn()
tsc=host.get_thrall_system_component()
hum=next((f for f in tsc.get_following_thrall_characters() if not f.is_mountable()),None)
# rider's components -- a mount/input component with a trigger?
print("RIDER components:")
for c in hum.get_components_by_class(unreal.ActorComponent):
    cn=c.get_class().get_name()
    if any(k in cn.lower() for k in ("mount","input","ride","interact")):
        print("  ", cn, "->", [m for m in dir(c) if any(k in m.lower() for k in ("mount","ride","try","request","start","seat")) and not m.startswith("_")][:14])
# BP_MountInput class methods
mi = unreal.load_object(None, "/Game/Systems/Mounts_v2/BP_MountInput.BP_MountInput_C")
print("\nBP_MountInput_C:", mi)
if mi:
    cdo = unreal.get_default_object(mi) if hasattr(unreal,"get_default_object") else None
    src = cdo or mi
    print("  mount-trigger methods:", [m for m in dir(src) if any(k in m.lower() for k in ("mount","try","request","start","ride")) and not m.startswith("_")][:20])
# how player mounts: is there an interaction / the GroupMovement? check player mount component
print("\nhost can_mount on self-found horse + is_mountable check; player get_rider:", call(host,"get_rider"))
