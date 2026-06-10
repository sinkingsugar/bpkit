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
| `01_recipe.py` | **not built/shipped since v34** — the C1 proof-of-concept (standalone `Stow`/`Restore` recipe BP, superseded mesh-attach pattern); kept as the custom-event authoring example |
| `02_manager.py` | **canonical mod — the only built step** — `BP_MountedFollowerManager : DreamworldMods.ModController` (per-player, MP-ready; version-stamped from `mf_config.MGR_VERSION`). Has a built-in orphan + compile self-check (`BUILD OK`). |
| `02a_manager_minimal.py` | smallest teaching slice: a `BeginPlay` that just raises the `Mount` cap |
| `restore_all.py` | dev scratch (formation-testing era) — un-stow / reset followers in PIE if an experiment misbehaves |

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

## Debugging — the beacon system

Two flags at the top of [`02_manager.py`](02_manager.py) control built-in diagnostics
(redeploy after flipping either):

- **`DEBUG`** — PIE-only **PrintString beacons**, auto-stamped with the build version,
  authored at every *one-shot* beat (never per-tick — the level-triggered logic would
  spam 10/s). They show on screen, in the output log, and in the in-game `~` console
  (`LogBlueprintUserMessages`). PrintString is compiled **out of Shipping**, so a DEBUG
  build never shows players anything — but ship with `False` to keep the graph lean.
  - `+5 follower caps applied (new player)` — once per player pawn, seconds after spawn.
    *Not seeing this means the per-player pass is dead — check the paste-drop guard.*
  - `stowed a rider onto a spare horse` — once per rider on mount.
  - `sweep-restored a rider (dismount/orphan)` — once per rider on dismount (or orphan
    cleanup).
  - `statue rescue (unfroze a stranded rider)` — only when a rider's horse died mid-ride.
  - `leash maintain caught a re-mobilized rider` — log copy of the HUD_DIAG catch below.
- **`HUD_DIAG`** (default **off** — the shipped mod is silent) — an optional
  **ship-visible** `HUDShowFIFO` banner (*"kept a rider seated"*, once per ride, re-armed
  while on foot) when the maintain pass catches Conan's leash AI re-enabling a seated
  rider's movement. Know this before reaching for console logging instead: **a Shipping
  build logs NOTHING from Blueprint** — `PrintString` (screen + log + `~` console) is
  compiled to a no-op there, so the HUD feed is the *only* channel that reaches a real
  player. The leash bug also only reproduces in the cooked game, which is why this flag
  exists at all; flip it on if you ever need field confirmation the fix is firing.

Build-time self-checks printed by every deploy: orphaned-pin scan, unresolved-wildcard /
error-marker scan, and the **authored-vs-pasted node-count guard** (paste silently drops
nodes whose function doesn't exist on the build — see `docs/INTERNALS.md` §8; that
mechanism once shipped a dead build).

## Status

**Shipping (experimental — feedback wanted, especially multiplayer/dedicated).**
v34 is the release build: **per-player** (every player pawn is served — the earlier
`GetPlayerCharacter(0)` host-only limit is gone), level-triggered + idempotent
stow/restore (a follower whistled mid-ride saddles up; a global sweep restores any
seated rider no mounted player accounts for — covering dismounts, followers that
left the follow list mid-ride, and owners who logged out mounted), the v31/v32
leash maintain pass (cook-only repro), a statue rescue for riders whose horse died,
10 Hz polling (`tick_interval=0.1`) for server-scale perf, and zero diagnostics.

Verification status: v34 deployed clean (148 nodes, 0 orphans, 0 compile errors,
independent error-scan clean, 2026-06-10). The **cooked-game ride test is still
pending**; the underlying v32/v33 logic was verified in the cooked game SP + MP
(listen-server).

Remaining polish (see [FEASIBILITY.md §9](FEASIBILITY.md)): combat behavior is an
accepted limitation (dismount to fight — mounted AI combat is player-gated native),
per-mount socket/pose tuning (camel/rhino), and persistence across relog (self-healing:
a relog respawns clean). The native **formation system** is a backburnered v2 path for
smoother group movement.
