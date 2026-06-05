import unreal
bp_obj = unreal.load_asset("/Game/_Scratch/BP_MF_Recipe")
unreal.BlueprintEditorLibrary.compile_blueprint(bp_obj)
# authoritative: upgrade-note / status accessors
for m in ("blueprint_status", "BlueprintStatus", "status", "Status"):
    try:
        print(m, "=", bp_obj.get_editor_property(m)); break
    except Exception:
        pass
# is the generated class valid + non-error? check BlueprintEditorLibrary helpers
for fn in dir(unreal.BlueprintEditorLibrary):
    if "error" in fn.lower() or "status" in fn.lower() or "uptodate" in fn.lower() or "is_blueprint" in fn.lower():
        print("BEL.", fn)
# does it have errors? KismetEditorUtilities-style
try:
    print("get_blueprint_status? ", unreal.BlueprintEditorLibrary.get_blueprint_status(bp_obj))
except Exception as e:
    print("no get_blueprint_status:", str(e).splitlines()[-1][:60])
