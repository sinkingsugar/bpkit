"""C6a -- BP_MF_SaveGame: a USaveGame subclass holding the persisted Mount limit.
The `dc MFHorses N` command writes N here + SaveGameToSlot; the manager loads it on
per-player init so the configured limit survives server restarts (a .sav in
Saved/SaveGames -- entirely separate from Conan's game_0.db, so zero save conflict).

Run with Play STOPPED:  python ue_run.py mods/mounted-followers/03_savegame.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
import os
from bpkit import bridge as bp, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "mounted-followers"))
sys.modules.pop("mf_config", None)
import mf_config as MOD

PKG, NAME = MOD.OUTPUT_PKG, MOD.SAVEGAME
PATH = PKG + "/" + NAME
FULL = PATH + "." + NAME

# create-or-reuse a USaveGame subclass (a data-only BP: no graph, just one var)
bp_obj, _ = bp.scratch_blueprint(pkg=PKG, name=NAME, parent=unreal.SaveGame)
print("savegame BP:", FULL)

intt = unreal.BlueprintEditorLibrary.get_basic_type_by_name("int")
unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "MountLimit", intt)  # no-op if exists
# instance-editable so the command can set it on a fresh CreateSaveGameObject instance
unreal.BlueprintEditorLibrary.set_blueprint_variable_instance_editable(bp_obj, "MountLimit", True)

unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)

# bake the default on the CDO (a save written before any dc still reads a sane value)
gc = unreal.load_object(None, FULL + "_C")
if gc:
    try:
        unreal.get_default_object(gc).set_editor_property("MountLimit", MOD.DEFAULT_MOUNT_LIMIT)
    except Exception as e:
        print("CDO default set err:", e)
unreal.EditorAssetLibrary.save_asset(PATH)

# verify
gc2 = unreal.load_object(None, FULL + "_C")
print("class loaded:", bool(gc2))
if gc2:
    cdo = unreal.get_default_object(gc2)
    print("MountLimit default:", cdo.get_editor_property("MountLimit"))
    # functional proof it's a valid USaveGame subclass: CreateSaveGameObject must accept it
    obj = unreal.GameplayStatics.create_save_game_object(gc2)
    print("create_save_game_object ->", obj, "| MountLimit:",
          obj.get_editor_property("MountLimit") if obj else None)
print("BUILD OK")
