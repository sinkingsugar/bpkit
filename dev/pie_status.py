"""Reconnect + report PIE state; end any running play session cleanly. No modals."""
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
inplay = les.is_in_play_in_editor()
print("is_in_play_in_editor:", inplay)
try:
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    print("pie worlds:", [w.get_path_name() for w in worlds])
except Exception as e:
    print("get_pie_worlds err:", e)
if inplay:
    les.editor_request_end_play()
    print("requested end play")
print("methods on LES:", [m for m in dir(les) if "play" in m.lower() or "sim" in m.lower()])
