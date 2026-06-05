import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
dtl = unreal.DataTableFunctionLibrary

# 1) candidate spawn-table assets: DataTables whose name hints spawn/weighted/NPC
allassets = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "DataTable"), True)
line("DataTables total:", len(allassets))
cands = []
for a in allassets:
    nm = str(a.asset_name)
    if any(k in nm.lower() for k in ["spawn", "weight", "npc", "zombie", "necro"]):
        cands.append(str(a.package_name))
line("candidate spawn tables (%d):" % len(cands))
for c in cands[:40]:
    line("   ", c)

# 2) find which table actually contains a row 'Sorcery_NecroZombie'
line("\n=== searching for row 'Sorcery_NecroZombie' ===")
TARGET = "Sorcery_NecroZombie"
for a in allassets:
    try:
        dt = unreal.load_asset(str(a.package_name))
        rows = dtl.get_data_table_row_names(dt)
        if any(str(r) == TARGET for r in rows):
            line("FOUND in:", a.package_name, " (rows:", len(rows), ")")
    except Exception:
        pass
