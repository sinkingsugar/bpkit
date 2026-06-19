"""Shigawire build step 02 -- DT_SW_Items: a 2-row ItemTableRow table the controller
merges into the game's /Game/Items/ItemTable (step 03). Rows are cloned LIVE from the
Chakram template pair (24114 weapon / 24115 projectile, which reuse the offhand-axe
throw BP) and repointed at our cloned BPs.

  weapon row  (WEAPON_TEMPLATE_ID):     VisualObject=BP_SW_HookLauncher_C,
                                        CompatableAmmunitions=[PROJECTILE_TEMPLATE_ID]
  projectile  (PROJECTILE_TEMPLATE_ID): VisualObject=BP_SW_HookProjectile_C  (the flying hook)

Idempotent. Run with Play STOPPED.
    python ue_run.py mods/shigawire/02_item_table.py
"""
import sys, os, json
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import config as _cfg
sys.path.insert(0, os.path.join(_cfg.REPO_ROOT, "mods", "shigawire"))
sys.modules.pop("sw_config", None)
import sw_config as MOD

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: Play-in-Editor running."); raise SystemExit

EAL = unreal.EditorAssetLibrary
DTL = unreal.DataTableFunctionLibrary
ATH = unreal.AssetToolsHelpers.get_asset_tools()

def cls_ref(name):
    return "%s/%s.%s_C" % (MOD.OUTPUT_PKG, name, name)

# --- read the template rows live from the game ItemTable ---
src_dt = EAL.load_asset(MOD.GAME_ITEM_TABLE)
row_struct = src_dt.get_row_struct()
rows = json.loads(DTL.export_data_table_to_json_string(src_dt))
by_name = {str(r.get("Name")): r for r in rows}
wsrc, psrc = by_name.get(MOD.SRC_WEAPON_ROW), by_name.get(MOD.SRC_PROJECTILE_ROW)
if not wsrc or not psrc:
    print("ABORT: template rows missing", MOD.SRC_WEAPON_ROW, MOD.SRC_PROJECTILE_ROW); raise SystemExit

# --- weapon row: clone + repoint ---
w = dict(wsrc)
w["Name"] = MOD.WEAPON_TEMPLATE_ID
w["VisualObject"] = cls_ref(MOD.ITEM)
w["CompatableAmmunitions"] = [int(MOD.PROJECTILE_TEMPLATE_ID)]
w["ShortDesc"] = 'NSLOCTEXT("", "ItemTable_%s_ShortDesc", "%s")' % (MOD.WEAPON_TEMPLATE_ID, MOD.DISPLAY_NAME)
w["LongDesc"]  = ('NSLOCTEXT("", "ItemTable_%s_LongDesc", "A coil of shigawire tipped with a barbed '
                  'hook. Throw it to reel yourself to where it bites; a hooked foe is staggered.")'
                  % MOD.WEAPON_TEMPLATE_ID)
w["FirstModifier"] = ""; w["SecondModifier"] = ""

# --- projectile (ammo) row: clone + repoint ---
p = dict(psrc)
p["Name"] = MOD.PROJECTILE_TEMPLATE_ID
p["VisualObject"] = cls_ref(MOD.HOOK)
p["CompatableAmmunitions"] = []
p["FirstModifier"] = ""

# --- create-or-reuse DT_SW_Items with the same row struct, fill ---
PATH = "%s/%s" % (MOD.OUTPUT_PKG, MOD.ITEMS_DT)
if EAL.does_asset_exist(PATH):
    dt = EAL.load_asset(PATH)
else:
    factory = unreal.DataTableFactory()
    factory.set_editor_property("struct", row_struct)
    dt = ATH.create_asset(MOD.ITEMS_DT, MOD.OUTPUT_PKG, unreal.DataTable, factory)
print("DT:", PATH, "| row struct:", dt.get_row_struct().get_name())

ok = DTL.fill_data_table_from_json_string(dt, json.dumps([w, p]))
EAL.save_asset(PATH)
names = [str(n) for n in dt.get_row_names()]
print("fill ok:", ok, "| rows:", names)
back = DTL.export_data_table_to_json_string(dt)
print("  weapon VisualObject ->", MOD.ITEM in back, "| ammo VisualObject ->", MOD.HOOK in back,
      "| ammo link ->", MOD.PROJECTILE_TEMPLATE_ID in back)
print("02 OK" if ok and MOD.WEAPON_TEMPLATE_ID in names and MOD.PROJECTILE_TEMPLATE_ID in names else "02 ISSUE")
