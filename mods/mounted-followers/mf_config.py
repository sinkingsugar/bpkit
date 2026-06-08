"""Metadata for the mounted-followers mod -- the single place that decides WHERE the
mod's generated Blueprints are written and what they're called.

The builders (00_recon / 01_recipe / 02_manager / 02a_manager_minimal) all read
from here, so changing OUTPUT_PKG moves the whole mod in one edit.

Imported by the builders via bpkit.config.REPO_ROOT (so it works no matter the cwd).
"""

# Content package the generated Blueprint assets are written to. MUST be the MOD's own
# content root (/Game/Mods/<ModName>) so the cook tags them "(Mod Asset)" and Conan
# REGISTERS the ModController. Assets cooked from anywhere ELSE are "(Base Asset)" -> the
# ModController loads but is culled as "[1]Invalid class" in a packaged build (runs in PIE,
# dead in the real game -- the bug we chased 2026-06-08). /Game/Mods/<mod> is writable in
# the DevKit when that mod is the ACTIVE mod (verified writable 2026-06-08).
# (Old /Game/MountedFollowers was an editor-only sandbox shortcut -- NOT shippable.)
OUTPUT_PKG = "/Game/Mods/MountedFollowers"

# Asset names within OUTPUT_PKG.
MANAGER = "BP_MountedFollowerManager"   # the ModController manager (the mod itself)
RECIPE = "BP_MF_Recipe"                 # the Stow/Restore cosmetic-mount recipe

# Stamped on the manager CDO so you can tell which build actually spawned.
# 26 = Shipping-safe on-screen diagnostics (HUDShowFIFO heartbeat + mount/dismount banners).
# 27 = relocated to /Game/Mods/MountedFollowers so the controller cooks as a Mod Asset
#      (the fix for "Invalid class" / never registering in a packaged build).
# 28 = removed the on-screen debug messaging (the bForceInit=false default DIDN'T take -- it
#      silently reverted to autogen 'true', so anims were still broken).
# 29 = the anim fix done right: bForceInitAnimScriptInstance is now WIRED to a literal false
#      (a pin default reverts; a wire can't) so the cosmetic-loop reset no longer re-inits every
#      character's AnimBP every tick.
# 30 = the cosmetic seat now only applies when the attach PARENT is a mountable horse, so thralls
#      attached to benches/wheels/stations are no longer wrongly put in the saddle pose/offset.
MGR_VERSION = 30

# Seated idle pose played on a stowed rider (full object path).
IDLE_ANIM = ("/Game/Characters/humans/animations/mounted/Horse/"
             "A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")


def full(name):
    """'/Game/.../Name.Name' object path for an asset NAME in this mod's package."""
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
