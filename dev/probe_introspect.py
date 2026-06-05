import unreal

for path in [
    "/Game/Characters/MountFunctionLibrary.MountFunctionLibrary",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse",
]:
    print("\n=== ", path)
    bp = unreal.load_asset(path)
    print("  type:", type(bp).__name__, "  class:", bp.get_class().get_name() if bp else None)
    # what editor properties exist?
    for prop in ["parent_class", "ParentClass", "generated_class", "GeneratedClass",
                 "blueprint_type", "geneated_class"]:
        try:
            v = bp.get_editor_property(prop)
            print("   prop %-16s = %s" % (prop, v))
        except Exception as e:
            print("   prop %-16s ERR %s" % (prop, str(e)[:60]))
    # The class object itself:
    cls = bp.get_class()
    print("  asset class parents:", end=" ")
    c = cls
    n = 0
    out = []
    while c and n < 10:
        out.append(c.get_name())
        c = c.get_super_class()
        n += 1
    print(" -> ".join(out))
