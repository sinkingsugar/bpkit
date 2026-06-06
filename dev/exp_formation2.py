import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:70]

# does the player already have a leader component? add one if not.
lc = call(pawn, "get_my_formation_leader_component")
print("existing leader_comp:", lc if "ERR" in str(lc) else (lc.get_name() if lc else None))
if not lc or "ERR" in str(lc):
    cls = unreal.load_object(None, "/Game/Systems/AI/Formations/BP_FormationLeaderComponent.BP_FormationLeaderComponent_C")
    print("leader comp class:", cls)
    try:
        comp = pawn.add_component_by_class(cls, False, unreal.Transform(), False)
        print("added leader component:", comp.get_name() if comp else None)
    except Exception as e:
        print("add_component_by_class ERR:", str(e)[:90])

print("set_formation_leader_row('Test'):", call(pawn, "set_formation_leader_row", unreal.Name("Test")))
print("player.is_formation_leader:", call(pawn, "is_formation_leader"))
lc2 = call(pawn, "get_my_formation_leader_component")
print("leader_comp now:", lc2 if "ERR" in str(lc2) else (lc2.get_name() if lc2 else None))

# tell the horses to join
tsc = pawn.get_thrall_system_component()
horses = [f for f in tsc.get_following_thrall_characters() if f.is_mountable()]
print("horses to join:", len(horses))
for h in horses:
    call(h, "set_formation_criteria_row", unreal.Name("Test"), True)
print("criteria set on all horses (autojoin). Check is_in_formation in a follow-up run.")
