import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
player = unreal.GameplayStatics.get_player_pawn(world, 0)

# --- THIRST / survival: find + apply a god / infinite-stats cheat ---
cm = None
for acc in ("conan_cheat_manager", "cheat_manager"):
    try:
        cm = getattr(pc, acc)
        if cm:
            print("cheat manager via", acc, ":", cm); break
    except Exception:
        pass
if cm:
    meths = [m for m in dir(cm) if any(k in m.lower() for k in
             ("god","infinit","survival","stat","heal","thirst","food","water","hunger","immort","invuln","drain","consume"))]
    print("cheat stat/god methods:", meths)
    for m in meths:
        if any(k in m.lower() for k in ("infinit","god","survival","immort")):
            try:
                getattr(cm, m)()
                print("  called", m)
            except Exception as e:
                print("  ", m, "needs args / err:", str(e)[:50])

# Console fallbacks
for cmd in ["God", "ToggleInfiniteStamina", "EnableCheats"]:
    try:
        unreal.SystemLibrary.execute_console_command(world, cmd, pc)
        print("exec:", cmd)
    except Exception as e:
        print("exec err", cmd, e)

# Player stat/attribute setters?
print("\nplayer stat methods:", [m for m in dir(player) if any(k in m.lower() for k in
      ("thirst","hydration","water","food","hunger","stat","attribute","vital"))][:30])

# --- SADDLE: inspect spawn_template_item signature ---
print("\nspawn_template_item doc:")
print((horse_doc := getattr(unreal.ConanCharacter, "spawn_template_item").__doc__ or "")[:400])
