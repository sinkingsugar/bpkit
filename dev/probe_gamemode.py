"""Predict the player-spawn modal: inspect the current map's GameMode + PlayerStart.
Read-only, no PIE, no modals."""
import unreal

ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world = ues.get_editor_world()
print("world:", world.get_path_name())
ws = world.get_world_settings() if hasattr(world, "get_world_settings") else None
print("world settings:", ws)
if ws:
    for p in ["default_game_mode", "game_mode_override"]:
        try:
            v = ws.get_editor_property(p)
            print("  %-20s = %s" % (p, v))
        except Exception as e:
            print("  %-20s ERR %s" % (p, str(e)[:50]))

# Project default game mode
try:
    import unreal as u
    gm = unreal.SystemLibrary.get_class_display_name  # noop guard
except Exception:
    pass

# PlayerStart actors + their encroachment
eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in eas.get_all_level_actors():
    cn = a.get_class().get_name()
    if "PlayerStart" in cn:
        print("PlayerStart:", a.get_name(), "loc=", a.get_actor_location())
    if "WorldSettings" in cn:
        for p in ["default_game_mode", "game_mode_override"]:
            try:
                print("  WS.%s = %s" % (p, a.get_editor_property(p)))
            except Exception:
                pass

# What is the project default GameMode (from config)?
try:
    gm_path = unreal.SystemLibrary.get_project_content_dir()
    print("content dir:", gm_path)
except Exception:
    pass
