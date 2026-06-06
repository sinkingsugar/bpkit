import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()

def names():
    return set(a.get_name() for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor))
def chars():
    return [c.get_name() for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)]
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]

before = names()
print("ConanCharacters BEFORE:", chars())

# APPLY formation: player as leader, horses autojoin
print("set_formation_leader_row ->", call(pawn, "set_formation_leader_row", unreal.Name("Test")))
tsc = pawn.get_thrall_system_component()
horses = [f for f in tsc.get_following_thrall_characters() if f.is_mountable()]
for h in horses:
    call(h, "set_formation_criteria_row", unreal.Name("Test"), True)
print("applied to", len(horses), "horses")

new = names() - before
print("NEW actors immediately:", sorted(new) if new else "(none)")
print("ConanCharacters AFTER:", chars())
print("is_formation_leader:", call(pawn, "is_formation_leader"))
