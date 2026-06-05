import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
chars = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
print("ConanCharacters:", len(chars))
for a in chars:
    cn = a.get_class().get_name()
    try: rider = a.get_rider()
    except Exception: rider = "?"
    try: mount = a.get_mount()
    except Exception: mount = "?"
    try: sad = a.get_embedded_saddle_id()
    except Exception: sad = "?"
    try: ap = a.get_attach_parent_actor()
    except Exception: ap = "?"
    ctrl = a.get_controller()
    print(" -", a.get_name(), "| class", cn)
    print("      rider=", rider, " mount=", mount, " saddle=", sad)
    print("      attach_parent=", ap, " ctrl=", ctrl.get_class().get_name() if ctrl else None,
          " loc=", a.get_actor_location())
