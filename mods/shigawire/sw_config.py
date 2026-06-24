"""Metadata for the Shigawire mod -- the single place that decides WHERE the mod's
generated Blueprints are written and what they're called.

Shigawire (Dune): a thin, absurdly high-tensile filament -- here, a grappling-hook
rope. Fire a hook -> it sticks -> the player is reeled toward the hit point; if the
hook lands on an enemy, the enemy is staggered/knocked down/briefly stunned (a
gap-closer + CC). Design + de-risk plan: FEASIBILITY.md.

OUTPUT_PKG must be the mod's own content root (/Game/Mods/<ModName>) so the cook tags
the assets "(Mod Asset)" and Conan REGISTERS the ModController. Assets cooked from
anywhere ELSE are "(Base Asset)" -> the controller loads but is culled "[1]Invalid
class" in a packaged build (works in PIE, dead in the real game -- the mounted-
followers bug, 2026-06-08). /Game/Mods/<mod> is writable in the DevKit only when that
mod is the ACTIVE mod; build steps fall back to SCRATCH_PKG (a DRY RUN) when it isn't.
"""

OUTPUT_PKG = "/Game/Mods/Shigawire"
SCRATCH_PKG = "/Game/_Scratch"

# --- Asset names within OUTPUT_PKG. Recon (FEASIBILITY.md, 2026-06-18) confirmed the
#     classes to subclass; names still PROVISIONAL pending the firing-path decision.
CONTROLLER = "BP_ShigawireController"   # ModController: config/registration; may be unneeded
                                        # if the mechanic ends up fully item-driven
HOOK = "BP_SW_HookProjectile"           # the flying hook -- subclass BP_BaseProjectile /
                                        # BP_ThrowableProjectile (native InventoryItemBase line);
                                        # on-hit: classify target -> pull + CC -> spawn cable
ITEM = "BP_SW_HookLauncher"             # the equippable -- subclass BP_ProjectileWeaponThrown /
                                        # BP_ProjectileWeaponLauncher (native GameItem line);
                                        # needs an item-table row to be spawnable/equippable
CABLE = "BP_SW_Cable"                   # cosmetic rope (CableComponent), hand -> hook point

CONTROLLER = "BP_ShigawireController"   # (declared above) ModController: merges the item rows
ITEMS_DT = "DT_SW_Items"                # DataTable (row struct ItemTableRow) merged into the game ItemTable

VERSION = 1

# --- Item-data model (recon 2026-06-19). A thrown weapon is an ItemTableRow whose ItemClass is a
#     ProjectileWeaponThrown and whose CompatableAmmunitions=[projectileTemplateID]; the projectile
#     item row's VisualObject is the flying BP_BaseProjectile subclass (where pull/CC/cable live).
#     We clone the Chakram pair (24114 weapon / 24115 projectile -- both reuse the offhand-axe throw
#     BP) and repoint them. Rows are merged into the game ItemTable via the controller's
#     ModDataTableOperations override (MergeDataTables) -- same mechanism mounted-followers used for
#     its console command. See FEASIBILITY.md.
GAME_ITEM_TABLE = "/Game/Items/ItemTable"                                  # merge target (object path built in builder)
SRC_WEAPON_ROW = "24114"                                                   # template weapon row (Chakram, reuses axe BP)
SRC_PROJECTILE_ROW = "24115"                                              # template projectile/ammo row
SRC_VISUAL = "/Game/Items/Weapons/Throwing/BP_throwing_offhand_axe"        # thrown-weapon visual BP to clone -> ITEM
SRC_PROJECTILE = "/Game/Items/Weapons/Throwing/BP_throwing_offhand_axe_projectile"  # projectile BP to clone -> HOOK

# TemplateIDs (ItemTable row names) for our two rows. CONFIRM these are collision-free for a public
# release (vanilla rows go up into the tens of thousands; other mods claim ranges too). Easy to change.
WEAPON_TEMPLATE_ID = "920140"      # the equippable Shigawire launcher
PROJECTILE_TEMPLATE_ID = "920141"  # its hook projectile/ammo
DISPLAY_NAME = "Shigawire Launcher"

# --- Launch-tech tunables (v2: launch tech, not arrest). The pull is split into a
#     consistent horizontal zip toward the hook + a SHAPED, CLAMPED vertical pop:
#       horizontal = normalize(flat dir to impact) * HORIZ_SPEED
#       vertical   = MapRangeClamped( abs(impact.Z - player.Z), 0..DZ_REF, UP_MIN..UP_MAX )
#     -> level wall = strong zip + modest pop; hook a ledge above OR floor below = bigger
#     launch (abs() makes the FLOOR pogo you UP), bounded by UP_MAX so it's never orbit.
#     Pull cook-confirmed working 2026-06-19; these shape the "after". All feel-tuned.
HORIZ_SPEED = 2000.0    # horizontal zip toward the hook (cm/s) -- the impact strength (keep ~strong)
UP_MIN      = 600.0     # vertical pop on a level hit (cm/s) -- the baseline leap
UP_MAX      = 1500.0    # vertical cap (cm/s) -- strong launch, never orbit
DZ_REF      = 900.0     # height delta (cm) at which the vertical pop reaches UP_MAX
MAX_RANGE   = 4000.0    # max grapple distance (cm); beyond this the hook just falls (unused yet)
STAGGER_SECS = 1.5      # enemy CC duration on a hook hit (placeholder; flinch is step 05)


def full(name):
    """'/Game/.../Name.Name' object path for an asset NAME in this mod's package."""
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
