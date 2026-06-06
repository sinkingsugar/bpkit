import unreal
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
if world is None:
    print("NO PIE -- press Play"); raise SystemExit
pc = unreal.GameplayStatics.get_player_controller(world, 0)
pawn = pc.get_controlled_pawn()
tsc = pawn.get_thrall_system_component()

def rd(o, n):
    try: return o.get_editor_property(n)
    except Exception as e: return "ERR(%s)" % str(e)[:25]
def call0(o, n):
    try: return getattr(o, n)()
    except Exception as e: return "ERR(%s)" % str(e)[:25]

# --- API: param names for the formation calls ---
print("=== formation API signatures ===")
for n in ("join_formation", "set_formation_criteria_row", "set_formation_leader_row",
          "can_autojoin_formation", "leave_formation"):
    m = getattr(unreal.ConanCharacter, n, None)
    print(" ", n, "::", (m.__doc__ or "NONE").splitlines()[0] if m else "MISSING")

# --- player: does it lead a formation? ---
print("\n=== player formation state ===")
print("  is_in_formation:", call0(pawn, "is_in_formation"))
print("  is_formation_leader:", call0(pawn, "is_formation_leader"))
print("  leader_comp:", call0(pawn, "get_my_formation_leader_component"))
print("  formation_criteria_name:", rd(pawn, "formation_criteria_name"))

# --- followers ---
print("\n=== followers formation state ===")
for f in tsc.get_following_thrall_characters():
    print("  %-30s in_form=%s autojoin=%s follower_comp=%s crit=%s" % (
        f.get_class().get_name(), call0(f, "is_in_formation"),
        call0(f, "can_autojoin_formation"),
        "yes" if call0(f, "get_my_formation_follower_component") not in (None, "") and "ERR" not in str(call0(f, "get_my_formation_follower_component")) else call0(f, "get_my_formation_follower_component"),
        rd(f, "formation_criteria_name")))

# --- look for formation criteria DataTables / assets ---
print("\n=== formation assets in /Game ===")
ar = unreal.AssetRegistryHelpers.get_asset_registry()
hits = []
for a in ar.get_all_assets():
    nm = str(a.asset_name)
    if "formation" in nm.lower() or "Formation" in nm:
        hits.append("%s  [%s]" % (nm, a.asset_class_path.asset_name))
    if len(hits) >= 25: break
print("\n".join(hits) if hits else "(none found by name)")
