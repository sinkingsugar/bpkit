import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
dtl = unreal.DataTableFunctionLibrary

# what helpers exist?
fns = [f for f in dir(dtl) if not f.startswith("_")]
line("DataTableFunctionLibrary fns:", ", ".join(fns))

dt = unreal.load_asset("/Game/Systems/SpawnTable/SpawnDataTable")
names = [str(n) for n in dtl.get_data_table_row_names(dt)]
idx = names.index("Sorcery_NecroZombie")
line("\ntarget row index:", idx)

# get_data_table_column_as_string for each property; print only target row's cell
get_cols = getattr(dtl, "get_data_table_column_names", None)
if get_cols:
    cols = [str(c) for c in get_cols(dt)]
    line("columns:", cols)
    for c in cols:
        try:
            vals = dtl.get_data_table_column_as_string(dt, c)
            line("  %-40s = %s" % (c, vals[idx] if idx < len(vals) else "?"))
        except Exception as e:
            line("  col", c, "err", e)
