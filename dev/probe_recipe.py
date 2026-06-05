import unreal
def line(*a): unreal.log(" ".join(str(x) for x in a))

dt = unreal.load_asset("/Game/Sorcery/Rituals/RitualData")
dtl = unreal.DataTableFunctionLibrary
names = list(dtl.get_data_table_row_names(dt))

for col in ["Payload", "Payload_36_98ADA3C641B993A15F5C0AB81F5FC0C2"]:
    try:
        vals = dtl.get_data_table_column_as_string(dt, col)
    except Exception as e:
        line("col", col, "ERR", e); continue
    if not vals:
        line("col", col, "-> empty"); continue
    line("\n=== column '%s' (%d) ===" % (col, len(vals)))
    for n, v in zip(names, vals):
        line("  %-8s %s" % (n, v))
    break
