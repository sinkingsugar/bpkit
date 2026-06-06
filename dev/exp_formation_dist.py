import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
def call(o,n,*a):
    try: return getattr(o,n)(*a)
    except Exception as e: return "ERR(%s)"%str(e)[:40]

lc = call(pawn, "get_my_formation_leader_component")
print("leader comp:", lc.get_name() if lc and "ERR" not in str(lc) else lc)
if lc and "ERR" not in str(lc):
    # any scale / spacing / radius / distance / offset knob?
    print("scale/spacing props:")
    for p in [x for x in dir(lc) if any(k in x.lower() for k in
              ("scale","spacing","radius","distance","offset","spread","row","template"))]:
        try: print("   %s = %r" % (p, lc.get_editor_property(p)))
        except Exception: pass

# dump each template row's data so we can see which has wider slots
print("\n=== FormationsTemplateTable rows ===")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
dt = None
for a in ar.get_all_assets():
    if str(a.asset_name) == "FormationsTemplateTable":
        dt = a.get_asset(); break
if dt:
    for rn in unreal.DataTableFunctionLibrary.get_data_table_row_names(dt):
        exp = unreal.DataTableFunctionLibrary.export_data_table_to_json(dt) if hasattr(unreal.DataTableFunctionLibrary,"export_data_table_to_json") else None
    # export whole table to JSON once
    try:
        js = unreal.DataTableFunctionLibrary.export_data_table_to_json(dt)
        print(js[:1500])
    except Exception as e:
        print("json export err:", e)
