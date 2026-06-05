import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
dtl = unreal.DataTableFunctionLibrary

# 1) the variations table - male AND female entries?
dt = unreal.load_asset("/Game/Characters/NPCs/Necromancy_followers/Blueprints/NecromancyZombieVariationsTable")
if dt:
    names = [str(n) for n in dtl.get_data_table_row_names(dt)]
    cols = [str(c) for c in dtl.get_data_table_column_names(dt)]
    line("VariationsTable: %d rows, cols=%s" % (len(names), cols))
    for n in names:
        idx = names.index(n)
        cells = []
        for c in cols:
            try:
                v = dtl.get_data_table_column_as_string(dt, c)[idx]
                cells.append("%s=%s" % (c, v))
            except Exception:
                pass
        line("  [%s] %s" % (n, " | ".join(cells)))
else:
    line("VariationsTable not found")
