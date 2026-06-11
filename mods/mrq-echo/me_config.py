"""Metadata for the mrq-echo mod -- the cooked-game proof for the MRQ TCP
push channel (docs/CONAN-NOTES.md §Network, "Full-duplex TCP with BP RECV").

OUTPUT_PKG must be the mod's own content root (/Game/Mods/<ModName>) so the cook
tags the BP "(Mod Asset)". The MrqEcho mod must exist in the DevKit (Mods tool ->
create) and be the ACTIVE mod for that package to be writable; the build step
falls back to /Game/_Scratch with a DRY RUN banner when it isn't.
"""

OUTPUT_PKG = "/Game/Mods/MrqEcho"
SCRATCH_PKG = "/Game/_Scratch"

CONTROLLER = "BP_MrqEchoController"   # ModController: constructs the executor,
                                      # binds the recv delegate, reconnects in Tick

HOST = "127.0.0.1"                    # the gateway console (same machine as the game)
PORT = 9777

VERSION = 1
HELLO = "hello from MrqEcho v%d (cooked)" % VERSION


def full(pkg, name):
    """'/Game/.../Name.Name' object path for an asset NAME in package pkg."""
    return "%s/%s.%s" % (pkg, name, name)
