import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

# follow / formation / spacing / offset knobs on the TSC
print("=== TSC follow/format/offset/spacing/distance methods+props ===")
hits = [x for x in dir(tsc) if any(k in x.lower() for k in
        ("follow", "format", "spacing", "offset", "distance", "spread", "slot", "position"))]
print(hits)

# same on a following horse + its behavior/AI
fols = tsc.get_following_thrall_characters()
horse = next((f for f in fols if f.is_mountable()), None)
if horse:
    print("\n=== horse follow/offset/distance methods ===")
    print([x for x in dir(horse) if any(k in x.lower() for k in
           ("follow", "format", "spacing", "offset", "distance", "spread", "goal", "accept"))])
    # AIController?
    ai = horse.get_controller() if hasattr(horse, "get_controller") else None
    print("horse controller:", ai.get_class().get_name() if ai else None)
    if ai:
        print("AI follow/accept/distance:", [x for x in dir(ai) if any(k in x.lower() for k in
              ("follow", "accept", "distance", "radius", "goal"))][:20])
