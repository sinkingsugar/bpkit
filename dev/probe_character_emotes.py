import unreal
ce = getattr(unreal, "CharacterEmotes", None)
print("CharacterEmotes type:", ce)
if ce:
    vals = [v for v in dir(ce) if not v.startswith("_")]
    print("count:", len(vals))
    print("ALL values:", vals)
    # highlight sit/mount/idle/dance
    print("\nsit/mount/idle:", [v for v in vals if any(k in v.lower() for k in ("sit","mount","idle","ride","rest","kneel"))])
