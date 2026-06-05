"""Enumerate the native ConanSandbox Python bindings for mount/follow/thrall API.

UE's PythonScriptPlugin generates glue for every reflected UCLASS/UFUNCTION/
UPROPERTY, so native Funcom classes likely appear under `unreal.*`. We scan the
whole `unreal` namespace + the key classes' members for the relevant keywords.

    python ue_run.py dev/probe_native_api.py
"""
import unreal

KW = ["mount", "saddle", "ride", "rider", "rein", "thrall", "follow",
      "tame", "pet", "passenger", "seat", "dismount", "horse", "companion",
      "leash", "command", "order"]


def hit(s):
    s = s.lower()
    return [k for k in KW if k in s]


# 1) Scan the whole unreal namespace for relevant class/function names.
print("###### unreal.* names matching keywords ######")
names = dir(unreal)
matched = [n for n in names if hit(n)]
for n in sorted(matched):
    obj = getattr(unreal, n)
    kind = "class" if isinstance(obj, type) else type(obj).__name__
    print("  %-45s [%s]" % (n, kind))

# 2) Is ConanCharacter exposed? Enumerate its mount-related methods.
print("\n###### ConanCharacter members ######")
cc = getattr(unreal, "ConanCharacter", None)
print("  unreal.ConanCharacter present:", cc is not None)
if cc:
    members = [m for m in dir(cc) if hit(m)]
    for m in sorted(members):
        print("   ", m)

# 3) MountFunctionLibrary (BP library) — but maybe a native MountLibrary exists too.
for libname in ["MountFunctionLibrary", "MountLibrary", "MountBlueprintLibrary",
                "ConanMountLibrary", "SaddleLibrary", "FollowerLibrary",
                "ThrallLibrary", "PetLibrary"]:
    lib = getattr(unreal, libname, None)
    if lib:
        print("\n###### unreal.%s ######" % libname)
        for m in sorted(dir(lib)):
            if not m.startswith("__"):
                print("   ", m)

# 4) Any class whose name screams mount/saddle/thrall component
print("\n###### Component-ish / system classes ######")
for n in sorted(names):
    low = n.lower()
    if any(low.endswith(suf) for suf in ("component", "subsystem", "manager", "system")) and hit(n):
        print("  ", n)
