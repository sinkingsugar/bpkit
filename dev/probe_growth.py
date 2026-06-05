import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
dtl = unreal.DataTableFunctionLibrary

def find_row(target):
    out = []
    for a in ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "DataTable"), True):
        try:
            dt = unreal.load_asset(str(a.package_name))
            if dtl.does_data_table_row_exist(dt, target):
                out.append(str(a.package_name))
        except Exception:
            pass
    return out

def dump_row(pkg, target):
    dt = unreal.load_asset(pkg)
    names = [str(n) for n in dtl.get_data_table_row_names(dt)]
    if target not in names:
        return
    idx = names.index(target)
    cols = [str(c) for c in dtl.get_data_table_column_names(dt)]
    line("\n=== %s  ::  row '%s' ===" % (pkg, target))
    for c in cols:
        try:
            v = dtl.get_data_table_column_as_string(dt, c)[idx]
            if v not in ("", "0.000000", "0", "None", "False"):
                line("  %-26s = %s" % (c, v))
        except Exception:
            pass

for tgt in ["Exiles1", "All Thralls Base", "Normal"]:
    tabs = find_row(tgt)
    line("row %r found in: %s" % (tgt, tabs))
    for t in tabs:
        dump_row(t, tgt)
