import unreal
FACTOR = 3.0   # tweak me
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
lc = pawn.get_my_formation_leader_component()
print("leader comp:", lc.get_name() if lc else None)

td = lc.get_editor_property("formation_template_data")
members = td.get_editor_property("members")
print("slots before:")
new_members = []
for m in members:
    t = m.get_editor_property("transform")
    loc = t.get_editor_property("translation")
    print("   ", loc)
    loc = unreal.Vector(loc.x * FACTOR, loc.y * FACTOR, loc.z)
    t.set_editor_property("translation", loc)
    m.set_editor_property("transform", t)
    new_members.append(m)
td.set_editor_property("members", new_members)
lc.set_editor_property("formation_template_data", td)

# read back
td2 = lc.get_editor_property("formation_template_data")
print("slots after (x%.1f):" % FACTOR)
for m in td2.get_editor_property("members"):
    print("   ", m.get_editor_property("transform").get_editor_property("translation"))
print("DONE -- move around and see if spacing is better")
