import unreal

def cls_of(path):
    try:
        c = unreal.EditorAssetLibrary.load_blueprint_class(path)
        if c:
            return c
    except Exception as e:
        print("   load_blueprint_class err:", str(e)[:60])
    return unreal.load_object(None, path + "_C")

def show(path, props):
    print("\n=== CDO:", path)
    c = cls_of(path)
    if not c:
        print("   !! no class"); return
    cdo = unreal.get_default_object(c)
    for p in props:
        try:
            v = cdo.get_editor_property(p)
            print("   %-30s = %s" % (p, v))
        except Exception as e:
            print("   %-30s ERR %s" % (p, str(e)[:45]))

COMMON = ["ai_controller_class", "auto_possess_ai", "is_mountable", "is_pet", "is_thrall", "is_companion"]
show("/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse", COMMON)
show("/Game/Characters/NPCs/Bear/Blueprints/BP_NPC_Wildlife_Bear_Brown_pet", COMMON)
show("/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall", COMMON)
