import unreal
cm = unreal.ConanCheatManager
print("ConanCheatManager spawn/npc/summon methods:")
for m in sorted(dir(cm)):
    if any(k in m.lower() for k in ("spawn","npc","summon","creature","thrall","pet","mount","horse")):
        print("  ", m)
print("\nSpawnTableLibrary:")
for m in sorted(dir(unreal.SpawnTableLibrary)):
    if not m.startswith("__"):
        print("  ", m)
