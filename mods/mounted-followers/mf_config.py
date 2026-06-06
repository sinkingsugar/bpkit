"""Metadata for the mounted-followers mod -- the single place that decides WHERE the
mod's generated Blueprints are written and what they're called.

The builders (00_recon / 01_recipe / 02_manager / 02a_manager_minimal) all read
from here, so changing OUTPUT_PKG moves the whole mod in one edit.

Imported by the builders via bpkit.config.REPO_ROOT (so it works no matter the cwd).
"""

# Content package the generated Blueprint assets are written to.
# NOTE: this kit is a sandbox project. /Game/Mods is READ-ONLY base content here
# (save_asset fails there), so use a writable project-content root. When you spin
# up the real mod project, point this at THAT mod's writable content root -- every
# builder follows automatically. Verified writable in this kit: /Game/MountedFollowers,
# /Game/_Scratch, /Game/ModsShared.
OUTPUT_PKG = "/Game/MountedFollowers"

# Asset names within OUTPUT_PKG.
MANAGER = "BP_MountedFollowerManager"   # the ModController manager (the mod itself)
RECIPE = "BP_MF_Recipe"                 # the Stow/Restore cosmetic-mount recipe

# Stamped on the manager CDO so you can tell which build actually spawned.
MGR_VERSION = 25

# Seated idle pose played on a stowed rider (full object path).
IDLE_ANIM = ("/Game/Characters/humans/animations/mounted/Horse/"
             "A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")


def full(name):
    """'/Game/.../Name.Name' object path for an asset NAME in this mod's package."""
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
