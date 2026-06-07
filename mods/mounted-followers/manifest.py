"""Deploy manifest for the mounted-followers mod -- consumed by `/deploy` and
`bpkit/ops/deploy.py`. Declares the ordered build steps and any source assets to
import. Shared metadata (asset names, output package, version, anim) lives in
mf_config.py; this file is just the deploy *plan*.

    & $py ue_run.py bpkit/ops/deploy.py mounted-followers
"""
import mf_config as _cfg

NAME = "mounted-followers"
OUTPUT_PKG = _cfg.OUTPUT_PKG

# Ordered build steps, run in the live editor with Play STOPPED. 00_recon.py is
# read-only diagnostics, not a build step, so it's intentionally excluded; the
# manager (02) is the mod itself and the recipe (01) is its cosmetic-mount asset.
BUILD = ["01_recipe.py", "02_manager.py"]

# Source assets to import BEFORE building (anims / meshes / textures shipped with
# the mod). Empty here -- this mod reuses an existing engine animation
# (mf_config.IDLE_ANIM) instead of shipping its own. Spec per item:
#   {"src": "assets/Foo.fbx", "dest": OUTPUT_PKG, "name": "A_Foo", "replace": True}
# 'src' is relative to this mod folder unless absolute. The import path is wired in
# bpkit/ops/deploy.py but unexercised until a mod actually ships an asset here.
ASSETS = []
