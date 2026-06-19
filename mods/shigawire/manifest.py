"""Deploy manifest for the Shigawire mod -- consumed by `/deploy` and
bpkit/ops/deploy.py. Declares the ordered build steps and any source assets to
import. Shared metadata (package, asset names, version, tunables) lives in
sw_config.py; this file is just the deploy *plan*.

    & $py ue_run.py bpkit/ops/deploy.py shigawire

PREREQ: the "Shigawire" mod must exist in the DevKit (Mods tool -> create mod) and be
the ACTIVE mod, else /Game/Mods/Shigawire is not writable and the build steps dry-run
into /Game/_Scratch. Cook must show the BPs as (Mod Asset) -- see sw_config.py.

STATUS: scaffold only. No build steps yet -- the mechanic (player-pull + enemy CC)
must be de-risked first via the read-only recon in FEASIBILITY.md (00_recon.py, a
diagnostics probe, NOT a build step). BUILD stays empty until that recon confirms the
native primitives exist.
"""
import sw_config as _cfg

NAME = "shigawire"
OUTPUT_PKG = _cfg.OUTPUT_PKG

# Ordered build steps, run in the live editor with Play STOPPED. 00_recon.py /
# 00b_recon_detail.py are read-only diagnostics, NOT build steps (excluded).
# Order: 01 clones the template BPs -> 02 builds the item rows (reference the clones) ->
# 03 the controller merges those rows into the game ItemTable -> 04 authors the pull on
# the cloned projectile. Steps are idempotent (re-deploy safe).
# TODO (gated on the cook+play test of the pull): 05 enemy flinch (add_stagger via a
# sphere-overlap at impact) + the cosmetic CableComponent rope.
BUILD = ["01_assets.py", "02_item_table.py", "03_controller.py", "04_projectile.py"]

# Source assets to import BEFORE building (meshes/anims/textures shipped with the mod):
#   {"src": "assets/Foo.fbx", "dest": OUTPUT_PKG, "name": "A_Foo", "replace": True}
# 'src' is relative to this mod folder unless absolute. Empty for now.
ASSETS = []

# NOTE for when build steps land: bpkit/ops/deploy.py line ~46 pops only "manifest" and
# "mf_config" from the editor module cache between deploys. Generalize it to also drop
# this mod's config ("sw_config") or a re-deploy may read a stale sw_config.
