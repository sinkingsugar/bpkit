import unreal, traceback

# 1) BlueprintEditorLibrary methods touching variables / pin types
print("=== BlueprintEditorLibrary var/type/pin methods ===")
for m in sorted(dir(unreal.BlueprintEditorLibrary)):
    if m.startswith("__"): continue
    if any(k in m.lower() for k in ("variable", "pin", "type", "member")):
        print("  ", m)

# 2) try kwargs construction (may bypass protected setters)
print("\n=== kwargs construction attempts ===")
for kwargs in (dict(pin_category="object"),
               dict(PinCategory="object")):
    try:
        t = unreal.EdGraphPinType(**kwargs)
        print("  ctor OK", kwargs)
    except Exception:
        print("  ctor FAIL", kwargs, "->", traceback.format_exc().splitlines()[-1][:80])

# 3) is there a pin-type factory anywhere?
print("\n=== module-level pin type makers ===")
for n in dir(unreal):
    if "pintype" in n.lower() or n in ("PinType",):
        print("  unreal.", n)

# 4) What did add_member_variable actually create for 'Rider'?
print("\n=== existing scratch vars ===")
bp_obj = unreal.EditorAssetLibrary.load_asset("/Game/_Scratch/BP_MF_Recipe")
try:
    names = unreal.BlueprintEditorLibrary.get_variable_names(bp_obj) if hasattr(unreal.BlueprintEditorLibrary, "get_variable_names") else None
    print("  get_variable_names:", names)
except Exception as e:
    print("  err:", str(e).splitlines()[-1][:80])
