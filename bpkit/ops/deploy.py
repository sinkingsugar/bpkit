"""Deploy a mod into the live editor: import its source assets, then run its
Blueprint build steps in order, then report. Driven by `mods/<name>/manifest.py`.

    & $py ue_run.py bpkit/ops/deploy.py <mod-name-or-path>     # e.g. mounted-followers

RUN INSIDE THE EDITOR (ship via ue_run.py) with Play STOPPED -- it compiles
Blueprints, which must never happen during PIE. Idempotent: build steps reuse /
overwrite their own assets, so re-deploying is safe.

A mod is "deployable" if its folder has a manifest.py exposing:
    BUILD   = ["01_step.py", ...]   # ordered step files (editor-side payloads), run as-is
    ASSETS  = [ {src,dest,name,replace}, ... ]   # optional source imports (anims/meshes/...)
    OUTPUT_PKG = "/Game/..."        # where it writes (for the report)
"""
import sys, os, importlib, traceback
for _m in list(sys.modules):
    if _m == "bpkit" or _m.startswith("bpkit."):
        sys.modules.pop(_m, None)
import unreal
from bpkit import config as cfg

argv = cfg.argv()
if not argv:
    print("usage: ue_run.py bpkit/ops/deploy.py <mod-name-or-path>")
    print("mods available:", ", ".join(sorted(
        d for d in os.listdir(os.path.join(cfg.REPO_ROOT, "mods"))
        if os.path.isfile(os.path.join(cfg.REPO_ROOT, "mods", d, "manifest.py")))) or "(none with manifest.py)")
    raise SystemExit

target = argv[0]
cand = target if os.path.isabs(target) else os.path.join(cfg.REPO_ROOT, "mods", target)
mod_dir = os.path.abspath(cand if os.path.isdir(cand) else target)
if not os.path.isdir(mod_dir):
    print("NO SUCH MOD:", target, "-- looked in", cand)
    raise SystemExit
name = os.path.basename(mod_dir)

# pre-flight: never author/compile during Play (breaks live instances)
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
if les.is_in_play_in_editor():
    print("ABORT: Play-in-Editor is running. Stop Play, then deploy.")
    raise SystemExit

# load the manifest fresh
sys.path.insert(0, mod_dir)
for m in ("manifest", "mf_config"):
    sys.modules.pop(m, None)
try:
    man = importlib.import_module("manifest")
except ModuleNotFoundError:
    print("NOT DEPLOYABLE: no manifest.py in", mod_dir)
    print("Add manifest.py with BUILD=[...] (ordered step files) -- see mods/mounted-followers/manifest.py.")
    raise SystemExit

BUILD = list(getattr(man, "BUILD", []))
ASSETS = list(getattr(man, "ASSETS", []))
OUTPUT_PKG = getattr(man, "OUTPUT_PKG", "?")
print("=== DEPLOY %s -> %s ===" % (name, OUTPUT_PKG))

# 1) import source assets (the 'detached repo carries its own content' path)
if ASSETS:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tasks = []
    for a in ASSETS:
        src = a["src"]
        if not os.path.isabs(src):
            src = os.path.join(mod_dir, src)
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", src)
        t.set_editor_property("destination_path", a.get("dest", OUTPUT_PKG))
        if a.get("name"):
            t.set_editor_property("destination_name", a["name"])
        t.set_editor_property("automated", True)
        t.set_editor_property("replace_existing", a.get("replace", True))
        t.set_editor_property("save", True)
        tasks.append((src, t))
    tools.import_asset_tasks([t for _, t in tasks])
    for src, t in tasks:
        out = list(t.get_editor_property("imported_object_paths") or [])
        print("  asset %-42s -> %s" % (os.path.basename(src), out or "FAILED"))
else:
    print("  (no source assets to import)")

# 2) run build steps in order, in THIS editor process. Each step is a normal
#    editor-side payload (does its own bpkit reload + prints its own result).
fails = 0
for step in BUILD:
    spath = step if os.path.isabs(step) else os.path.join(mod_dir, step)
    print("\n--- build step: %s ---" % step)
    if not os.path.isfile(spath):
        print("  MISSING:", spath)
        fails += 1
        continue
    with open(spath, "r", encoding="utf-8") as f:
        code = f.read()
    g = {"__name__": "__deploy_step__", "__file__": spath}
    try:
        exec(compile(code, spath, "exec"), g)
    except SystemExit:
        pass
    except Exception:
        print("  STEP RAISED:")
        traceback.print_exc()
        fails += 1

print("\n=== DEPLOY %s: %s ===" % (name, "OK" if fails == 0 else "%d STEP(S) FAILED" % fails))
