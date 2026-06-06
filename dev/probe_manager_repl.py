import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:40]
def rd(o,n):
    try: return o.get_editor_property(n)
    except Exception: return "?"
cls = unreal.load_object(None, "/Game/_Scratch/BP_MountedFollowerManager.BP_MountedFollowerManager_C")
mgrs = unreal.GameplayStatics.get_all_actors_of_class(world, cls)
print("manager instances (server world):", [m.get_name() for m in mgrs])
for m in mgrs:
    print("  has_authority:", call(m,"has_authority"),
          "| replicates:", rd(m,"replicates"),
          "| net_load_on_client:", rd(m,"net_load_on_client"),
          "| only_relevant_to_owner:", rd(m,"only_relevant_to_owner"),
          "| net_dormancy:", rd(m,"net_dormancy"))
    print("  MgrVersion:", rd(m,"MgrVersion"))
