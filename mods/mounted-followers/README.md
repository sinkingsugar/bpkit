# Mounted Followers (Conan Exiles)

A mod that makes your thralls/pets **ride their own horse and keep pace** with you,
instead of sprinting on foot while you ride. Authored entirely from outside the
editor with [`bpkit`](../../README.md) — compiled Blueprint logic, **no C++, no
runtime Python**. Verified working in single-player and multiplayer (listen-server).

A spiritual successor to the author's original **Mounted Followers for Skyrim**
(Nexus Mods) — same itch, fifteen years and one engine later, this time built by
an AI driving the dev kit. The Workshop blurb lives in [DESCRIPTION.txt](DESCRIPTION.txt).

This is the reference **application** of the framework. The hard-won, live-verified
Conan facts behind it are in [`docs/CONAN-NOTES.md`](../../docs/CONAN-NOTES.md); the
full design audit + verdict is in [FEASIBILITY.md](FEASIBILITY.md).

## How it works (one paragraph)

Conan's real mount system can't seat an AI rider from script (it's native and
input-gated). But a horse is already a *pet that follows you* (`is_pet=True`), so
the mod is a **cosmetic composite**: a persistent `ModController` manager polls the
player's mount state each tick (via `get_rider`, since `get_mount` is broken), and
when you mount it **attaches each humanoid follower's actor to a spare horse's
`attachrider` socket**, freezes it, and plays a seated idle pose — then reverses it
on dismount. Each follower gets its own horse; follower caps are raised per group.
MP works because the manager is `always_relevant` and uses **actor-attach** (which
replicates) plus a non-gated client-side cosmetic loop.

## Deploy (one command)

**In Claude Code:** `/deploy mounted-followers` — builds the whole mod from its
[`manifest.py`](manifest.py) (runs `01_recipe` → `02_manager` in order, imports any
source assets, verifies). Run with **Play stopped**.

Equivalent manual command:

```powershell
& $py ue_run.py bpkit/ops/deploy.py mounted-followers
```

## Build sequence (step by step)

The same steps run individually, via the editor's bundled Python (see the
[root README](../../README.md) for `$py`):

```powershell
& $py ue_run.py mods/mounted-followers/00_recon.py            # read-only recon (the 4 build facts)
& $py ue_run.py mods/mounted-followers/01_recipe.py           # Stow/Restore recipe on a scratch BP
& $py ue_run.py mods/mounted-followers/02_manager.py          # THE mod: the full manager (canonical)
```

| Script | Role |
|---|---|
| `00_recon.py` | read-only recon: player pawn, recipe APIs, the ModController hook, mount-state reads |
| `01_recipe.py` | authors the cosmetic-mount `Stow`/`Restore` (attach + freeze + seated pose / reverse) on a scratch Actor BP |
| `02_manager.py` | **canonical mod** — `BP_MountedFollowerManager : DreamworldMods.ModController` (MP-ready; version-stamped from `mf_config.MGR_VERSION`). Has a built-in orphan + compile self-check (`BUILD OK`). |
| `02a_manager_minimal.py` | smallest teaching slice: a `BeginPlay` that just raises the `Mount` cap |
| `restore_all.py` | recovery utility — un-stow / reset all followers if the mod misbehaves |

The node mechanics this mod relies on (array nodes, ForEach iteration) have
deterministic regression tests in [`tests/`](../../tests/): `test_array_nodes.py`,
`test_foreach.py`, `test_bp_authoring.py`.

## Configuration

All mod metadata — the output content package, asset names, manager version, and the
seated idle anim — lives in [`mf_config.py`](mf_config.py); the builders read from it,
so changing `OUTPUT_PKG` moves the whole mod in one edit.

`OUTPUT_PKG` **must** be the mod's own content root (`/Game/Mods/<ModName>`, writable
when that mod is the *active* mod in the Dev Kit). Only assets there cook as
**(Mod Asset)**; a ModController cooked from anywhere else is a **(Base Asset)** that
loads but gets culled as `[1]Invalid class` in the packaged game — runs in PIE, dead
in the real game. Full packaging checklist (cook dialog, pak verification with
UnrealPak): [`docs/CONAN-NOTES.md`](../../docs/CONAN-NOTES.md) §Packaging.

## Status

**Shipping (experimental — feedback wanted, especially multiplayer/dedicated).**
Working SP + MP (listen-server), verified in the **cooked/packaged game** — including the leash fix (v31/v32: Conan's follower catch-up AI re-enables a
seated rider's movement; a per-tick server maintain pass re-pins it; cook-only repro).
v33 is the release build: identical logic, all on-screen diagnostics stripped.

Remaining polish (see [FEASIBILITY.md §9](FEASIBILITY.md)): combat behavior is an
accepted limitation (dismount to fight — mounted AI combat is player-gated native),
per-mount socket/pose tuning (camel/rhino), and persistence across relog (self-healing:
a relog respawns clean). The native **formation system** is a backburnered v2 path for
smoother group movement.
