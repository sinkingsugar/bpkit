# Mounted Followers — Audit & Feasibility Report

**Question:** Can thralls/pets be made to *mount up* (ride their own horse/rhino) and
keep pace with the player, instead of sprinting on foot while you ride?

**Method:** Live reflection + Blueprint-graph reads against the running CEUE5 Dev Kit
(UE 5.6.1, `ConanSandbox`) over the Python remote-execution channel, 2026-06-05.
No guessing — every claim below is backed by a probe in `dev/probe_*` /
`dev/read_*` and a dump in `dump_*.txt`.

> **Historical note.** The one-off `dev/*` probe scripts cited throughout this report
> were removed in the framework cleanup; their findings are distilled into
> [`docs/CONAN-NOTES.md`](../../docs/CONAN-NOTES.md) and [`docs/JOURNEY.md`](../../docs/JOURNEY.md),
> and the scripts remain in git history. The mod builders they produced live alongside
> this file (`00_recon.py` … `02_manager.py`).

---

## TL;DR / Verdict

**UPDATED after live PIE testing (see §7).** The static audit suggested this was
*only* a locomotion problem; the live test proved there is **also a seating wall**.

- ✅ **Eligibility is not player-gated.** `ConanCharacter::CanMount(npc)` returns OK
  for an AI (undead-thrall) rider against a real mount — no player-only type check at
  the eligibility layer.
- ❌ **The mount *action* IS effectively player-gated and not script-reachable.** Every
  way to actually *seat* a rider from Blueprint/Python failed — `Mount()`,
  `BPMountServer()`, and the real trigger `BPStartMountProcessClient()` (which returned
  **False** for an AI rider). They don't even seat the *player* when called directly;
  the player only mounts via the genuine input-driven native process. The `BP*Mount*`
  functions are **hooks the native code calls**, not entry points that perform mounting.
- 🔒 **Therefore, reusing Conan's real mount system for an AI rider is NOT achievable in
  a content-only kit.** The seat logic lives in native C++ reachable only through the
  player's input pipeline; an AI follower has no client to drive it. Doing it "properly"
  would need a C++/source change the Enhanced Dev Kit cannot compile.
- 🟢 **The realistic content-only path is a cosmetic composite** (see §3, Approach C),
  made cheaper by one shipping fact: **mounts are already pets that follow you**
  (`BP_NPC_Mounts_Horse` has `is_pet=True`). So you can let the *real horse* follow as
  a pet and **attach the thrall to its saddle socket** — a "fake" mount that keeps perfect
  pace, without touching the locked native mount system.
- 🏆 **PROVEN LIVE (2026-06-05, §8):** a Fighter NPC was attached to the horse's own
  `attachrider` socket, frozen non-destructively, and posed with the kit's
  `A_human_mounted_idle_HORSE` clip — it rode the moving horse correctly (screenshot
  captured). Verdict moves from "cosmetic *might* work" to **"cosmetic works,
  demonstrated."** Recipe in §8.

> Note: `is_mountable()` is a class-level *true* and `GetEmbeddedSaddleId()` reads
> `None` **even while a player is actively riding** — so neither is a reliable "is
> ridden / has saddle" signal. The authoritative live signal is `mount.GetRider()`
> (returns the player when mounted; stayed `None` for every AI-seat attempt).

Confidence: **high** on the architecture/audit AND now on the seating verdict (live-
verified); **medium** on cosmetic-approach effort, pending the
§6 locomotion test.

---

## 1. How the shipping systems actually work

### Class hierarchy (probe: `dev/probe_parents2.py`)
Everything is one native base:

```
BP_NPC_Mounts_Horse ─▶ BP_NPC_Wildlife_Hooved ─▶ /Script/ConanSandbox.ConanCharacter
BP_NPC_Wildlife_*_pet ─▶ BaseBPWildlife        ─▶ /Script/ConanSandbox.ConanCharacter
BP_*UndeadThrall / humanoid thralls            ─▶ /Script/ConanSandbox.ConanCharacter
```

So **mount, pet, and thrall are all the same C++ class** with different flags/components.
The mount/follow logic lives in compiled `ConanSandbox` C++ — we can't edit it, but the
PythonScriptPlugin exposes its full reflected surface, which is how this audit was done.

### The mount API on `ConanCharacter` (probe: `dev/probe_signatures.py`)
All `BlueprintCallable`, so reachable from our Blueprints:

| Call (on the **rider**)              | Signature / meaning |
|--------------------------------------|---------------------|
| `mount(mounted_npc: ConanCharacter)` | Seat this character on `mounted_npc`. **Any ConanCharacter.** |
| `dismount(force: bool)`              | Get off. |
| `can_mount(mounted_npc) -> Text?`    | Collision pre-check; returns an error string or None=ok. |
| `get_mount() / get_rider()`          | The replicated rider↔mount link. |
| BP hooks: `bp_pre_mount_server_client`, `bp_post_mount_server_client(…, from_right_side)`, `bp_mount_server`, `bp_dismount_server`, `bp_cancel_mount_client` | **Overridable in Blueprint** — our injection points. |
| `get_closest_mounting_spot(rider)`   | Called *on the mount*; where the rider walks to before mounting. |
| `get_mount_input() -> MountInput`    | The steering component (see below). |

Replication is built in: `replicate_mount`, `signal_mount_replicated`,
`ConanCharacter_SignalMountReplicated`, `ConanCharacter_MountStaggered`.

### Steering = player input (probe: horse `MountableInterface` graph, `dump_BP_NPC_Mounts_Horse.txt`)
`MountInput` is an input component: `get_controller_analog_stick_state`,
`consume_input_key`, `enable_autorun`, `get_current_mount_movement_state`
(`MountMovementState`: STAND/WALK/RUN/SPRINT/BACKPEDALING). The horse's
`MountableInterface` graph handles `JumpActionPressed` and `Brake`.
**→ A ridden mount moves because a *player controller* feeds it input.** Remove the
player and, as-is, nothing tells the mount to move.

### Follower / thrall AI (probes: `dev/probe_native_api.py`, `dev/probe_cdo2.py`)
- Follow target: `get_followed_player_controller()`, `set_additional_follow_distance()`,
  `set_automove_from_command()`, `command_follower()` on `ConanPlayerController`.
- Orders: `AIFollowerOrderType` = NONE/MOVE/ATTACK/HOLD/FLEE/RETURN;
  tactics `AIFollowerTacticType` = CHASE/HOLD/WITHDRAW/PRIORITIZE_BASED_ON_WEIGHT.
- Movement: `ConanPathFollowingComponent` / `ConanNewPathFollowingComponent`, plus a
  full **`FormationFollowerComponent`** (`join_formation`, `change_formation_slot`,
  blackboard keys `bb_key_formation_leader/slot/template/in_formation`).
- AI controllers: humanoid thralls → `HumanAIController`; creatures/mounts →
  `CreatureAIController*` (mounts specifically `CreatureAIControllerHooved`).
- **The follow logic drives the follower pawn's own `CharacterMovementComponent`/legs.**
  There is no code path where a follower drives a *separate* mount pawn.

### The crucial hint: **a mount is already a pet** (probe: `dev/probe_cdo2.py`)
`BP_NPC_Mounts_Horse` CDO has **`is_pet = True`**. Your horse is a *tamed pet that
already follows you* when you're not riding it. And `is_mountable` is a **computed
function** (driven by `FindSaddleData` → saddle/datatable), not a stored bool — so
mountability is "does it have a saddle," which we control via data.

---

## 2. Why followers don't mount today (the exact gap)

Putting it together, the missing piece is a single thing:

> **No system makes an AI-controlled mount *move to follow the player while it has a
> rider*.** Seating works; replication works; the mount can even already follow you as a
> pet *when empty*. But the moment it's "ridden," movement is expected to come from
> player `MountInput`, and the follower AI has no concept of "drive that other pawn."

This matches Funcom's known design history: mounts (Riders of Hyboria, 2020) shipped
after the thrall/pet follower system, and mounted followers were never wired up —
exactly the "half-baked, came later" situation you suspected.

---

## 3. Feasibility approaches (content-only kit, no C++)

We can edit/author Blueprints, override the `bp_*_mount_*` hooks, call any
BlueprintCallable native function, set CDO defaults, and add components — but we can't
touch the C++ movement/AI. Within that:

### Approach A — **"Mount is the follower, thrall is the passenger"**  ❌ DISPROVEN (live, §7)
- *Original idea:* make the **horse** the registered follower (it already does this:
  `is_pet=True`, `CreatureAIControllerHooved`, follows when empty), then server-side seat
  the thrall with `thrall.mount(horse)` and let the horse's AI carry it.
- **Why it's dead in a content-only kit:** the §7 live test showed there is **no
  Blueprint/script call that seats a rider** — `mount()`, `bp_mount_server()`, and the
  real trigger `bp_start_mount_process_client()` all fail to seat *even the player*; the
  seat only happens via the native, player-input-driven mount process, which returns
  **False** for an AI rider. So we never even reach the "does the mount still move"
  question — we can't get the rider on. This would require C++ (unavailable here).
- Effort: **N/A** — blocked at the seating step.

### Approach B — **"Thrall drives the mount via its own AI"**
- Thrall mounts; we translate the thrall's path-follow output into synthetic
  `MountInput` (`MountInput.input_key` / analog state / `enable_autorun`).
- Most faithful (uses the *real* mount locomotion + animations) but the hardest:
  we'd be reverse-engineering and feeding the input pipeline frame-by-frame from BP,
  fighting a system built for a human at a gamepad. High risk of jank.
- Effort: **high.** Risk: **high.** Recommend only if A's mount-AI is hard-disabled
  *and* you want true mounted locomotion fidelity.

### Approach C — **"Cosmetic composite follower"**  ✅ the realistic content-only path
Two flavours, both avoiding the locked native mount system entirely:

**C1 — Real-horse pet + attached rider (recommended).** Exploit `is_pet=True`: let an
actual `BP_NPC_Mounts_Horse` follow the player as a normal pet, and **attach the thrall
to the horse's saddle socket** (`AttachToComponent`, rider seat bone). The horse's own
pet-follow AI keeps perfect pace; the thrall is just parented on top in a seated pose.
No `mount()` call, so the player-gated wall in §7 never applies. You also get the real
horse mesh/animations for the *mount's* locomotion for free.

**C2 — Single composite pawn.** One follower pawn that *is* horse-mesh + rider-socket,
driven by the normal follower AI. Simplest to keep in sync, but you rebuild the horse
visuals per species.

- Downsides (both): "fake" mount — no real saddle interaction, no mount montage, the
  player can't take the horse over, thrall combat means detach→fight→re-attach, and the
  seated rider needs a sit/idle pose (reuse a rider anim or accept a default).
- Effort: **low–moderate.** Risk: **low.** This is the MVP that actually ships in a
  content-only kit.

---

## 4. Cross-cutting risks & details

- **Server authority / replication.** Mount/dismount must run server-side
  (`bp_mount_server`, `mount` is server-driven; state replicates via `OnRep_Mount` →
  `replicate_mount`). Our hooks fire `*_server_client`, so doable, but test in a
  listen-server/dedicated context, not just single-player.
- **Navmesh & mount footprint.** A mounted thrall now needs *horse-width* pathing.
  Conan mounts already pathfind as wildlife (`CreatureAIControllerHooved`) so the nav
  data exists, but follower paths were tuned for a humanoid capsule — expect
  clipping/stuck spots near builds and require `additional_following_distance` tuning.
- **Animation.** Generic NPCs lack the rider anim layer that players use on a saddle.
  The rider pose/blends may be player-`AnimBP`-specific; a thrall may need the player
  rider anim set retargeted, or it sits in a default pose (acceptable for MVP).
- **Combat & orders.** Decide behavior on ATTACK/HOLD: dismount to fight on foot
  (safe, matches current feel) vs. mounted combat (needs the rider attack anims +
  the mount to hold position — more work).
- **Follower cap / formation.** Mounted followers should still count against the
  follower limit and can ride `FormationFollowerComponent` slots — likely free reuse,
  but verify a mount pawn is an eligible formation member.
- **~~Saddle gating~~ (CORRECTED in §7).** `GetEmbeddedSaddleId()` returns `None` even
  while a player is actively riding, so it is **not** a saddle/ridden signal. Don't gate
  on it. The authoritative live signal is `mount.GetRider()`.

---

## 5. ~~What we could NOT determine statically~~ → now determined (§7)

The static audit's open question was "does `Mount()` disable the mount's AI/movement."
Live testing answered a more fundamental one first: **you can't even seat the AI rider
from script**, so the movement question is moot for the content-only path. See §7.

## 6. (superseded by §7 — the experiment was run)

---

## 7. Live validation — what actually happened in PIE (2026-06-05)

Ran in a real PIE/listen-server session (`/Game/Dev/AlmostEmpty`, has navmesh), player
character spawned, admin enabled. Actors created via the engine `Summon` console command
+ admin panel (a real `BP_NPC_Mounts_Horse_Knight4`, flagged `is_pet/is_thrall=True`).

**Findings, in order:**
1. **Spawn-into-PIE from the editor channel doesn't work** (`EditorActorSubsystem.
   spawn_actor_from_class` → `None`; no world-context spawn is exposed). Use the in-game
   `Summon` console command instead. Summoned NPCs are under-initialized — **no auto AI
   controller**; you must summon + `possess()` a controller (`HumanAIController_C`,
   `CreatureAIControllerHooved_C`) manually.
2. **`can_mount(AI rider)` → OK** (returns `None`). Eligibility is *not* player-gated. ✅
3. **`mount(horse)` → no-op.** `get_rider`/`get_mount` stay `None` for the AI rider
   *and* for the player when called directly. The rider just gets pulled to the mounting
   spot and stands there (observed in-world: "zombie sitting under the horse").
4. **`bp_start_mount_process_client(horse)` → `False`** for the AI rider — the real,
   input-driven trigger refuses a clientless rider.
5. **Direct server seat sequence fails:** `bp_pre_mount_server_client` → `False`,
   `bp_mount_server`/`replicate_mount` → no effect. These `bp_*` calls are **native-
   called hooks, not performers** — invoking them from script does nothing.
6. **Control test (decisive):** player mounts via normal input →
   `horse.GetRider()` returns the **player** correctly. So the measurement is valid, the
   horse is genuinely rideable, and the AI-seat failures in 3–5 are real, not artifacts.
   (Also: `GetEmbeddedSaddleId()==None` *while ridden* → saddle id is a red herring.)

**Verdict:** the mount **seat** is performed by native C++ reachable only through the
player input pipeline. No Blueprint/Python entry point seats a rider. An AI follower has
no client to drive it and is explicitly refused. **→ The real mount system cannot be
repurposed for AI riders in a content-only kit. Ship Approach C (C1).**

---

### Appendix — evidence artifacts (this session)
Static audit: `dev/probe_mount_followers.py`, `dev/probe_mount2.py` (asset discovery);
`dev/probe_parents2.py` (→ `ConanCharacter` native base); `dev/probe_native_api.py`
(mount/follow binding surface); `dev/probe_signatures.py` (signatures, enums,
`FormationFollowerComponent`, `MountInput`); `dev/probe_cdo2.py` (`is_pet=True` on the
horse); `dev/read_mountlib.py`, `dev/read_horse.py` + `dump_*.txt` (BP graphs:
`MountableInterface` = `JumpActionPressed`/`Brake`; `FindSaddleData`).

Live test: `dev/pie_step1_enter.py`, `dev/summon_actors.py`, `dev/summon_rider.py`,
`dev/mount_test_live.py`, `dev/mount_test_v2.py`, `dev/fix_ctrl_mount2.py`,
`dev/player_mount_test.py`, `dev/probe_mount_process.py`, `dev/start_mount_proc.py`,
`dev/server_seat.py`, `dev/snapshot_mounted.py` (the control test).

---

## 8. Working prototype — the proven recipe (live, 2026-06-05)

A Fighter NPC riding the player's following horse, posed correctly, horse moving
freely. The exact steps that worked (all content-only, scriptable from BP):

**Attach (key: attach the MESH ROOT, not the actor/capsule):**
- The mount mesh has purpose-built sockets — **`attachrider`** and `saddleSocket`.
- Attaching the rider *actor* (capsule root) to the socket lands the body ~90u low and
  yaw-rotated -90° (UE's standard Character mesh-vs-capsule offset). Instead, attach the
  rider's **skeletal mesh component** to `attachrider` with `SNAP_TO_TARGET` (loc+rot) →
  root bone sits exactly on the socket. Verified: `mesh.GetWorldLocation()` ==
  `hmesh.GetSocketLocation("attachrider")`.

**Freeze (non-destructive — never Destroy a persistent follower):**
- `CharacterMovement`: `disable_movement()` + `stop_movement_immediately()` +
  tick off + `set_active(false)`.
- Capsule: `set_collision_enabled(NoCollision)`; rider `set_actor_enable_collision(false)`.
- Mesh: collision off, `set_simulate_physics(false)`, `set_all_bodies_simulate_physics(false)`.
- **GOTCHA:** do **not** disable the skeletal-mesh component's tick — that stops
  animation evaluation and the pose freezes. Movement-comp + capsule disabled is enough
  to stop the rider pushing the horse; the mesh must keep ticking to animate.

**Pose:**
- 404 mounted/riding `AnimSequence`s ship in the kit; `A_human_mounted_idle_HORSE`
  (passive) and `A_human_mounted_combat_idle_HORSE` both match `SK_human_Skeleton`.
- Force it over the NPC's AnimBP: `mesh.set_animation_mode(ANIMATION_SINGLE_NODE)` +
  `mesh.play_animation(anim, loop=True)`, after `stop_all_montages`.

**The real mod (automation + reversal), no native mount system touched:**
1. On the **player**'s `BPPostMountServerClient(mounted_npc)` (server): enumerate the
   player's followers (`GetFollowedPlayerController()==myPC`), snapshot them, and for each
   do attach → freeze → pose against `mounted_npc` (the horse).
2. On `BPPostDismountServerClient` / `SignalDismountStart`: reverse — restore AnimBP
   (`set_animation_mode(ANIMATION_BLUEPRINT)`), re-enable movement/collision/tick,
   re-possess if needed, detach, teleport beside the player.
3. Run server-side; replicate attach/hidden state for MP.

**Caveats proven in the prototype:**
- Use a *persistent* follower, not the finite-lifespan undead test stand-in (it vaporized).
- Combat music in the test was the *summoned enemy* stand-in being hostile; the real
  feature uses the player's already-allied thrall, so it won't trigger combat.
- Remaining polish: per-mount socket/pose tuning (camel/rhino variants exist), and
  deciding combat behavior (auto-dismount to fight vs. mounted).

---

## 9. Roadmap / TODO

Status: **research + live single-rider prototype done (§7, §8); recipe now reproduced as
compiled Blueprint and live-verified (§10 / C1 done).** Remaining to make it a real mod:

- [x] **Recipe as compiled Blueprint (C1, done 2026-06-05).** `Stow`/`Restore` authored as K2
      node-graphs on `BP_MF_Recipe`, injected from outside the editor, compiled clean, and
      live-verified in PIE: `Stow` snaps a dancer's mesh onto the horse `attachrider` socket
      (distance 0.0); `Restore` detaches + restores `MOVE_Walking`. See §10.
- [x] **C2 logic chain — PROVEN LIVE 2026-06-05.** Full mount→detect→iterate→filter→act chain
      fires in PIE: `MGR VERSION=4` (fixed class spawns; rebuilds take effect with NO editor restart
      — the framework cache was never the real blocker), `MOUNT DETECTED` (via GetMountInput), ForEach
      iterates all followers (`followers seen=3`), `IsMountable` filter skips the 2 horses and fires
      `STOW A FOLLOWER` for the lone humanoid entertainer. Key discriminator: **IsMountable** (stable
      creature-type, true=horse) NOT IsMount (mount-STATE; flips, true-for-all at mount time). NB UE
      `LogBlueprintUserMessages` dedups identical strings -> make per-run debug strings unique (embed a
      counter/version) for full visibility. Remaining: replace the STOW *print* with the real action.
- [x] **C2 — Polling manager DONE & LIVE-VERIFIED 2026-06-05** (`BP_MountedFollowerManager :
      DreamworldMods.ModController`, authored by `dev/c2_build.py`). The follower visibly mounts a
      spare horse when the player mounts, and dismounts when the player does. Full behaviour:
      - Auto-spawns (framework picks up any ModController subclass) + auto-raises Mount cap once on
        tick, guarded by `Initialized` bool (auto-spawn precedes player spawn, so BeginPlay too early).
      - Detects mount/dismount via `IsValid(GetMountInput(player))` vs a `WasMounted` bool
        (`player.GetMount()` is BROKEN — mem `player-getmount-broken`).
      - On MOUNT (2-pass over `GetFollowingThrallCharacters`): **Pass A** picks a `SpareHorse` =
        a follower that `IsMountable` AND has no rider (`IsValid(GetRider)`==false → excludes the
        horse the player is on); **Pass B** for each non-mountable (humanoid) follower runs C1's
        attach chain inline (save mesh xform → attach to `attachrider` socket → freeze movement +
        collision → seated idle pose `A_human_mounted_idle_HORSE`).
      - On DISMOUNT: **Pass D** reverses it per humanoid (anim mode→AnimBlueprint, MOVE_Walking,
        collision on, re-attach mesh to capsule, restore saved xform so it doesn't float).
      - Bugs fought & killed (all live-verified): GetMount→GetMountInput; inert ForEach (needed
        `ResolvedWildcardType` + exec-wired source); `IsMount`→`IsMountable` (IsMount is mount-STATE,
        true-for-all at mount tick); wildcard `Array_Length` compile fail; SpareHorse grabbing the
        player's own mount. **Framework cache was a red herring** — rebuilds take effect with NO
        editor restart (proven via the `MgrVersion` CDO tag, now ==6).
      - **Limitations (→ C3/C5):** one `SavedMeshXform` var + one `SpareHorse` = correct for ONE
        humanoid; multiple followers need per-rider state and proper 1:1 nearest matching (C3).
        Debug `PrintString`s (MGR VERSION / MOUNT DETECTED / STOWING / DISMOUNT) still in — strip in
        C5 polish. Diagnostics: `dev/c2_live.py`, `probe_follower_kind.py`, `read_log.py`.
- [ ] **Auto-on-dismount reversal.** Covered by C2's dismount-transition branch; polish the
      restore (teleport beside player, re-possess) is C5.
- [x] **Multiple horses (C4 mechanism, live-proven 2026-06-05).** Follower caps are PER GROUP
      ("Mount" vs "Warrior"/etc.) on the player's `BP_ThrallSystemComponent`. Mounts are their own
      "Mount" group, so a generic follower-count mod won't cover them. Raise it with
      `add_thrall_group_limit_adjustment("Mount", N)` (additive/mod-safe) — confirmed live: after
      raising, the player claims and has **multiple horses following at once**. The mod calls this
      in the C2 ModController BeginPlay. (Test helper: `dev/c4_setcap.py` — runtime, re-apply per
      PIE session.) Still TODO: spacing/visual when several ride; the Stow loop already handles N.
- [x] **Horse↔follower matching (C3) — DONE & LIVE-VERIFIED 2026-06-05.** Simplified per user:
      not nearest-neighbour, just **distinct horse per follower** (no two share a mount). Pass A
      builds `SpareHorses[]` (every unridden mountable follower); Pass B keeps a `HumanoidCounter`,
      humanoid #i claims `SpareHorses[i]` (`GetArrayItem`) **guarded by `i < Array_Length`** and
      attaches if in range; surplus followers stay on foot. Index-alignment = distinct mounts.
      Verified: 2 entertainers → 2 separate horses. KEY paste gotcha: `IsValid` on a
      `GetArrayItem.Output` pin won't merge (bare Object pin doesn't take the special node's output
      type — `comp_of` only works because it PRE-TYPES its self pin); use an int-range guard instead.
      Also: also bumped the **"Warrior"** group cap (humanoid thralls live there), not just "Mount".
- [ ] **Follower spacing (C5 polish).** Mounted (and on-foot) followers cluster/bump — they home on
      one follow point. Conan HAS a formation system (`join_formation`/`set_formation_criteria_row`/
      `is_in_formation`) + a simple knob `set_additional_follow_distance(N)`. Easy fix: stagger each
      spare horse's additional follow distance by its index so they trail in a line. NB calling a
      setter on the GetArrayItem horse hits the same self-pin-merge issue — pre-type the self pin or
      set it on the stored array element. Also: strip the vN debug PrintStrings in final polish.
- [ ] **Per-mount socket/pose tuning.** camel/rhino variants exist; pick the matching
      `A_human_mounted_idle_<MOUNT>` and verify each species' `attachrider` socket.
- [ ] **Combat behavior.** On ATTACK/aggro: auto-dismount the follower to fight on foot
      (safe, matches current feel) vs. mounted combat (more work). Don't let a stowed/hidden
      follower die invisibly — restore it before it can take lethal damage (watch DBNO).
- [ ] **MP / replication.** Run all of it server-side and replicate attach/frozen state;
      test on a listen + dedicated server, not just SP.
- [ ] **Persistence.** Never `Destroy()` a follower to stow it; ensure attach/frozen state
      survives relog and doesn't corrupt follower registration.

---

## 10. Implementation log — C1: recipe as compiled Blueprint (2026-06-05)

The §8 recipe was driven by raw Python in the prototype. C1 re-expressed it as **compiled
Blueprint logic** so it can ship in a mod (no Python/C++ at runtime), authored entirely from
outside the editor via node-text injection (`bpkit.author`/`bpkit.ir` → `bpkit.bridge.inject` → compile).

**Artifact:** `/Game/_Scratch/BP_MF_Recipe` (Actor BP, will move onto the C2 ModController).
- Member vars (instance-editable): `Rider`, `Mount` (ConanCharacter refs), `MountIdleAnim`
  (AnimSequence ref, default `A_human_mounted_idle_HORSE`).
- `Stow`: attach `Rider.Mesh` → `Mount.Mesh` socket `attachrider` (SnapToTarget) → `DisableMovement`
  → `SetActorEnableCollision(false)` → `SetAnimationMode(SingleNode)` → `PlayAnimation(MountIdleAnim, loop)`.
- `Restore`: `SetAnimationMode(Blueprint)` → `SetMovementMode(MOVE_Walking)` →
  `SetActorEnableCollision(true)` → re-attach `Mesh` → `CapsuleComponent`.

**Live result (PIE), both directions verified on a dancer NPC:** `Stow` → mesh exactly on
socket (dist 0.0), rides the moving horse seated; `Restore` → detaches, `MOVE_Walking`, stands
on the ground correctly and resumes following on foot. Build/verify scripts: `dev/c1_build.py`
(authoring), `dev/c1_errors.py` (compile-error scan), `dev/c1_pie_test.py` +
`dev/c1_restore_test.py` (live).

**Restore mesh-offset fix (critical):** re-attaching the mesh to the capsule with `SnapToTarget`
snaps it to the capsule *center* → rider floats ~96u up and yaw-rotated. Fix: a `SavedMeshXform`
(Transform) member var — `Stow` saves `mesh.GetRelativeTransform()` BEFORE reparenting, `Restore`
`K2_SetRelativeTransform`s it back after re-attach. This NPC's true offset is `(0,0,-96), yaw -90°`
(the standard Character mesh-vs-capsule offset; readable from the class CDO's mesh component).
GOTCHA: `Stow` must run **once** per mount — calling it again while already stowed re-saves the
(attached, ~zero) transform and corrupts the restore. The C2 poller fires once per transition, so
fine; add an "already stowed?" guard if ever called ad-hoc.

**Authoring lessons (also in memory):** component accessors (`GetMesh`/`GetCharacterMovement`)
are unreflected C++ inlines → use non-self-context `VariableGet` of the component var
(`bp-typed-pin-defaults`); node defaults/wires need the exact canonical K2 pin name + matching
PinType or they orphan and the autogen default silently wins; never compile a BP during PIE
(`no-bp-edit-during-pie`); a stale BP reload collision-renames pasted custom events (delete the
asset for a clean build, Play stopped); `Summon` needs the class pre-`load_object`'d and spawns
deferred a frame; finite-lifespan NPCs (undead) vaporize when summoned ownerless.

---

## 11. The "seated follower slides to the ground" bug — durable freeze (v31→v32, 2026-06-09)

**Symptom.** You mount and ride; a follower rides fine, then *after a while* the thrall is
suddenly on the ground following you — yet still in the mounted idle pose and at the saddle
offset. Erratic. **Repros ONLY in the cooked/packaged game — never in PIE.**

**Diagnosis.** The actor never detaches (user-verified), so the cosmetic seat loop keeps posing
it; what changes is the rider's *own* movement. Conan's follower **catch-up / leash AI**
(`ConanCharacter.is_ai_controller_leashing`, `wait_for_catch_up_time` / `has_time_catched_up` /
`try_resume_from_catch_up_time`, `teleport`) re-enables the seated follower's
`CharacterMovement` (`MOVE_None`→`Walking`) once you ride far enough; `CharacterMovement` then
walks the still-attached pawn down to the ground. The original stow freeze (`disable_movement()`)
was applied **once** on the mount transition, so a single AI re-enable broke it permanently until
dismount. PIE's small always-loaded world rarely makes a follower fall far enough behind to trip
the leash → no PIE repro (and `PrintString` is compiled out of Shipping, so diagnostics had to
move to `ConanCharacter.HUDShowFIFO`).

**Fix (v32, live-confirmed cooked SP).** A per-tick **server** (`HasAuthority`) MAINTAIN pass,
chained off the tick scan: for each humanoid still seated on a mountable horse, re-pin
`disable_movement()` (MOVE_None) **and** re-assert the saddle relative loc/rot **every tick**.
Trigger-agnostic — defeats both a movement-mode flip and a teleport/recall drift. Server-
authoritative, so it covers SP + listen + dedicated; the per-client cosmetic pose loop is
untouched. Confirmed when the lean once-per-ride `HUDShowFIFO` "kept a rider seated" banner fired
(= the leash *did* trigger) while the follower stayed seated. If the AI ever jitters, escalate to
`ConanPlayerController.command_follower(follower, loc, AIFollowerOrderType.HOLD)` at stow to stop
it at the source. **MP (listen/dedicated) still to verify.**

**Lesson.** A one-shot freeze on a still-AI-possessed follower is not durable — maintain it every
tick (or stop the AI), and never trust a clean PIE run for follower/leash behaviour.
