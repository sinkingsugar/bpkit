import unreal
for path in ("/Game", ):
    pass
ar = unreal.AssetRegistryHelpers.get_asset_registry()

def find(name):
    for a in ar.get_all_assets():
        if str(a.asset_name) == name:
            return a.get_asset()
    return None

for tname in ("FormationsTemplateTable", "FormationCriteriaTable"):
    dt = find(tname)
    print("=== %s ===" % tname, "->", dt)
    if not dt:
        continue
    try:
        rows = unreal.DataTableFunctionLibrary.get_data_table_row_names(dt)
        print("  rows:", [str(r) for r in rows])
    except Exception as e:
        print("  rows ERR:", e)
    # try to read the struct of the first row
    try:
        col = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(dt, "RowName")
    except Exception:
        pass
print("\n=== component classes ===")
for cn in ("BP_FormationLeaderComponent", "BP_FormationFollowerComponent"):
    c = find(cn)
    print(" ", cn, "->", c)
