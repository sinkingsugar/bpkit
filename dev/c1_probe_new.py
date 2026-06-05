import unreal
print("=== get_struct_type sig ===")
print(unreal.BlueprintEditorLibrary.get_struct_type.__doc__)

def doc(cls, m):
    f = getattr(cls, m, None)
    print("\n%s.%s:" % (cls.__name__, m))
    print((f.__doc__ or "?").split("\n\n")[0] if f else "  MISSING")

doc(unreal.SceneComponent, "get_relative_transform")
doc(unreal.SceneComponent, "set_relative_transform")
doc(unreal.SceneComponent, "k2_set_relative_transform")
doc(unreal.AIBlueprintHelperLibrary, "get_ai_controller")
doc(unreal.BrainComponent, "stop_logic")
doc(unreal.BrainComponent, "restart_logic")
doc(unreal.ActorComponent, "set_component_tick_enabled")
# AIController has brain_component property?
print("\nAIController has 'brain_component' prop:",
      "brain_component" in [p for p in dir(unreal.AIController)])
print("AIModule paths: AIController =", unreal.AIController.static_class().get_path_name())
print("BrainComponent =", unreal.BrainComponent.static_class().get_path_name())
print("AIBlueprintHelperLibrary =", unreal.AIBlueprintHelperLibrary.static_class().get_path_name())
