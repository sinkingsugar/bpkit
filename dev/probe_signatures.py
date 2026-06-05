"""Dump docstrings/signatures of the mount + follower API so we understand the
rider model (player-only vs any ConanCharacter), and enumerate the supporting
components/enums.

    python ue_run.py dev/probe_signatures.py
"""
import unreal

cc = unreal.ConanCharacter

MOUNT_FNS = [
    "mount", "dismount", "can_mount", "is_mountable", "is_mount",
    "get_mount", "get_rider", "bp_mount_server", "bp_dismount_server",
    "bp_pre_mount_server_client", "bp_post_mount_server_client",
    "get_closest_mounting_spot", "get_mount_input", "replicate_mount",
    "is_pet", "is_thrall", "is_companion", "is_formation_follower",
    "get_my_formation_follower_component", "get_followed_player_controller",
    "set_additional_follow_distance", "set_automove_from_command",
    "get_thrall_component", "get_thrall_system_component",
]
print("###### ConanCharacter mount/follower function signatures ######")
for fn in MOUNT_FNS:
    f = getattr(cc, fn, None)
    doc = (f.__doc__ or "").strip() if f else "<missing>"
    print("\n-- %s" % fn)
    print("   ", doc.replace("\n", "\n    "))


def dump_members(clsname, kwfilter=None):
    cls = getattr(unreal, clsname, None)
    print("\n###### %s ######" % clsname)
    if not cls:
        print("  <not present>")
        return
    for m in sorted(dir(cls)):
        if m.startswith("__"):
            continue
        if kwfilter and not any(k in m.lower() for k in kwfilter):
            continue
        print("  ", m)


dump_members("ThrallComponent")
dump_members("ThrallSystemComponent")
dump_members("FormationFollowerComponent")
dump_members("MountInput")
dump_members("ConanPlayerController", ["mount", "follow", "thrall", "pet", "command", "order", "ride", "saddle"])

# Enums
for en in ["AIFollowerOrderType", "AIFollowerTacticType", "FollowerType",
           "MountMovementState", "FollowingMessageType"]:
    e = getattr(unreal, en, None)
    print("\n###### enum %s ######" % en)
    if e:
        for m in dir(e):
            if not m.startswith("_") and m.upper() == m:
                print("   ", m)
