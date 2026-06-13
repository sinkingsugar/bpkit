"""C6c -- DT_MF_Commands: a 1-row BlueprintCommandDataRow table the manager merges
into the game's CustomConsoleCommandsDataTable at BeginPlay so `dc MFHorses N`
resolves. Row: name=MFHorses, CommandActorClass=BP_MF_HorsesCommand, RequireAdmin
(admins in MP; SP players are admin), RunOnServer (the cap is server-authoritative).

Run with Play STOPPED:  python ue_run.py mods/mounted-followers/05_command_table.py
"""
import sys
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal, os, json
from bpkit import config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "mounted-followers"))
sys.modules.pop("mf_config", None)
import mf_config as MOD

PKG, NAME = MOD.OUTPUT_PKG, MOD.CMD_TABLE
PATH = PKG + "/" + NAME
CMD_CLS = "%s/%s.%s_C" % (PKG, MOD.COMMAND, MOD.COMMAND)   # BP_MF_HorsesCommand generated class
DTL = unreal.DataTableFunctionLibrary

# create-or-reuse the DataTable with RowStruct = BlueprintCommandDataRow
eal = unreal.EditorAssetLibrary
if eal.does_asset_exist(PATH):
    dt = eal.load_asset(PATH)
else:
    factory = unreal.DataTableFactory()
    factory.set_editor_property("struct", unreal.BlueprintCommandDataRow.static_struct())
    dt = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PKG, unreal.DataTable, factory)
print("DataTable:", dt, "| row struct:", dt.get_row_struct().get_name() if dt else None)

# discover exact column export names (handles b-prefix / casing) then build the row JSON
cols = DTL.get_data_table_column_export_names(dt)
print("columns:", cols)
def col(sub):
    return next((c for c in cols if sub.lower() in c.lower().replace("_", "")), None)

row = {"Name": MOD.CMD_NAME}
row[col("commandactorclass")] = CMD_CLS
ra = col("requireadmin");  row[ra] = True if ra else None
rs = col("runonserver");   row[rs] = True if rs else None
rc = col("runonclient");   row[rc] = False if rc else None
row = {k: v for k, v in row.items() if v is not None or k == "Name"}
print("row to write:", row)

ok = DTL.fill_data_table_from_json_string(dt, json.dumps([row]))
print("fill ok:", ok)
eal.save_asset(PATH)

# verify: row present + command class resolved
print("row names:", [str(n) for n in dt.get_row_names()])
back = DTL.export_data_table_to_json_string(dt)
print("contains command class:", MOD.COMMAND in (back or ""))
print("contains require/server flags:", '"RequireAdmin"' in (back or "") or "require" in (back or "").lower())
print("--- exported row ---")
print(back)
print("BUILD OK" if dt and MOD.CMD_NAME in [str(n) for n in dt.get_row_names()] else "BUILD ISSUE")
