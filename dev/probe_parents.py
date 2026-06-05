"""Load key BPs, walk parent-class chain to the native C++ base, list members.

    python ue_run.py dev/probe_parents.py
"""
import unreal


def chain(cls):
    out = []
    c = cls
    n = 0
    while c and n < 50:
        nm = c.get_name()
        pkg = c.get_outer().get_name() if c.get_outer() else "?"
        out.append("%s(%s)" % (nm, pkg))
        c = c.get_super_class()
        n += 1
    return out


def dump_bp(path):
    print("\n" + "=" * 72)
    print("BP:", path)
    bp = unreal.load_asset(path)
    if not bp:
        print("  !! load failed")
        return None
    try:
        gen = bp.get_editor_property("generated_class")
    except Exception:
        gen = None
    try:
        par = bp.get_editor_property("parent_class")
    except Exception:
        par = None
    print("  parent_class   :", par.get_name() if par else None)
    print("  generated_class:", gen.get_name() if gen else None)
    cls = gen or par
    if cls:
        print("  CHAIN:")
        for c in chain(cls):
            print("     ", c)
    return cls


TARGETS = [
    "/Game/Characters/MountFunctionLibrary.MountFunctionLibrary",
    "/Game/Characters/NPCs/Hooved_Wild/Blueprints/BP_NPC_Mounts_Horse.BP_NPC_Mounts_Horse",
    "/Game/Characters/NPCs/Bear/Blueprints/BP_NPC_Wildlife_Bear_Brown_pet.BP_NPC_Wildlife_Bear_Brown_pet",
    "/Game/Characters/NPCs/Necromancy_followers/Blueprints/BP_FiniteLifespanUndeadThrall.BP_FiniteLifespanUndeadThrall",
]
classes = {}
for t in TARGETS:
    classes[t] = dump_bp(t)

# Find the player pawn class + any native mount/saddle/thrall classes by scanning
# the parent chains we just discovered.
print("\n\n###### Searching loaded native classes for mount/thrall/saddle/rider ######")
# Enumerate all loaded UClass objects via the engine's object iterator proxy.
kw = ["mount", "saddle", "ride", "rider", "rein", "thrall", "follow", "tame", "pet", "horse"]
found = set()
# Walk the package /Script/* native classes we can reach from known bases.
bases = [c for c in classes.values() if c]
for b in bases:
    c = b
    while c:
        nm = c.get_name().lower()
        if any(k in nm for k in kw):
            found.add(c.get_name() + "  <" + (c.get_outer().get_name() if c.get_outer() else "?") + ">")
        c = c.get_super_class()
for f in sorted(found):
    print("  ", f)
