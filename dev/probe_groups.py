import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()
print("TSC:", tsc.get_class().get_name())

# group counts (summary said get_follower_group_counts -> {"Mount":N,"Warrior":N,...})
for m in ("get_follower_group_counts", "get_follower_group_limits", "get_thrall_group_limits"):
    if hasattr(tsc, m):
        try: print(m, "->", getattr(tsc, m)())
        except Exception as e: print(m, "ERR", e)

# every TSC method mentioning group/limit/follow
print("\nTSC group/limit methods:")
print(sorted(x for x in dir(tsc) if any(k in x.lower() for k in ("group", "limit", "follow"))))

# which group is each following thrall in?
print("\nfollowers + their group:")
fols = tsc.get_following_thrall_characters()
for f in fols:
    grp = "?"
    for m in ("get_thrall_group", "get_follower_group", "get_group", "get_thrall_type"):
        if hasattr(f, m):
            try: grp = "%s=%s" % (m, getattr(f, m)()); break
            except Exception as e: grp = "ERR"
    # also any 'group' property/method on the thrall
    gmeths = [x for x in dir(f) if "group" in x.lower()]
    print("  %-34s mountable=%s grp[%s] groupmeths=%s" % (
        f.get_class().get_name(),
        f.is_mountable() if hasattr(f, "is_mountable") else "?", grp, gmeths[:5]))
