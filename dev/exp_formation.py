import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:60]

# 1) make the PLAYER a formation leader with the 'Test' template
print("set_formation_leader_row('Test'):", call(pawn, "set_formation_leader_row", unreal.Name("Test")))
print("  player.is_formation_leader:", call(pawn, "is_formation_leader"))
lc = call(pawn, "get_my_formation_leader_component")
print("  player.leader_comp:", lc if "ERR" in str(lc) else (lc.get_name() if lc else None))

# 2) find a ConanCharacter NPC (not the player, alive) to test joining
npcs = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
        if c != pawn]
print("\nConanCharacters in world (non-player):", len(npcs))
for c in npcs[:6]:
    print("   -", c.get_class().get_name())
if npcs:
    t = npcs[0]
    print("\ntest-join on:", t.get_class().get_name())
    print("  set_formation_criteria_row('Test', autojoin=True):",
          call(t, "set_formation_criteria_row", unreal.Name("Test"), True))
    print("  can_autojoin_formation:", t.get_editor_property("can_autojoin_formation")
          if hasattr(t, "get_editor_property") else "?")
    print("  is_in_formation (immediate):", call(t, "is_in_formation"))
