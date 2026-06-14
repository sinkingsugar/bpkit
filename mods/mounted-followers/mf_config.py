"""Metadata for the mounted-followers mod -- the single place that decides WHERE the
mod's generated Blueprints are written and what they're called.

The builders (00_recon / 02_manager / 02a_manager_minimal) all read
from here, so changing OUTPUT_PKG moves the whole mod in one edit.

Imported by the builders via bpkit.config.REPO_ROOT (so it works no matter the cwd).
"""

# Content package the generated Blueprint assets are written to. MUST be the MOD's own
# content root (/Game/Mods/<ModName>) so the cook tags them "(Mod Asset)" and Conan
# REGISTERS the ModController. Assets cooked from anywhere ELSE are "(Base Asset)" -> the
# ModController loads but is culled as "[1]Invalid class" in a packaged build (runs in PIE,
# dead in the real game -- the bug we chased 2026-06-08). /Game/Mods/<mod> is writable in
# the DevKit when that mod is the ACTIVE mod (verified writable 2026-06-08).
# (Old /Game/MountedFollowers was an editor-only sandbox shortcut -- NOT shippable.)
OUTPUT_PKG = "/Game/Mods/MountedFollowers"

# Asset names within OUTPUT_PKG.
MANAGER = "BP_MountedFollowerManager"   # the ModController manager (the mod itself)
SAVEGAME = "BP_MF_SaveGame"             # USaveGame subclass holding the persisted Mount limit
COMMAND = "BP_MF_HorsesCommand"         # UDataActorCommand subclass: the `dc MFHorses N` handler
CMD_TABLE = "DT_MF_Commands"            # 1-row BlueprintCommandDataRow table merged into the game's

# --- configurable Mount-follower limit (v39) ---
# The mod raises ONLY the "Mount" group cap (never Warrior/Crafter/etc.) so it can't clobber other
# follower mods (e.g. Better Thralls) -- that overlap was the BT-conflict FPS/limit bug (AstroCat
# report, 2026-06-13). The cap is SET (reset+add) to MOUNT_LIMIT, an idempotent assert that converges
# and never stacks. MOUNT_LIMIT is the DEFAULT/fallback; an admin (or SP player) overrides it live with
#   dc MFHorses <N>     (or  DataCmd MFHorses <N>)
# which applies to all players immediately (no restart) AND persists to a UE SaveGame slot, reloaded on
# BeginPlay. Server-authoritative + require_admin (SP players are admin -> works in SP too).
DEFAULT_MOUNT_LIMIT = 5     # extra Mount slots over the base cap when nothing is configured
MOUNT_LIMIT_MAX = 50        # clamp ceiling for the dc arg (typo / grief guard)
SAVE_SLOT = "MountedFollowersConfig"   # UE SaveGame slot (a .sav in Saved/SaveGames; NOT game_0.db)
CMD_NAME = "MFHorses"       # the console command name: `dc MFHorses N`
CUSTOM_CMD_TABLE = "/Game/Systems/Cheats/CustomConsoleCommandsDataTable"  # game table we merge into

# Stamped on the manager CDO so you can tell which build actually spawned.
# 26 = Shipping-safe on-screen diagnostics (HUDShowFIFO heartbeat + mount/dismount banners).
# 27 = relocated to /Game/Mods/MountedFollowers so the controller cooks as a Mod Asset
#      (the fix for "Invalid class" / never registering in a packaged build).
# 28 = removed the on-screen debug messaging (the bForceInit=false default DIDN'T take -- it
#      silently reverted to autogen 'true', so anims were still broken).
# 29 = the anim fix done right: bForceInitAnimScriptInstance is now WIRED to a literal false
#      (a pin default reverts; a wire can't) so the cosmetic-loop reset no longer re-inits every
#      character's AnimBP every tick.
# 30 = the cosmetic seat now only applies when the attach PARENT is a mountable horse, so thralls
#      attached to benches/wheels/stations are no longer wrongly put in the saddle pose/offset.
# 31 = FIX "seated thrall slides to the ground while still saddled". The one-shot stow freeze
#      (DisableMovement, fired once on the mount transition) is REVERSIBLE -- Conan's follower
#      catch-up/leash AI re-enables the rider's movement after a while of riding and
#      CharacterMovement then walks the STILL-attached pawn down to the ground (user-confirmed:
#      the actor never detaches). Added a per-tick server MAINTAIN pass: for every humanoid still
#      seated on a horse, re-pin MOVE_None + re-assert the saddle relative transform. Trigger-
#      agnostic (defeats a movement-mode flip AND a teleport/recall drift), server-authoritative
#      so it fixes SP + listen + dedicated. (Debug build -- carries diagnostic PrintStrings that
#      only show in PIE/non-Shipping; strip them in polish.)
# 32 = same maintain-pass FIX as v31, but the bug ONLY repros in the COOKED game (never PIE), so the
#      diagnostics are now Shipping-safe + lean: PrintString (compiled out of Shipping) is replaced by
#      Conan HUDShowFIFO, fired at most ONCE per ride -- a "mounted -- stowing" banner on mount and a
#      "kept a rider seated" banner the first time the maintain pass catches the leash re-mobilizing a
#      rider (ReportedFight bool, re-armed at stow). No per-tick spam. Strip both at final polish.
# 33 = RELEASE: all on-screen diagnostics stripped (the v32 mount banner + the once-per-ride
#      "kept a rider seated" report and its ReportedFight/DbgCount bookkeeping vars). Logic is
#      byte-for-byte the v32 behavior otherwise. NOTE an in-place rebuild leaves the old (now
#      unused) ReportedFight/DbgCount vars on the existing BP -- harmless, but a fresh build
#      (or manual var delete in the editor) yields the cleanest shipping asset.
# 34 = PER-PLAYER + housekeeping (deployed clean 2026-06-10: 148 nodes, 0 orphans, 0 compile
#      problems, independent error-scan clean; COOKED-game verification still pending):
#      - the host-only fix: the server pass iterates EVERY player pawn (valid-PlayerState scan
#        over the same GetAllActorsOfClass result the cosmetic loop uses) instead of
#        GetPlayerCharacter(0); caps raised once per player pawn (InitializedPlayers).
#      - stow/restore went LEVEL-TRIGGERED + idempotent (the seated-check gates the one-shots),
#        retiring WasMounted/the transition machinery; a follower whistled mid-ride saddles up.
#      - GLOBAL restore sweep via ActiveSeats: any seated humanoid whose horse no mounted player
#        legitimized this tick is restored -- covers dismount, followers that left the follow
#        list mid-ride, and owners who logged out while mounted (players excluded via
#        PlayerState, else a riding player could be force-dismounted).
#      - OccupiedHorses excludes already-carrying horses from the spare pool (a stowed rider
#        doesn't register via GetRider, so re-stows could double-book without it).
#      - follow-distance stagger reset to 0 when the owner is on foot.
#      - PERF: CDO tick_interval=0.1 (10 Hz polling instead of per-frame, ~6x cheaper).
#      - BP_MF_Recipe dropped from the build/pak (vestigial since the manager inlined stow at
#        v14; its mesh-attach pattern is the superseded pre-MP approach).
# 35 = v34 + PIE diagnostics: a DEBUG flag in the builder authors PrintString beacons at the
#      one-shot beats (caps applied / stowed / sweep restore / statue rescue). PrintString is
#      stripped from Shipping, but flip DEBUG=False and redeploy for the release cook anyway.
# 36 = THE v34 per-player pass actually runs now. Root cause of "+5 caps broken": Pawn's
#      GetPlayerState is NOT a UFUNCTION in this Conan build, and ImportNodesFromText SILENTLY
#      DROPS unresolvable CallFunction nodes (no orphan, NO compile error; IsValid then read an
#      unwired null pin = false) -- so the player gate never passed and the whole per-player
#      pass (caps/stow/restore) was dead code. Same dropped node had made the cosmetic loop's
#      player exclusion a no-op since v30 (harmless by luck). Fix: IsPlayerControlled (reflected
#      in this build; both gated passes are server-side where it's accurate) in all 3 spots, and
#      a new authored-vs-pasted node-count guard in the build self-check (the only tell).
# 37 = diagnostics polish (single-player CONFIRMED WORKING on v36): dbg beacons auto-stamp the
#      build version; NEW HUD_DIAG flag -- ship-visible HUDShowFIFO "kept a rider seated" banner
#      (once per ride, ReportedCatch latch re-armed while on foot) when the maintain pass
#      catches the leash AI re-mobilizing a seated rider, because the leash only repros in the
#      COOKED game where PrintString doesn't exist. DEBUG adds a matching log line in PIE.
#      Release deploy: DEBUG=False, HUD_DIAG to taste (recommended True).
# 38 = HUD_DIAG defaulted OFF (Giovanni: no player-visible diagnostics; the shipped mod is
#      SILENT -- note a Shipping build logs NOTHING from BP, PrintString is a no-op there).
#      Leash-catch detection restructured to author under DEBUG *or* HUD_DIAG so the PIE log
#      line survives with the banner off. Release deploy: DEBUG=False too.
# 39 = MOUNT-ONLY + CONFIGURABLE LIMIT (the BT-conflict fix + AstroCat's settable-limit ask):
#      - cap raise now touches ONLY the "Mount" group (was all 6: Mount/Warrior/Crafter/Bearer/
#        Performer/Archer). Touching the others stacked additively on Better Thralls' groups every
#        session -> BT fought back per-tick -> server FPS tank + limit clobbering. Mount is the
#        mod's own group; nothing else manages it, so the conflict is gone.
#      - SET semantics: reset_thrall_group_limit_adjustment("Mount") + add(..., N) instead of a
#        guarded one-time add. Idempotent, converges to exactly N, relog/re-apply safe.
#      - N = DEFAULT_MOUNT_LIMIT (5) unless overridden via `dc MFHorses N` (BP_MF_HorsesCommand,
#        a UDataActorCommand registered by merging DT_MF_Commands into the game's
#        CustomConsoleCommandsDataTable at BeginPlay). The command applies to all players live
#        (no restart) and persists N to a BP_MF_SaveGame slot, reloaded on each per-player init.
# 40 = PERF: stop the blind per-tick GetAllActorsOfClass(ConanCharacter) sweep (O(every player+thrall
#      +NPC), ran on server AND every client even when nobody was riding -- a server-FPS cost separate
#      from the v39 BT fix). Now: players are enumerated via GameState.PlayerArray (O(players)); the
#      per-player pass (caps/detect/stow/restore) is cheap + runs every tick; the expensive
#      GetAllActorsOfClass cosmetic + global sweep gate on RunCosmetic (=AnyMounted OR WasMounted, a
#      1-tick trailing run so the cosmetic anim-reset still fires the tick after the last dismount).
#      Server sets AnyMounted in the per-player detect; clients via a cheap local-player follower scan
#      (no replication available). Idle ticks (nobody riding) now do ZERO GetAllActorsOfClass.
#      Trade-off: a client only seat-animates OTHER players' followers while ITS local player is also
#      riding. (NEVER SHIPPED -- that trade-off was rejected; see v41.)
# 41 = v40 perf WITHOUT the MP trade-off. The COSMETIC loop runs on every RENDER instance (clients +
#      listen host + SP), UNGATED -- so each re-derives EVERY player's seated-follower pose (the mod
#      never replicated custom state; it recomputes per-instance from native attach/get_rider). Only a
#      *dedicated* server skips the cosmetic (is_dedicated_server -- no render, anim invisible + non-
#      replicated). The server's global restore sweep gets its OWN GetAllActorsOfClass, gated on
#      SweepRun = AnyMounted OR WasMounted (1-tick trailing for dismount/orphan restore). Player-find
#      via GameState.PlayerArray. Net: an idle DEDICATED server does ZERO GetAllActorsOfClass; clients
#      keep animating everyone (no trade-off). Listen server fully correct (host = render + authority).
# 42 = REMOVED follow-distance management entirely. The mod set SetAdditionalFollowDistance =
#      index*180 on each spare horse while mounted (cosmetic: fan the posse into a trailing line)
#      and reset it to 0 on every horse follower when on foot. But AdditionalFollowDistance is the
#      same knob Conan's in-game follow-distance control drives, and the unmounted reset ran every
#      tick (10 Hz) on the server -> any distance the player picked was clobbered back to the base
#      (~5m) within a frame. It was a solution looking for a problem; seated followers are actor-
#      attached to their horse so spacing them was the only effect. Dropped both spots -> spare
#      horses now follow at the player's chosen distance; the player's follow-distance setting sticks.
MGR_VERSION = 42

# Seated idle pose played on a stowed rider (full object path).
IDLE_ANIM = ("/Game/Characters/humans/animations/mounted/Horse/"
             "A_human_mounted_idle_HORSE.A_human_mounted_idle_HORSE")


def full(name):
    """'/Game/.../Name.Name' object path for an asset NAME in this mod's package."""
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
