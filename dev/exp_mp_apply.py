import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
def call(o, n, *a):
    try: return getattr(o, n)(*a)
    except Exception as e: return "ERR(%s)" % str(e)[:40]
pc = unreal.GameplayStatics.get_player_controller(world, 0)
host = pc.get_controlled_pawn()
tsc = host.get_thrall_system_component()

# 1) raise caps for all the humanoid follower groups so you can recruit more thralls
for grp in ("Warrior", "Crafter", "Bearer", "Performer", "Archer"):
    call(tsc, "add_thrall_group_limit_adjustment", unreal.Name(grp), 5)
print("raised caps. groups now:", call(tsc, "get_follower_group_counts"))

# 2) actor-attach each humanoid follower to a distinct spare (unridden) horse
fols = tsc.get_following_thrall_characters()
spares = [f for f in fols if f.is_mountable() and call(f, "get_rider") is None]
hums = [f for f in fols if not f.is_mountable()]
R = unreal.AttachmentRule.SNAP_TO_TARGET
print("spares:", len(spares), "humanoids:", len(hums))
for i, h in enumerate(hums):
    if i < len(spares):
        horse = spares[i]
        h.set_actor_enable_collision(False)
        cm = h.get_character_movement() if hasattr(h, "get_character_movement") else None
        if cm: call(cm, "disable_movement")
        call(h, "attach_to_component", horse.get_editor_property("Mesh"), "attachrider", R, R, R, False)
        h.set_actor_relative_location(unreal.Vector(0, 0, 90), False, False)
        print("  attached", h.get_class().get_name(), "->", horse.get_class().get_name())
print(">> recruit a 2nd thrall now if you want; then we can rebuild the manager properly.")
