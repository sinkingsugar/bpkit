---
name: deploy
description: Build and deploy a mod from this repo into the live Unreal editor — import its source assets, run its Blueprint build steps in order, then verify. Argument is the mod folder name under mods/ (or a path), e.g. mounted-followers.
argument-hint: <mod-name>
disable-model-invocation: true
---

Deploy the mod named in `$ARGUMENTS` as a **smart process**: get it built and verified, adapting on failure rather than just reporting one. `$py` = `bpkit.config.BUNDLED_PYTHON` (or `$env:BPKIT_PYTHON`).

## 1. Pre-flight
- Channel up: `& $py ue_run.py bpkit/ops/ping.py` (ENGINE_VERSION printed). If dead, point the user at `/setup`.
- The deployer itself **refuses to run during Play** (authoring compiles Blueprints, which breaks live instances) — if it prints `ABORT: Play-in-Editor is running`, ask the user to stop Play, then re-run.

## 2. Deploy
`& $py ue_run.py bpkit/ops/deploy.py $ARGUMENTS`

This reads `mods/$ARGUMENTS/manifest.py`, imports any source `ASSETS`, then runs each `BUILD` step (an ordinary editor-side payload) in order in one editor session. Each step prints its own result (e.g. `BUILD OK`). Ends with `=== DEPLOY <mod>: OK ===` or `N STEP(S) FAILED`.

## 3. On failure — adapt, don't just report
- A step that printed a compile/orphan problem: scan with `& $py ue_run.py bpkit/ops/compile_errors.py` (wildcard / `bOrphanedPin` / `ErrorMsg`), fix the offending node in that step's builder, re-deploy. Remember "compiled" ≠ "no errors".
- `NOT DEPLOYABLE: no manifest.py`: the mod folder needs a `manifest.py` declaring `BUILD = [...]` (ordered step files) — model it on `mods/mounted-followers/manifest.py`.
- An asset `-> FAILED`: check the `src` path in the manifest (relative to the mod folder) and that the source file exists; UE import factories are picky about extensions.

## 4. Report
Mod name → output package, which steps ran, asset imports, and the final verdict. If you fixed something to get it green, say exactly what.

## 5. Shipping ≠ deploying
`/deploy` only authors into the **editor** (`/Game/<Mod>`) for PIE testing; it does NOT package. The real game runs a separate **cook → pak** from the Dev Kit mod tool (e.g. `...\UE4\Saved\Mods\<Mod>\Output\<Mod>.pak`). If the user says "works in editor but not in the real/packaged game," it's almost always packaging, not the graph:
- The controller (any `mods/*/02_manager`-style logic) must cook as a **(Mod Asset)** — i.e. be authored under `/Game/Mods/<ModName>/` — or the packaged game culls it as `[1]Invalid class` (works in PIE, dead packaged). Confirm in the cook dialog. (`bRequiresLoadOnStartup` is NOT required — verified in the cooked game 2026-06-10.)
- Verify the cooked pak (don't trust it): `UnrealPak.exe <Mod>.pak -List` → extract → `UnrealPak.exe <Mod>-Windows.utoc -List` for the inner asset list (IoStore `.ucas` is Oodle-compressed — use `-List`, never grep). Shipping strips `PrintString`/`GetAll`; use `HUDShowFIFO` / `ClientHUDShowNotification` for visible diagnostics. Full write-up: `docs/CONAN-NOTES.md` §Packaging.
