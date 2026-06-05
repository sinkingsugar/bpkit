import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
found = False
for m in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if "MountedFollowerManager" in m.get_class().get_name():
        found = True
        try:
            ver = m.get_editor_property("MgrVersion")
        except Exception as e:
            ver = "NO_PROP(%s)" % e
        print("MGR", m.get_name(), "| MgrVersion:", ver,
              "| Initialized:", m.get_editor_property("Initialized"),
              "| WasMounted:", m.get_editor_property("WasMounted"))
if not found:
    print("NO MANAGER INSTANCE IN WORLD (not in PIE, or not spawned yet)")
print("VERDICT: MgrVersion==2 -> FIXED class is live; 0/missing -> stale cached class -> restart editor")
