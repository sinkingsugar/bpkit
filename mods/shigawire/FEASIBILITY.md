# Shigawire — Grappling Hook: Design & Feasibility

**Idea:** Fire a hook. It sticks to whatever it hits. The player is reeled toward the
hit point (a gap-closer / mobility tool). If the hook lands on an **enemy**, that enemy
is additionally **staggered / knocked down / briefly stunned** — so you arrive on a
disoriented target. Think *Scorpion-meets-Roadhog*, except **you** travel to the
target, not the reverse.

**Status:** recon DONE (2026-06-18) — **all four unknowns came back GREEN** (see
§Recon results). The mod is feasible content-only. Nothing built yet; `manifest.BUILD`
stays empty until the firing-path / pull-feel / CC-flavor decisions are made.

---

## Decomposition

1. **Fire a hook** — a custom projectile/thrown-tool BP. On hit, line-trace / read the
   hit actor and classify it: terrain vs. `ConanCharacter` vs. enemy AI. Reading the
   hit actor's class/props cross-instance is well-trodden (`IsThrall`, `IsMountable`,
   `g.var_get`). Firing it from a **custom item** is data-table grind (Conan items are
   heavily data-driven) but low *uncertainty*.
2. **Pull the player toward the hit point** — *the make-or-break "feel" piece.* Needs
   movement manipulation on the player pawn (launch/impulse, or a per-tick interp).
3. **CC the enemy on hit** — stagger / knockdown / stun. A recon question: is there a
   callable native status/knockback, or is hit-reaction locked behind the
   damage/animation pipeline (mount-seating-style "no BP call does it")?
4. **Rope visual** — cosmetic `CableComponent`, hand → hook point. Cosmetic-only, so
   recompute per render instance in MP (same lesson as the saddle pose, v47).
5. **MP / replication** — event-driven, not a persistent Always-Relevant manager.
   Likely a server RPC for the launch (server-authoritative) + a multicast for the
   cosmetic rope. Owning-client `CharacterMovement` is prediction-friendly, which works
   *in our favor* for the pull (see risk #1).

## Where the risk actually lives (scar tissue)

Conan's movement and combat reactions are heavily **native + input-gated** — every
time we've driven the engine's movement/anim systems from the side they fought back
(mount seating is player-gated; the leash re-mobilized seated followers; the saddle
pose wedged the AI). So the two real unknowns are #2 and #3:

- **Pulling the player.** Does a `LaunchCharacter` / `AddImpulse`-style call exist and
  actually work + replicate on `ConanCharacter`'s movement component? If **yes**, very
  promising — owning-client char movement predicts locally and replicates up cleanly.
  If the pull has to fight a native movement gate (the way followers did), the feel
  gets painful and we may be stuck with a teleport (no swing).
- **Enemy CC.** Is there a reflected `ApplyStatusEffect` / knockback / stagger we can
  call cleanly, or is hit-reaction native-only? If only the *damage pipeline* triggers
  it, we might piggyback by dealing a tagged damage event rather than calling CC
  directly.

The item/projectile authoring (#1, #4) is the most *laborious* part but the least
*uncertain* — grind, not a wall.

## Verdict (POST-recon, 2026-06-18) — GREEN

Build it. Every load-bearing primitive exists and is script-reachable in the content-
only kit; none of the native-gating that burned mounted-followers applies here. The
player-pull is the *canonical* engine call (not gated), the enemy CC has both a one-call
path and the game's own combat-reaction pipeline, the firing rides an existing item +
projectile framework, and the cosmetic rope component is bound. Confidence: **high** on
all four. Remaining unknowns are build-phase details (below), not feasibility risks.

---

## Recon results (2026-06-18)

Probes: `00_recon.py` + `00b_recon_detail.py` (read-only — `dir()` / `__doc__` /
asset-registry tags; no UFunction calls, no PIE; no scratch assets created). Engine
`5.6.1-365833`.

**1. PULL — ✅ the player-pull is NOT gated.** `ConanCharacter.launch_character(launch_velocity,
xy_override, z_override)` is reflected (inherited `ACharacter::LaunchCharacter`) — the
canonical "fling the character" call. Alternatives on `ConanCharacterMovementComponent`:
`add_impulse(impulse, velocity_change)`, `add_force(force)`, writable `velocity`,
`request_direct_move(vel, force_max_speed)`, `disable_movement_for_duration(d)`. Conan
even has a native knockback/ragdoll state machine (`unreal.KnockbackStage` enum,
`KnockbackRagdollingStart` / `SignalCanGetUpFromKnockback` signals), so "being yanked /
knocked" is first-class. MP: launch is standard CharacterMovement (server-authoritative
+ owning-client prediction) — call server-side, replicates; nail exact authority in build.

**2. THROW — ✅ existing item + projectile framework to subclass.** Parent chains (from
AssetData tags):
- *projectile (the flying hook):* native `InventoryItemBase` → `BP_BaseProjectile` →
  `BP_ThrowableProjectile`. Subclass here; on-hit it classifies the target + triggers
  pull/CC + spawns the cable. `ProjectileMovementComponent` is available for flight.
- *launcher (the equippable):* native `GameItem` → `BPGameItemWeapon` →
  `BP_ProjectileWeapon` → `BP_ProjectileWeaponThrown` / `BP_ProjectileWeaponLauncher`.
  Subclass here for the fire/aim entry point.
- *concrete template:* `BP_throwing_offhand_axe` (← `BP_BaseVisualProjectileWeapon`) +
  `BP_throwing_offhand_axe_projectile`. Aim/fire pipeline to inherit:
  `BP_ProjectileWeaponAimingInterface`, `BPI_BaseProjectile`.

**3. CC — ✅✅ multiple paths, flinch→stun.**
- *one-call:* `ConanCharacter.add_stagger(stagger)`; plus `add_buff(buff_class, potency)`
  / `remove_buff(buff_class)` against `/Game/Systems/Buffs/` (base `01_BP_AC_Buff_Master`).
- *idiomatic (the game's own combat reaction):* `GameplayStatics.apply_point_damage(target,
  dmg, hit_dir, hit, instigator, causer, damage_type_class)` with a `BP_Knockback_*`
  DamageType — `BP_Knockback_Flinch`, `…_Knockdown`, `…_KnockUp_*`, `…_NPC_Away`, and
  **stun** `BP_Knockback_Stun_Quick` / `…_Lengthy` / `…_Extra_Strong`. AI side reacts via
  `ConanAttackerAIController.notify_knockbacked` / `handle_knockback_response`.

**4. CABLE — ✅** `unreal.CableComponent` is bound (MeshComponent line) → cosmetic rope
authorable (bpkit can author the component + we recompute it per render instance in MP,
the saddle-pose lesson).

### Open items (build-phase, NOT blockers)
- `add_stagger`'s exact arg type (float vs. struct) — read the pin when authoring the node.
- How a thrown weapon aims & spawns its projectile — a graph read of `BP_throwing_offhand_axe`
  / `BP_ProjectileWeaponThrown` (first build step; use `/bp-read`).
- The item-table row needed to make the launcher equippable/admin-spawnable.
- Exact MP authority for `launch_character` + `apply_point_damage` (server-side).

---

## Build status (2026-06-19)

Decisions (Giovanni): **reskin the throwing axe** (full reskin in order) · **ballistic
launch** · **light stagger/flinch**. Built as 4 idempotent steps; `python ue_run.py
bpkit/ops/deploy.py shigawire` runs the chain (Play stopped). All compile clean (the lone
flagged `K2_SetRelativeRotation` node is a pre-existing axe-projectile warning, identical
in the source — not introduced here).

- **`01_assets.py`** — clones `BP_throwing_offhand_axe_projectile` → `BP_SW_HookProjectile`
  (the flying hook, still a `BP_BaseProjectile` child) and `BP_throwing_offhand_axe` →
  `BP_SW_HookLauncher` (the thrown-weapon shell).
- **`02_item_table.py`** — `DT_SW_Items` (row struct `ItemTableRow`), two rows cloned LIVE
  from the Chakram template pair and repointed: weapon `920140` (`VisualObject`=HookLauncher,
  `CompatableAmmunitions=[920141]`) and ammo `920141` (`VisualObject`=HookProjectile).
  TemplateIDs are `sw_config` constants — **confirm collision-free before public release.**
- **`03_controller.py`** — `BP_ShigawireController : ModController`; its
  `ModDataTableOperations` override calls `MergeDataTables(game ItemTable, DT_SW_Items)` to
  register both rows (the same merge mechanism mounted-followers used for `dc MFHorses`).
- **`04_projectile.py`** — **launch tech + auto-return** (self-resets via delete+reclone so
  the logic is re-authorable). Extends the cloned projectile's `StopProjectile` event (fires
  when the hook embeds), `HasAuthority`-gated → `GetInstigator` → cast `ConanCharacter`:
  - **Launch** (`LaunchCharacter`, xy=z=override): the pull is split into a consistent
    horizontal zip + a shaped/clamped vertical pop, so what you hit decides the launch:
    `horizontal = Normalize(MakeVector(Δx, Δy, 0)) · HORIZ_SPEED`,
    `vertical = MapRangeClamped(Abs(Δz), 0..DZ_REF, UP_MIN..UP_MAX)`. Level wall → strong
    zip + modest pop; ledge above OR floor below → bigger launch (`Abs` makes the floor pogo
    you up); `UP_MAX` caps orbit. All `sw_config` knobs.
  - **Auto-return** (`SpawnTemplateItem(templateID=PROJECTILE_TEMPLATE_ID, …)` on the
    instigator): refund the hook to the thrower's inventory (the base projectile uses the
    same call to "spawn the projectile item in the receiver"). KNOWN: `showNotification`
    stays `true` → a pickup toast per throw; silence it if spammy.

Cook-confirmed (2026-06-19, v1 simple pull): `StopProjectile` fires on impact + the launch
works in-game. v2 launch-tech feel is tuned by cook (no fall-damage immunity — slow-fall
spell handles landings, per Giovanni).

### Pending
- **Enemy flinch** (step 05): `StopProjectile` carries no hit actor, so a sphere-overlap at
  the impact point → `add_stagger` / `BP_Knockback_Flinch` on a hit `ConanCharacter`
  (`add_stagger`'s arg type to be read off the pin when authoring).
- **Cosmetic cable** (`CableComponent` hand → impact, recomputed per render instance).
- **Feel tuning** of `HORIZ_SPEED` / `UP_MIN` / `UP_MAX` / `DZ_REF` (cook/play-only).
