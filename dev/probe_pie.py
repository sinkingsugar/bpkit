"""What PIE / world-access control do we have from the remote-exec channel?

Checks: current editor map, whether a game (PIE) world exists right now, and
which PIE-control entrypoints are callable from Python (so we know if Claude can
press Play, or the user must).

    python ue_run.py dev/probe_pie.py
"""
import unreal

# 1) Current editor world / loaded map
try:
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
except Exception:
    ues = None
print("UnrealEditorSubsystem:", ues)
if ues:
    try:
        ew = ues.get_editor_world()
        print("  editor_world:", ew.get_name() if ew else None, ew.get_path_name() if ew else None)
    except Exception as e:
        print("  get_editor_world err:", e)
    # get_game_world returns the PIE/game world if one is running
    for m in ("get_game_world",):
        f = getattr(ues, m, None)
        print("  has %s:" % m, f is not None)
        if f:
            try:
                gw = f()
                print("    ->", gw)
            except Exception as e:
                print("    err:", e)

# 2) PIE control entrypoints
print("\n-- PIE control surfaces --")
les = None
try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
except Exception as e:
    print("  no LevelEditorSubsystem:", e)
print("LevelEditorSubsystem:", les)
if les:
    for m in dir(les):
        if any(k in m.lower() for k in ("play", "pie", "simulate")):
            print("   LES.", m)

print("\n-- EditorLevelLibrary play fns --")
ell = getattr(unreal, "EditorLevelLibrary", None)
if ell:
    for m in dir(ell):
        if any(k in m.lower() for k in ("play", "pie", "simulate")):
            print("   ELL.", m)

# 3) Is there a navmesh / game mode hint in the current world?
print("\n-- World/game-mode context --")
try:
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = eas.get_all_level_actors()
    print("  editor actors in level:", len(actors))
    kinds = {}
    for a in actors:
        cn = a.get_class().get_name()
        if any(k in cn for k in ("Nav", "GameMode", "PlayerStart", "Recast")):
            kinds[cn] = kinds.get(cn, 0) + 1
    print("  nav/gamemode/start actors:", kinds)
except Exception as e:
    print("  actor scan err:", e)
