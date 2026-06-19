"""Shigawire build step 01 -- clone the throwing-axe template BPs into the mod package.

  BP_SW_HookProjectile <- BP_throwing_offhand_axe_projectile  (child of BP_BaseProjectile;
                          the flying actor where pull/CC/cable logic gets added in step 04)
  BP_SW_HookLauncher   <- BP_throwing_offhand_axe             (the thrown-weapon visual shell)

Idempotent (skips an existing clone). Run with Play STOPPED.
    python ue_run.py mods/shigawire/01_assets.py
"""
import sys, os
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
    print("ABORT: Play-in-Editor running. Stop Play, then build."); raise SystemExit

EAL = unreal.EditorAssetLibrary
if not EAL.does_directory_exist(MOD.OUTPUT_PKG):
    print("ABORT: %s not mounted -- create+activate the Shigawire mod in the DevKit first." % MOD.OUTPUT_PKG)
    raise SystemExit

def clone(src, dst_name):
    dst = "%s/%s" % (MOD.OUTPUT_PKG, dst_name)
    if EAL.does_asset_exist(dst):
        print("  exists, skip:", dst); return dst
    if not EAL.does_asset_exist(src):
        print("  !! SOURCE MISSING:", src); return None
    obj = EAL.duplicate_asset(src, dst)
    ok = EAL.save_asset(dst) if obj else False
    print("  cloned %-22s -> %s  (saved=%s)" % (os.path.basename(src), dst, ok))
    return dst if obj else None

print("=== Shigawire 01: clone template assets ===")
proj = clone(MOD.SRC_PROJECTILE, MOD.HOOK)
item = clone(MOD.SRC_VISUAL, MOD.ITEM)

# verify the projectile is still a BP_BaseProjectile subclass (parent preserved by duplicate)
if proj:
    bp = EAL.load_asset(proj)
    gen = bp.generated_class()
    sup = gen.get_super_class() if hasattr(gen, "get_super_class") else None
    print("  HookProjectile generated class:", gen.get_name(),
          "| super:", sup.get_name() if sup else "(unknown)")
print("01 OK" if proj and item else "01 ISSUE")
