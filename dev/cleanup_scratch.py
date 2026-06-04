"""In-editor payload: delete all throwaway scratch assets created during dev."""
import unreal

eal = unreal.EditorAssetLibrary
SCRATCH_DIRS = ("/Game/_InjectScratch", "/Game/_Scratch")

for d in SCRATCH_DIRS:
    if not eal.does_directory_exist(d):
        print("clean:", d, "-> not present")
        continue
    for a in eal.list_assets(d, recursive=True, include_folder=False):
        path = a.split(".")[0]
        print("  delete_asset %-45s -> %s" % (path, eal.delete_asset(path)))
    ok = eal.delete_directory(d)
    print("clean:", d, "-> delete_directory", ok, "| exists?", eal.does_directory_exist(d))
