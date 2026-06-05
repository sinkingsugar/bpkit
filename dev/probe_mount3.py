"""Structural probe of the mount system + follower/thrall classes.

For each target: load it, print parent-class chain (to find the native C++ base),
its components, and its function/variable surface. This tells us where the
mount logic actually lives (native vs BP) and what API exists.

    python ue_run.py dev/probe_mount3.py
"""
import unreal


def parent_chain(cls):
    chain = []
    c = cls
    seen = 0
    while c and seen < 40:
        chain.append(c.get_name())
        c = c.get_super_class()
        seen += 1
    return chain


def dump_class(path, max_fns=60, max_vars=60):
    print("\n" + "=" * 70)
    print("TARGET:", path)
    obj = unreal.load_object(None, path)
    if obj is None:
        # try as asset (Blueprint) then get generated class
        asset = unreal.load_asset(path)
        print("  load_asset ->", asset)
        if asset and hasattr(asset, "generated_class"):
            cls = asset.generated_class()
        else:
            cls = None
    else:
        cls = obj if isinstance(obj, unreal.Class) else obj.get_class()
    if cls is None:
        # maybe path is a blueprint asset
        bp = unreal.load_asset(path)
        if bp:
            try:
                cls = bp.generated_class()
            except Exception as e:
                print("  no generated_class:", e)
    if cls is None:
        print("  !! could not resolve class")
        return
    print("  class:", cls.get_name())
    print("  parents:", " -> ".join(parent_chain(cls)))
    # Functions
    try:
        fns = unreal.get_type_from_class(cls) if hasattr(unreal, "get_type_from_class") else None
    except Exception:
        fns = None
    # Use the editor function library to list functions/properties via reflection
    try:
        fnames = [f for f in dir(cls)]
    except Exception:
        fnames = []
    # Better: enumerate FProperties + UFunctions through the class default object
    cdo = unreal.get_default_object(cls) if hasattr(unreal, "get_default_object") else None
    print("  CDO:", cdo)


# Native-class discovery: walk the parent chain of a mount BP to find the C++ base + module.
print("###### MOUNT SYSTEM ######")
for p in [
    "/Game/Characters/MountFunctionLibrary.MountFunctionLibrary",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse",
]:
    dump_class(p)

print("\n###### FOLLOWER / THRALL / PET ######")
for p in [
    "/Game/Characters/NPCs/Bear/Blueprints/BP_NPC_Wildlife_Bear_Brown_pet.BP_NPC_Wildlife_Bear_Brown_pet",
    "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall",
]:
    dump_class(p)
