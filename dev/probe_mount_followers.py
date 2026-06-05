"""Discovery probe: find mount + follower/thrall related assets and classes.

Scans the asset registry for blueprints whose name/path hints at horses, mounts,
riding, saddles, thralls, pets, followers, and AI controllers. Also lists the
key native classes (UClass) if reflected, and dumps the mount component's
function/var surface. Read-only — no edits.

    python ue_run.py dev/probe_mount_followers.py
"""
import unreal

ar = unreal.AssetRegistryHelpers.get_asset_registry()

# Keyword buckets we care about
BUCKETS = {
    "mount/ride": ["mount", "ride", "rider", "saddle", "horse", "rhino", "camel"],
    "follower/thrall/pet": ["thrall", "follower", "pet", "companion", "tame"],
    "ai/behavior": ["aicontroller", "behaviortree", "bt_", "bb_", "_ai", "aibase"],
}

print("=== Scanning all assets (this can take a moment) ===")
all_assets = ar.get_all_assets(include_only_on_disk_assets=True)
print("total assets:", len(all_assets))

hits = {k: [] for k in BUCKETS}
for a in all_assets:
    try:
        name = str(a.asset_name).lower()
        path = str(a.package_name).lower()
    except Exception:
        continue
    blob = name + " " + path
    for bucket, kws in BUCKETS.items():
        for kw in kws:
            if kw in blob:
                hits[bucket].append(str(a.package_name) + "." + str(a.asset_name))
                break

for bucket in BUCKETS:
    rows = sorted(set(hits[bucket]))
    print("\n=== %s : %d hits ===" % (bucket, len(rows)))
    for r in rows[:120]:
        print("  ", r)
    if len(rows) > 120:
        print("   ... (%d more)" % (len(rows) - 120))
