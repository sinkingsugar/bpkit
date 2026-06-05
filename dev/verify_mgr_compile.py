import unreal
PATH = "/Game/_Scratch/BP_MountedFollowerManager"
bp = unreal.load_asset(PATH)
# recompile fresh
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
unreal.SystemLibrary.collect_garbage()
# read the tail of the log we just wrote and look for a compile failure on THIS asset
import os
logdir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())
logs = [os.path.join(logdir, f) for f in os.listdir(logdir) if f.endswith(".log")]
logs.sort(key=lambda p: os.path.getmtime(p))
tail = open(logs[-1], "r", encoding="utf-8", errors="ignore").read().splitlines()[-120:]
hits = [l for l in tail if ("undetermined" in l) or
        ("failed to compile" in l and "MountedFollowerManager" in l) or
        ("[Compiler]" in l and "Error" in l)]
print("=== recent compile errors touching the manager ===")
print("\n".join(hits) if hits else "(NONE -- manager compiles clean)")
