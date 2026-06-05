import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))
dtl = unreal.DataTableFunctionLibrary

dt = unreal.load_asset("/Game/Systems/Perks/NPCPerksDataTable")
names = [str(n) for n in dtl.get_data_table_row_names(dt)]
cols = [str(c) for c in dtl.get_data_table_column_names(dt)]
line("NPCPerksDataTable: %d rows" % len(names))
line("columns:", cols)
line("first 20 row names:", names[:20])

# dump a couple of rows to see chance/condition fields (randomness + PerkType gating)
for tgt in names[:3]:
    idx = names.index(tgt)
    line("\n=== row '%s' ===" % tgt)
    for c in cols:
        try:
            v = dtl.get_data_table_column_as_string(dt, c)[idx]
            if v not in ("", "0.000000", "0", "None", "False"):
                line("  %-26s = %s" % (c, v))
        except Exception:
            pass
