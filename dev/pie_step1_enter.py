"""Step 1: enter Simulate-in-Editor (idempotent) and report world state.

Simulate ticks the world (AI possess + navmesh) without needing a player pawn.
Run, wait ~3s for PIE to spin up, then run pie_step2_spawn.py.

    python ue_run.py dev/pie_step1_enter.py
"""
import unreal

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
already = les.is_in_play_in_editor()
print("is_in_play_in_editor (before):", already)
if not already:
    try:
        unreal.EditorLevelLibrary.editor_play_simulate()
        print("requested editor_play_simulate()")
    except Exception as e:
        print("editor_play_simulate err:", e)
        # fallback to begin play
        les.editor_request_begin_play()
        print("requested editor_request_begin_play()")
else:
    print("already in PIE/sim")

# get_pie_worlds may be empty until the world finishes spinning up (next ticks)
try:
    worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
    print("pie_worlds now:", [w.get_path_name() for w in worlds])
except Exception as e:
    print("get_pie_worlds err:", e)
