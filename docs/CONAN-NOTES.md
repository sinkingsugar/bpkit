# Conan Exiles — live-verified facts

Game/engine-specific knowledge learned by probing the running Conan Exiles
Enhanced Dev Kit (UE 5.6.1). This is the **application** layer — the generic
framework knowledge is in [INTERNALS.md](INTERNALS.md). Most of this was won
building the **mounted-followers** mod (see [JOURNEY.md](JOURNEY.md) and
[`mods/mounted-followers/`](../mods/mounted-followers/)).

Every claim here was verified live; where a claim corrects an earlier assumption,
the correction is noted.

---

## Class model

`mount`, `pet`, and `thrall` are all the **same native C++ class**
`/Script/ConanSandbox.ConanCharacter` with different flags/components:

```
BP_NPC_Mounts_Horse ─▶ BP_NPC_Wildlife_Hooved ─▶ ConanCharacter
BP_*_pet            ─▶ BaseBPWildlife         ─▶ ConanCharacter
humanoid thralls    ─▶                            ConanCharacter
```

The mount/follow logic lives in compiled `ConanSandbox` C++ — not editable, but
fully **reflected** to Python, which is how it was audited.

## Mounting

- **No Blueprint/Python call seats a rider** (player *or* NPC). `mount()`,
  `bp_mount_server`, `replicate_mount`, `bp_post_mount_server_client`, and the real
  trigger `bp_start_mount_process_client` all fail to actually seat from script —
  the `bp_*` functions are **hooks the native code calls**, not performers. The
  native seat runs only through the player input pipeline; an AI rider is refused
  (`bp_start_mount_process_client` → `False`). → For mounted *followers*, use a
  **cosmetic socket-attach**, not the real mount system.
- **`can_mount(rider)` is *not* player-gated** — returns OK (`None`) for an AI
  rider. Eligibility ≠ ability to seat.
- **`get_mount()` on the PLAYER returns `None` even while riding.** Detect mount
  state via the mount's `get_rider() == player` (ground truth: scan following
  horses). `get_mount_input()` lags/flakes — its `BP_MountInput` object is torn
  down and recreated each mount cycle, so `IsValid` reads false for a long window
  on remount.
- **`is_mountable` (creature-type, true = horse) is the discriminator** between a
  following horse and a humanoid thrall — **not** `is_mount` (mount-*state*, flips
  and is true-for-all at mount time).
- `GetEmbeddedSaddleId()` reads `None` even while a player is actively riding —
  **not** a "ridden/has-saddle" signal. Don't gate on it.

## Followers

- **Follower caps are per named group** on the player's `BP_ThrallSystemComponent`:
  groups include `Mount`, `Warrior`, `Crafter`, `Bearer`, `Performer`, `Archer`.
  Mounts live in their own `Mount` group, so a generic follower-count mod won't
  cover them. Raise a cap with `add_thrall_group_limit_adjustment("<Group>", N)`
  (additive, mod-safe). Default `Warrior`/`Crafter` cap was 1 (a 2nd thrall swapped
  out the 1st). **Runtime adjustments don't persist** — re-apply each session
  (the mod does it in the ModController's guarded init).
- Follow tuning: `set_additional_follow_distance(N)` staggers followers into a
  trailing line (avoids clustering/bumping at one follow point).
- AI controllers: humanoid thralls → `HumanAIController`; creatures/mounts →
  `CreatureAIControllerHooved`. Follow logic drives the follower's *own*
  `CharacterMovementComponent` — there is no native path where a follower drives a
  separate mount pawn (the exact gap that makes mounted followers unshipped).

## Persistent mod logic — the ModController hook

Persistent mod logic = a **`DreamworldMods.ModController` subclass** (an Actor with
`BeginPlay` + `Tick`). The framework auto-spawns any ModController subclass on play
— but **before the player exists**, so do player-dependent init on `Tick` guarded
by an `Initialized` bool, *not* in `BeginPlay`. Conan's stock template to inspect:
`/Game/Items/Example_modcontroller`. Stamp a version int on the CDO (e.g.
`MgrVersion`) so you can tell which class actually spawned (stale-class detection).

## Cosmetic mounted rider — the working recipe

Attach + freeze + pose, all content-only and scriptable from Blueprint:

- **Attach the rider's skeletal MESH** to the horse's **`attachrider`** socket
  (fallback `saddleSocket`) with `SnapToTarget`. Attaching the *actor/capsule*
  instead lands the body ~90u low and yaw-rotated −90° (the standard Character
  mesh-vs-capsule offset).
- **Freeze non-destructively** (never `Destroy` a persistent follower): unpossess +
  `disable_movement` (MOVE_NONE) + capsule collision off + actor collision off +
  physics off. **Keep the skeletal-mesh component ticking** — disabling its tick
  freezes animation evaluation. Use runtime setters on live components, not
  `set_editor_property`.
- **Pose:** force a seated single-node anim over the AnimBP —
  `set_animation_mode(ANIMATION_SINGLE_NODE)` + `play_animation(anim, loop=True)`
  after `stop_all_montages`. Idle clip:
  `/Game/Characters/humans/animations/mounted/Horse/A_human_mounted_idle_HORSE`
  (matches `SK_human_Skeleton`). 404 mounted/riding sequences ship in the kit.
- **Restore:** reverse — `ANIMATION_BLUEPRINT`, `MOVE_Walking`, collision on,
  re-attach mesh → capsule, and **restore the saved relative transform** (save
  `mesh.GetRelativeTransform()` *before* reparenting; re-attaching with
  `SnapToTarget` snaps to the capsule center → rider floats ~96u up). Run Stow
  **once** per mount — re-running while stowed re-saves the (attached, ~zero)
  transform and corrupts the restore.

## Multiplayer / replication (the crux of the MP build)

- **Relevancy first.** A logic-only actor (hidden root, no collision, no position —
  a typical ModController manager) is **never relevant to clients**, so it never
  replicates there: its `Tick`, Multicast RPCs, and replicated vars are all **dead
  on clients** even with `RemoteRole == SimulatedProxy`. This was the root cause of
  every "host-only" symptom. Fix: CDO `always_relevant = True`.
- **ModController does not tick on clients** unless made relevant → apply cosmetics
  (the seated single-node pose) **locally on each client** in a non-gated loop from
  replicated state; keep gameplay server-only behind `HasAuthority`. Add a reset
  branch (not-attached → restore AnimBP) so clients un-pose on dismount.
- **Actor-attach replicates; component/mesh-attach does NOT.** Attach the follower
  **actor** (`AActor::K2_AttachToComponent`, parent = horse mesh) → clients see it
  ride. Mesh-attach desyncs (host mounted, clients at origin). Relative loc/rot set
  after an actor-attach replicate with it.
- **BP attach/detach need the `K2_` prefix.** `K2_AttachToComponent` /
  `K2_DetachFromActor` are the BlueprintCallable versions; the plain C++ names
  (`DetachFromActor`) compile clean but **silently no-op** (this caused the whole
  dismount bug). Python method names drop the prefix (`detach_from_actor`).
- **Server-side animation does NOT auto-replicate.** `PlayAnimMontage` replicates;
  a single-node `play_animation` and a *transient/dynamic* slot montage do **not** —
  confirmed even on the host *player*. A replicating seated full-body pose needs a
  **real (saved) AnimMontage on the `Fullbody3rd` slot**, not a dynamic montage.
- **Emotes replicate:** `EmoteController.start_emote` multicasts and reaches clients
  (e.g. `CharacterEmotes.SIT_ON_GROUND`) — a promising replicated-pose path.
- Exclude **mountable creatures** (horses) and **other players**
  (`GetPlayerState` valid; `IsPlayerControlled` is false for other players'
  sim-proxies) from any "seat the attached characters" loop, or you apply human
  anims to horse skeletons.

## Spawning & PIE control

- **Spawn into the live game world with the `Summon <ClassPath>_C` console
  command** (deferred a frame; `load_object` the class first so it resolves).
  `EditorActorSubsystem.spawn_actor_from_class` lands actors in the **editor**
  world, not the PIE world. Summoned NPCs are under-initialized (no auto AI
  controller — possess one manually). Finite-lifespan NPCs (undead) vaporize when
  summoned ownerless; use a persistent follower.
- **PIE surface:** `LevelEditorSubsystem.is_in_play_in_editor` /
  `editor_request_begin_play` / `editor_request_end_play`;
  `UnrealEditorSubsystem.get_game_world()` (None when not playing);
  `editor_play_simulate` ticks AI+navmesh without a player pawn. **Do not start
  Play yourself — the user controls Play** (driving PIE once dropped the user into a
  bad session and cost trust). Read/experiment only in the user's own session.
- **Slate modals freeze the channel** (they block the game thread). Rescue from a
  *separate host process* over Win32: the editor's main `UnrealWindow` is DISABLED
  while the modal dialog window stays ENABLED+foreground → post Enter/Esc to the
  enabled one (`dev`-era `dismiss_modal.py`).

## Formation system (backburnered — a v2 path)

Native formations make mounted followers move as a smooth group. Activate via
`set_formation_leader_row("…")` on the player + `set_formation_criteria_row("…",
autojoin=True)` on each follower; widen slots via the leader component's
`formation_template_data`. Tables: `FormationsTemplateTable`,
`FormationCriteriaTable`; component `BP_FormationLeaderComponent`. Open issues:
slot rotation, tight-spot fail-safe, BP-baking.

## Finding native signatures — never fire blind

Calling a native UFunction with guessed/empty args to make the error "reveal" the
signature can **null-deref and crash the whole editor** (cost two PIE sessions).
Unreal's reflection already has every signature — read it instead:
- **Docstring:** every reflected function auto-generates a typed `__doc__`, e.g.
  `unreal.ConanCharacter.bp_mount_server.__doc__`. For a BP class:
  `t = type(unreal.get_default_object(cls)); print(t.start_emote.__doc__)`.
- **Enums:** `dir(unreal.CharacterEmotes)`; `<Enum>.<VALUE>.get_display_name()`.
- **BP graphs:** `bpkit.bridge.read_blueprint(path)` — the `K2Node_FunctionEntry`
  node lists typed param pins (PIE-independent, read-only).

Only after you know the real param **types**, make one call with correct args.
