import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def by_tag(t):
    a = unreal.GameplayStatics.get_all_actors_with_tag(world, t); return a[0] if a else None
horse = by_tag("TEST_HORSE")

# 1) Read SaddleTable rows + the item-template id column
st = unreal.load_object(None, "/Game/Items/SaddleTable.SaddleTable")
print("SaddleTable:", st)
try:
    rows = unreal.DataTableFunctionLibrary.get_data_table_row_names(st)
    print("row names (%d):" % len(rows), [str(r) for r in rows][:15])
    cols = unreal.DataTableFunctionLibrary.get_data_table_column_as_string(st, "ItemId") if hasattr(unreal.DataTableFunctionLibrary, "get_data_table_column_as_string") else None
    print("ItemId column:", cols)
except Exception as e:
    print("datatable err:", e)
# Export first few rows as json-ish
try:
    exp = unreal.DataTableFunctionLibrary.export_to_json_string(st) if hasattr(unreal.DataTableFunctionLibrary,"export_to_json_string") else None
    if exp:
        print("JSON head:", exp[:1200])
except Exception as e:
    print("export err:", e)

# 2) Horse inventory surface
print("\n=== horse inventory methods ===")
for m in sorted(dir(horse)):
    if any(k in m.lower() for k in ("inventory","saddle","add_item","equip","item")):
        print("  ", m)
