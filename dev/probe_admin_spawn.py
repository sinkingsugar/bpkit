import unreal
# Conan admin/spawn function libraries + player-controller spawn/cheat methods
names = dir(unreal)
libs = [n for n in names if any(k in n for k in ("Admin","Cheat","Spawn","Summon")) and any(k in n for k in ("Library","Manager","Function","Component","Controller","Subsystem"))]
print("candidate libs/classes:", sorted(libs)[:40])
# player controller spawn/admin/summon/follow
pc = unreal.ConanPlayerController
print("\nPC spawn/admin/summon/cheat/follow methods:")
for m in sorted(dir(pc)):
    if any(k in m.lower() for k in ("spawn","admin","summon","cheat","make_follow","command_follower","give")):
        print("  ", m)
# Does GameplayStatics have finish_spawning_actor / any deferred?
print("\nGS *spawn*actor* / finish:", [m for m in dir(unreal.GameplayStatics) if "actor" in m.lower()])
