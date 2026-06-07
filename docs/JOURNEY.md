# The journey — provenance

How the framework and the mounted-followers mod were actually built. This is the
**narrative record** so the one-off reverse-engineering scripts don't have to be
kept: ~200 throwaway probe/diagnostic scripts produced the findings now distilled
into [INTERNALS.md](INTERNALS.md) and [CONAN-NOTES.md](CONAN-NOTES.md) and were
removed. The reusable tools and the mod source that survived are noted below.

---

## Part 1 — reverse-engineering the bridge

1. **Confirm the wall.** Probing the stock `unreal` API showed it can create
   assets, edit vars, and compile, but cannot read or build graph nodes — no
   `ImportNodesFromText`, graph node lists unexposed. (→ motivated everything.)
2. **Find the exported C++ entrypoints.** A dependency-free PE export dumper
   (`bpkit.pe`) located the decorated symbol names for `ImportNodesFromText`,
   `ExportNodesToText`, `GetAllGraphs`, etc. in the loaded editor DLLs. In-process
   `ctypes` resolves them by address.
3. **Prove WRITE.** A schema-trivial comment node pasted via `ImportNodesFromText`,
   then compiled + saved — isolated the paste mechanism. `CanImportNodesFromText`
   turned out to be a non-destructive **oracle** for "is this text acceptable."
4. **Read the struct layouts off live sets.** Pure-read byte introspection of
   UE-built `TSet`s nailed the field offsets (see INTERNALS §3) without ever
   risking a crash.
5. **Hit and defeat the read-path crash.** `ExportNodesToText` takes its `TSet`
   **by value** and `~TSet`-frees the element buffer; a ctypes-allocated buffer
   → heap corruption + a *delayed* crash (two editor crashes to diagnose). Fix:
   allocate the element buffer with the engine's `FMemory::Malloc`. Validated by
   `memcmp` against a real set *before* exporting, then proven by reading an entire
   production blueprint (`BP_BatDemonGlider`: 19 graphs, ~950 nodes, 2.8 MB) with
   zero crashes.
6. **Authoritative node reads.** `UEdGraph::Nodes` read directly (`graph_nodes`)
   instead of `GetObjectsWithOuter`, which surfaces undo-buffer orphans after edits.
7. **Authoring patterns.** Discovered from real exported nodes and validated by
   compile: the typed-pin orphan trap, array nodes as `CallArrayFunction`/
   `GetArrayItem`, the inert-`ForEach`/`ResolvedWildcardType` rule, component
   getters as typed `VariableGet`, and that "compiled" ≠ "no errors" (INTERNALS §8).

This crystallized into the `bpkit` package: `bridge` (IO), `ir` (model), `author`
(DSL), `compact` (navigation), `pe` (symbol discovery).

## Part 2 — the mounted-followers mod

Goal: make thralls/pets ride their own horse and keep pace, instead of sprinting
on foot while you ride. Full design audit + verdict:
[`mods/mounted-followers/FEASIBILITY.md`](../mods/mounted-followers/FEASIBILITY.md).

- **C0 — recon.** Established the four build facts: player pawn class; the recipe
  component/anim APIs are reflected + BlueprintCallable; the persistent hook is a
  `DreamworldMods.ModController` subclass; mount/rider state is readable.
- **Feasibility verdict (live PIE).** The real mount system **cannot** be
  repurposed for AI riders in a content-only kit — native seat is input-gated and
  refuses a clientless rider (CONAN-NOTES → Mounting). The shipping fact that
  rescues it: a horse is already a **pet that follows you** (`is_pet=True`). →
  Ship a **cosmetic composite**: real horse follows as a pet, thrall attached to
  its `attachrider` socket in a seated pose.
- **C1 — recipe as compiled Blueprint.** `Stow`/`Restore` authored as K2 node
  graphs (attach mesh → socket, freeze, seated idle / reverse), injected from
  outside the editor, compiled clean, live-verified both directions on a dancer NPC.
- **C2 — polling manager.** `BP_MountedFollowerManager : ModController`: raises the
  Mount cap (guarded init on tick), detects mount/dismount via `get_rider` truth
  (not the broken `get_mount`), 2-pass spare-horse-per-follower pairing, runs the
  C1 stow/restore inline. Killed a string of bugs: `get_mount`→`get_rider`, inert
  ForEach, `IsMount`→`IsMountable`, wildcard `Array_Length`, SpareHorse grabbing
  the player's own mount.
- **C3/C4 — scaling.** Distinct horse per follower (index-aligned `SpareHorses[]` +
  `HumanoidCounter`, guarded by an int-range test — `IsValid` won't merge onto a
  `GetArrayItem.Output` pin); per-group cap raises (`Mount` *and* `Warrior`).
- **C5 — multiplayer.** The hard part. Made it work on a listen-server by: CDO
  `always_relevant=True` (else the logic actor is never relevant to clients →
  everything dead there), **actor-attach** (replicates; mesh-attach doesn't), the
  `K2_` detach prefix, and a non-gated client-side cosmetic loop re-applying the
  seated pose from replicated state. (Full MP findings in CONAN-NOTES.)

### What survived from the build
- **Mod source** (reproduces the product) → [`mods/mounted-followers/`](../mods/mounted-followers/):
  the recon, the C1 recipe builder, the canonical C2 manager builder (the latest,
  MP-ready `MgrVersion`), the smallest "Step A" teaching slice, the ForEach and
  array-node regression tests, and an un-stow recovery utility.
- **Reusable tools** → [`bpkit/ops/`](../bpkit/ops/): editor liveness ping, PIE
  play/stop/state control, host-side modal rescue, scratch-asset cleanup, log tail,
  compile-error scan.
- **Everything else** (~200 probe/diagnostic/superseded scripts, plus a separate
  sorcery-ritual recon thread for RecallCorpse/RaiseDead that never became a
  product): distilled into the docs and removed. The git history preserves them if
  ever needed.
