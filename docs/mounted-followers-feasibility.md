# Mounted Followers — Audit & Feasibility Report

**Question:** Can thralls/pets be made to *mount up* (ride their own horse/rhino) and
keep pace with the player, instead of sprinting on foot while you ride?

**Method:** Live reflection + Blueprint-graph reads against the running CEUE5 Dev Kit
(UE 5.6.1, `ConanSandbox`) over the Python remote-execution channel, 2026-06-05.
No guessing — every claim below is backed by a probe in `dev/probe_*` /
`dev/read_*` and a dump in `dump_*.txt`.

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

## 9. Roadmap / TODO (not yet done)

Status: **research + live single-rider prototype done (§7, §8).** Remaining to make it a
real, usable mod:

- [ ] **Auto-on-mount Blueprint.** Hook the player BP's `BPPostMountServerClient(mounted_npc)`
      → for each current follower, run the §8 attach/freeze/pose recipe against `mounted_npc`.
- [ ] **Auto-on-dismount reversal.** Hook `BPPostDismountServerClient` / `SignalDismountStart`
      → restore AnimBP (`ANIMATION_BLUEPRINT`), re-enable movement/collision/tick, re-possess,
      detach, teleport the follower beside the player.
- [ ] **Multiple followers.** Player should be able to bring several mounted followers. The
      follower-count cap is a known-easy mod (community mods already raise pet/thrall counts);
      raise it, then the attach loop already handles N followers. Decide spacing/visual when
      several ride.
- [ ] **Assign a horse to a thrall.** Each follower needs its *own* mount to ride, not the
      player's. Design: spawn/own a horse-pet per thrall and pair them (thrall ↔ its horse),
      so on player-mount each thrall mounts *its* assigned horse and the horse-pet follows.
      Needs a pairing/registration data model + UI/command to assign.
- [ ] **Per-mount socket/pose tuning.** camel/rhino variants exist; pick the matching
      `A_human_mounted_idle_<MOUNT>` and verify each species' `attachrider` socket.
- [ ] **Combat behavior.** On ATTACK/aggro: auto-dismount the follower to fight on foot
      (safe, matches current feel) vs. mounted combat (more work). Don't let a stowed/hidden
      follower die invisibly — restore it before it can take lethal damage (watch DBNO).
- [ ] **MP / replication.** Run all of it server-side and replicate attach/frozen state;
      test on a listen + dedicated server, not just SP.
- [ ] **Persistence.** Never `Destroy()` a follower to stow it; ensure attach/frozen state
      survives relog and doesn't corrupt follower registration.
