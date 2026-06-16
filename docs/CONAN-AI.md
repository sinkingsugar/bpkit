# Conan Exiles — NPC / Thrall AI (reusable across mods)

Live-verified facts about Conan's **"NewAI"** system (UE 5.6.1 Dev Kit, engine
`5.6.1-365199`), reverse-engineered by reflecting the native controller classes and
dumping the shipped behaviour-tree blueprints (`bpkit.bridge.read_blueprint`). This is
mod-agnostic reference — the mounted-followers application is the last section.

> How this was found (repeat it for any AI question): reflect the controller class
> surface (`dir()` + `__doc__` for signatures), list `/Game/Systems/AI/NewAI` via the
> AssetRegistry, and `read_blueprint("/Game/Systems/AI/NewAI/<Asset>.<Asset>")` to dump a
> `BTTask_*` / `BTS_*` / `BTD_*` graph node-by-node. **Never** call a native UFunction
> blind to "discover" it (crashes the editor — see CLAUDE.md); read the reflected doc / BP
> graph instead.

## Controller class hierarchy
All AI lives on the **controller**, not the pawn. The follow logic drives the
follower's *own* `CharacterMovementComponent` (no native path drives a separate mount —
the gap mounted-followers works around).

```
AController
  AIController                       (engine; BrainComponent, PathFollowingComponent)
    ConanAIController                (native; dynamic-subtree API, possess/reset)
      ConanBasicAIController         (native; is_following, home location/rotation, move_to_*)
        ConanAttackerAIController    (native; leashing, combat, finish_leashing, set_should_not_leash)
          HumanAIController          (BP /Game/Systems/AI/NewAI — humanoid thralls/fighters)
          (creatures use CreatureAIController*/LandAndWaterAIController/GolemAIController)
```

Reach the controller from a pawn: `GetController` → cast to `ConanAttackerAIController`
(humanoid followers cast cleanly; a non-attacker controller fails the cast → skip).
`brain_component` / `path_following_component` are properties on the controller (the
brain is a `UBrainComponent`: `start_logic` / `stop_logic(reason)` / `restart_logic` /
`is_paused` — a hard reboot of the whole behaviour tree if ever needed).

## Dynamic behaviour subtrees (the heart of NewAI)
A Conan AI runs one root BT whose branches are **dynamic subtrees injected by GameplayTag**.
"What is this NPC doing right now" = which subtree is installed under which tag.

Controller API (on `ConanAIController` and below):
- `set_behavior_subtree(subtree_tag, subtree_asset)` — install a subtree under a tag.
- `set_multiple_behavior_subtrees(map)` — batch install.
- `reset_behavior_subtrees_by_tag(tags)` — remove specific tags (→ tag's default).
- `reset_all_behavior_subtrees_to_default()` — remove ALL dynamic subtrees.
- `has_dynamic_subtree_set_by_tag(tag) -> bool` — query what's installed.
- `run_behavior_tree(bt_asset) -> bool` — swap the whole root tree.

In-tree, the game sets/clears subtrees with the tasks **`BTTask_SetDynamicBehaviorTree`**
/ **`BTTask_ResetDynamicBehaviorTree`**.

Shipped subtree assets (`/Game/Systems/AI/NewAI`):
`BT_Orders` (master order branch) · `BT_Order_Defend` / `_Flee` / `_Move` / `_Return` /
`_Wait` (in `FollowerOrders/`) · `BT_Leashing` · `BT_Fighting` · `BT_Passive` ·
`BT_Disengaged` · `BT_DoNothing` · `BT_Harvest` · `BT_HousePet` · `BT_GolemFollower`.
Blackboards: `BB_FollowAndGather` (the follower BB), `BB_Simple`, `BB_HousePet`, …

**Follower orders** are issued as `AIFollowerOrderType` = `{NONE=0, ATTACK=1, MOVE=2,
HOLD=3, RETURN=4, FLEE=5}` (via `ConanPlayerController.command_follower(follower, loc,
type)`), and surface in-tree as the `BT_Order_*` subtree under the order tag.

## Engagement behaviour (the combat stance)
`AIEngagementBehavior` = `{PASSIVE=0, DEFENSIVE=1, AGGRESSIVE=2}` — the follower's "attack"
setting in the radial menu:
- **AGGRESSIVE** = "attack on sight" (auto-engages enemies in range).
- **DEFENSIVE** = fights back only when attacked, then disengages.
- **PASSIVE** = never fights.

On `ConanCharacter`: `get_engagement_behavior()` / `set_engagement_behavior(b)` plus
`set_engagement_distance(d)` / `set_disengagement_distance(d)`.

**Crucial:** a running subtree can *temporarily override* the stance via the service
**`BTS_OverrideEngagementBehavior`**, and **`BTS_ResetBTOverrideWhenDone`** restores it
when that subtree ceases. So while a leash/return subtree is active the follower is
forced toward PASSIVE/DEFENSIVE; the override is meant to clear when the subtree finishes
*normally*. Force-yanking the subtree out from under the service (instead of finishing it)
can leave the stance stuck — the root cause of "thrall went passive and won't re-engage".

## Leashing / catch-up (the follower recall machine)
A follower that falls too far behind its owner is **recalled**: the AI installs
`BT_Leashing`, suppresses combat (engagement override), and walks/teleports the follower
back. Triggers: `BTD_LocationIsInLeashingRange`, `BTDecorator_ShouldGetHome`,
`Curve_HateLeash`. The "mounted catch-up" sub-phase is on `ConanCharacter`:
`wait_for_catch_up_time()` (enter) / `has_time_catched_up()` / `try_resume_from_catch_up_time()`
(low-level exit) / `client_end_catch_up_time()` / `is_ai_controller_leashing()` (pure read).

**The clean, authoritative controls (`ConanAttackerAIController`):**
- **`finish_leashing()`** — the game's own complete leash-exit. `BTTask_FinishLeashing`
  does exactly: cast owner → `finish_leashing()` → if `IsFollowing()` just finish, else
  rotate to `get_home_rotation()`. Prefer this over poking the low-level catch-up calls.
- **`set_should_not_leash(bool)`** — hard gate. `true` = this controller will not leash
  at all. The clean way to *prevent* leashing for a stretch (then re-enable + `finish_leashing`).
- Home: `get/set_home_location()`, `get/set_home_rotation()`, `is_at_home(tol)`, `teleport_home()`.
- `should_teleport_when_following(failed)`, `get_allowed_home_range()`.

While leashing, **re-enabling the follower's movement every tick fights the leash AI and
jams its state machine** (it never registers a successful catch-up) — see mounted-followers
below. The leash trips in the **cooked game**, rarely in PIE (PIE's small always-loaded
world keeps followers close), so leash bugs pass every PIE test.

## Follow relationship (`ThrallSystemComponent`, on the player)
`server_set_following(thrall, follow, feedback=True)` / `set_following(...)`
(`feedback=False` = no command sound) · `is_thrall_following_character(thrall)` ·
`get_following_thrall_characters() -> [ConanCharacter]` · `get_following_thralls()` (IDs) ·
`get_follower_group_counts() -> Map[Name,int]` · group limits via
`reset_thrall_group_limit_adjustment(group)` / `add_thrall_group_limit_adjustment(group,N)`.
Controller-side follow read: `ConanBasicAIController.is_following()`. Clear the current
order: `ConanAttackerAIController.clear_command()`.

## Targeting & combat helpers (`ConanCharacter` / `ConanAttackerAIController`)
`have_valid_target()` (**impure** — don't wire as a pure data pin, it gets pruned;
`is_ai_controller_leashing()` IS pure) · `has_target_in_attack_range()` · `is_in_combat_range()`
· `is_attacking()` · `should_sense_target(t)` · `force_remove_target_lock()` ·
`notify_target_cleared(c)` / `notify_targeted(i,c)` · `get_target_type()` / `get_target_location()`.

## Movement (`ConanAttackerAIController`)
`move_to_location(dest,…)` / `move_to_actor(goal,…)` / `funcom_move_to_location(dest,purpose,…)`
· `stop_movement()` · `get_move_status() -> PathFollowingStatus` · `get_immediate_move_destination()`
· `set_preferred_movement_speed(purpose,pref)` / `request_best_movement_speed()`
· `set_move_block_detection(bool)`.

---

## Application: mounted-followers stow/restore as a push/pop
A seated follower is actor-attached to a horse and frozen (`MOVE_None`, collision off,
single-node saddle anim). The horse drags it far from the owner, so the leash AI fires;
the v32 fix re-pins `MOVE_None` every tick to keep it on the saddle. That per-tick fight
**jams the catch-up machine** and leaves `BT_Leashing` (with its engagement override)
installed, so after dismount the follower is stuck PASSIVE/DEFENSIVE — won't auto-engage,
fights only when directly hit, "self-heals" once it eventually re-aggros (AstroCat,
2026-06). Cook-only; never reproduces in PIE.

**Fix history (each was a partial, restore-side patch):**
- v43 — `try_resume_from_catch_up_time()` + `cancel_any_forced_movement()` on restore.
- v44 — `reset_all_behavior_subtrees_to_default()` on restore.
- v45 — **the game's own push/pop**, replacing the guesses:
  - **STOW (push):** `ConanAttackerAIController.set_should_not_leash(true)` — the leash never
    trips while seated → catch-up never engages → nothing to jam (and the per-tick re-pin
    becomes belt-and-suspenders).
  - **RESTORE (pop):** `set_should_not_leash(false)` + `finish_leashing()` — re-enable and run
    the game's own clean leash-exit (the `BTTask_FinishLeashing` path).

General rule (holds for any "I parked an NPC's AI" mod): **don't hand-list undos —
disable the offending subsystem with its own gate on the way in, and call the game's own
finisher on the way out.** Symmetric, and immune to us forgetting a piece.
