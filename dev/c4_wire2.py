import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

# find the NEW horse: a Mounts_Horse not already following the player
horses = [c for c in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.ConanCharacter)
          if "Mounts_Horse" in c.get_class().get_name()]
print("horses in world:", [(h.get_name(), h.get_followed_player_controller() == pc) for h in horses])
new = next((h for h in horses if h.get_followed_player_controller() != pc), None)
print("new (unfollowing) horse:", new.get_name() if new else None)
if not new:
    print("!! no free horse (summon may still be deferred — re-run)"); raise SystemExit

tc = new.get_thrall_component()
print("new horse thrall comp:", tc.get_class().get_name() if tc else None)
print("Mount count BEFORE:", tsc.get_follower_group_counts())
tsc.set_following(tc, True, True)
print(">>> set_following(newHorseThrallComp, True)")
print("Mount count AFTER :", tsc.get_follower_group_counts())
print("new horse now follows player:", new.get_followed_player_controller() == pc)
