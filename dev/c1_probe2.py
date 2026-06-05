import unreal, traceback
t = unreal.EdGraphPinType()
for cand, val in (("PinCategory", "object"),
                  ("PinCategory", unreal.Name("object")),
                  ("PinSubCategoryObject", unreal.ConanCharacter.static_class())):
    try:
        t.set_editor_property(cand, val)
        print("SET OK", cand, "=", repr(val))
    except Exception:
        print("SET FAIL", cand, "=", repr(val))
        print("   ", traceback.format_exc().splitlines()[-1])

# read back what we have
for cand in ("PinCategory", "PinSubCategoryObject"):
    try:
        print("GET", cand, "=", t.get_editor_property(cand))
    except Exception as e:
        print("GET FAIL", cand, ":", str(e).splitlines()[-1][:80])

# does add_member_variable accept this now?
bp_obj = unreal.EditorAssetLibrary.load_asset("/Game/_Scratch/BP_MF_Recipe")
if bp_obj:
    ok = unreal.BlueprintEditorLibrary.add_member_variable(bp_obj, "Rider", t)
    print("add_member_variable Rider ->", ok)
    # confirm it took the right type
    for v in unreal.BlueprintEditorLibrary.get_blueprint_variables(bp_obj) if hasattr(unreal.BlueprintEditorLibrary, "get_blueprint_variables") else []:
        print("  var:", v)
