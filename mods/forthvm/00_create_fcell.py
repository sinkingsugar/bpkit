"""Create the FCell struct (ST_ForthCell) with 7 DISTINCT-typed members, FULLY
PROGRAMMATIC. Creating the struct is stock Python; members go through the ctypes
bridge (FStructureEditorUtils::AddVariable, engine-built pin types by address). The
struct's mandatory default bool member is reused as the 'B' field; the other six are
added. Robust + idempotent: closes editors + deletes (verified) before rebuilding,
so re-runs never duplicate members. Self-verifies via a MakeStruct probe.

    & $py ue_run.py mods/forthvm/00_create_fcell.py
"""
import sys, os, re
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import bridge as bp, config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "forthvm"))
sys.modules.pop("config", None)
import config as MOD

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: in PIE -- run with Play stopped"); raise SystemExit

bel = unreal.BlueprintEditorLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
EAL = unreal.EditorAssetLibrary

PKG, SN = MOD.OUTPUT_PKG, MOD.STRUCT
path, objpath = PKG + "/" + SN, PKG + "/" + SN + "." + SN


def force_delete():
    # Gentle, session-safe delete. NOTE: in a long editor session the undo/transaction
    # buffer pins "deleted" structs, so this can't truly free a rebuilt one -- that's
    # what the post-build member-count self-check catches (abort, ask for a fresh
    # session). NEVER close the user's other tabs to force it.
    if not EAL.does_asset_exist(path):
        return True
    try:
        aes.close_all_editors_for_asset(unreal.load_asset(objpath))
    except Exception:
        pass
    EAL.delete_asset(path)
    return not EAL.does_asset_exist(path)


if not force_delete():
    print("ABORT: could not delete existing", path, "-- close its tab in the editor and re-run")
    raise SystemExit

tools.create_asset(SN, PKG, unreal.UserDefinedStruct, unreal.StructureFactory())
struct_ptr = bp.find_object(objpath)
print("FCell:", objpath, "@ 0x%x  (fresh)" % struct_ptr)

BASIC = {"Integer": "int", "Integer64": "int64", "Float": "real", "Boolean": "bool"}
STRUCTS = {"Vector": "/Script/CoreUObject.Vector", "Rotator": "/Script/CoreUObject.Rotator",
           "Transform": "/Script/CoreUObject.Transform"}


def pin_for(label):
    return (bel.get_basic_type_by_name(BASIC[label]) if label in BASIC
            else bel.get_struct_type(unreal.load_object(None, STRUCTS[label])))


# CRITICAL: hold the pin wrappers alive across the AddVariable calls. The engine-built
# FEdGraphPinType is owned by the Python wrapper; if it's GC'd before AddVariable reads
# its address, the address is freed memory and AddVariable silently falls back to int.
held = [(role, label, pin_for(label)) for role, label in MOD.ADD_MEMBERS]
added = 0
for role, label, pin in held:                  # B is the default member -> not added
    pa = bp.obj_addr(pin)
    ok = bp.add_struct_variable(struct_ptr, pa) if pa else False
    print("  +%-5s %-10s -> %s" % (role, label, ok))
    added += 1 if ok else 0

# --- self-verify BEFORE saving: author MakeStruct, read the member pins back ---
# scratch BP names get reused across runs (and deletes may not stick this session),
# so clear the graph first -> the verify reads ONLY the current MakeStruct node.
_, full = bp.scratch_blueprint(name="BP_FCellVerify")
_bpp, _gp = bp.find_graph(full, "EventGraph")
if _gp:
    bp.clear_graph(_bpp, _gp)
bp.inject(full, ('Begin Object Class=/Script/BlueprintGraph.K2Node_MakeStruct Name="MK"\n'
                 '   StructType="/Script/CoreUObject.UserDefinedStruct\'%s\'"\n'
                 'End Object\n') % objpath, graph_name="EventGraph")
seen = {}                                       # dedupe by pin name (graphs can repeat)
for g in bp.read_blueprint(full):
    for line in g["text"].splitlines():
        if 'PinName="MemberVar' in line:
            nm = re.search(r'PinName="([^"]+)"', line).group(1)
            cat = re.search(r'PinType\.PinCategory="([^"]*)"', line)
            sub = re.search(r"PinSubCategoryObject=[^']*'([^']+)'", line)
            seen[nm] = ((cat.group(1) if cat else "?") + ("/" + os.path.basename(sub.group(1)) if sub else ""))
EAL.delete_asset(full.split(".")[0])
unreal.SystemLibrary.collect_garbage()

pins = sorted(seen.items())
print("\n--- FCell members (%d) ---" % len(pins))
for nm, tag in pins:
    print("  %-42s %s" % (nm, tag))
distinct = len(set(seen.values())) == len(seen)
ok = (added == len(MOD.ADD_MEMBERS) and len(pins) == 7 and distinct)
if ok:
    EAL.save_asset(path)
    print("\nFCELL OK: 7 distinct-typed members, saved. struct=%s" % objpath)
else:
    print("\nFCELL POLLUTED: %d members (want 7). NOT saved. This struct name is pinned by"
          " this session's undo buffer from repeated rebuilds -- restart the editor (or this"
          " is a stale name). A fresh editor session builds clean." % len(pins))
