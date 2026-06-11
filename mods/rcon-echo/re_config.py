"""Metadata for the rcon-echo mod -- the cooked-game transport proof for the
RCON->Blueprint receive channel (the LLM-NPC project's RECV link).

OUTPUT_PKG must be the mod's own content root (/Game/Mods/<ModName>) so the cook
tags the BPs "(Mod Asset)" -- see docs/CONAN-NOTES.md §Packaging. The RconEcho
mod must exist in the DevKit (Mods tool -> create) and be the ACTIVE mod for
this package to be writable.
"""

OUTPUT_PKG = "/Game/Mods/RconEcho"

# Asset names within OUTPUT_PKG.
CMD = "BP_RconEchoCmd"               # RconCommandObject subclass: the `bpecho` command
CONTROLLER = "BP_RconEchoController" # ModController that hard-references CMD so the
                                     # class is in the cooked load chain (the plugin's
                                     # BP-subclass discovery mechanism is unverified;
                                     # this guarantees the class is at least LOADED)

# The RCON command word + help text.
CMD_NAME = "bpecho"
CMD_HELP = "Usage: bpecho <text...> -- echoes the args back from mod Blueprint (RconEcho v%d)"

# Stamped into CMD_HELP and the controller CDO.
VERSION = 1


def full(name):
    """'/Game/.../Name.Name' object path for an asset NAME in this mod's package."""
    return "%s/%s.%s" % (OUTPUT_PKG, name, name)
