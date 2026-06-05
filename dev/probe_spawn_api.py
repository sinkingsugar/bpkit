import unreal
gs = [m for m in dir(unreal.GameplayStatics) if "spawn" in m.lower()]
print("GameplayStatics spawn*:", gs)
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
print("EAS spawn*:", [m for m in dir(eas) if "spawn" in m.lower()])
print("EditorLevelLibrary spawn*:", [m for m in dir(unreal.EditorLevelLibrary) if "spawn" in m.lower()])
# Is there a world-aware spawn anywhere obvious?
print("has SystemLibrary?", hasattr(unreal, "SystemLibrary"))
