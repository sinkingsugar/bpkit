"""pie - drive Play-In-Editor + suppress deadlocking modals from Python.

RUN INSIDE THE EDITOR (ship via ue_run.py). Library, like bp_bridge.

Why this exists: testing the mod meant asking the user to press Play / Stop and to
dismiss modal dialogs by hand. Modals are the nasty bit -- a Slate modal runs a
nested loop on the game thread, which is the same thread that services
remote_execution, so while a modal is up our commands never run (looks like a dead
channel). Two-pronged fix:

  1. PREVENT (this module): flip the engine global `GIsRunningUnattendedScript` to
     true via ctypes-by-address (same trick as bp_bridge). With it set,
     FMessageDialog::Open returns the dialog's DEFAULT answer without ever showing a
     modal -- so scripted Play/compile/save actions can't deadlock us.
  2. RESCUE (bpkit/ops/dismiss_modal.py, host-side): if a modal slips through anyway,
     an EXTERNAL process finds the editor's modal window over Win32 and dismisses it
     (the editor's game thread is blocked, so the rescue must come from outside).

Public API:
    is_in_pie() -> bool
    start_play(suppress=True)        # editor_request_begin_play, modals suppressed
    stop_play()  -> bool             # editor_request_end_play
    dialogs_suppressed() -> bool     # read GIsRunningUnattendedScript
    suppress_dialogs(on=True) -> bool  # set it; returns prior value
"""
import ctypes

# --- ctypes resolve of the exported global bool (data export) ---------------
_k32 = ctypes.windll.kernel32
_k32.GetModuleHandleW.restype = ctypes.c_void_p
_k32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
_k32.GetProcAddress.restype = ctypes.c_void_p
_k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

_UNATTENDED_SYM = b"?GIsRunningUnattendedScript@@3_NA"   # bool GIsRunningUnattendedScript
_unattended_addr = None


def _unattended_flag():
    """ctypes c_bool view over the engine's GIsRunningUnattendedScript global."""
    global _unattended_addr
    if _unattended_addr is None:
        h = _k32.GetModuleHandleW("UnrealEditor-Core.dll")
        if not h:
            raise OSError("UnrealEditor-Core.dll not mapped (editor running?)")
        addr = _k32.GetProcAddress(h, _UNATTENDED_SYM)
        if not addr:
            raise OSError("export not found: GIsRunningUnattendedScript")
        _unattended_addr = addr
    return ctypes.c_bool.from_address(_unattended_addr)


def dialogs_suppressed():
    return bool(_unattended_flag().value)


def suppress_dialogs(on=True):
    """Set GIsRunningUnattendedScript; returns the PRIOR value so callers can restore.
    While true, modal message dialogs auto-return their default answer (no UI block)."""
    f = _unattended_flag()
    prior = bool(f.value)
    f.value = bool(on)
    return prior


# --- PIE control via LevelEditorSubsystem -----------------------------------
def _les():
    import unreal
    return unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)


def is_in_pie():
    return bool(_les().is_in_play_in_editor())


def start_play(suppress=True):
    """Request begin-play in the active level viewport. With suppress=True, modal
    prompts (e.g. 'Could not find a starting spot') auto-dismiss so the begin-play
    that fires next tick can't deadlock the remote-exec channel."""
    if suppress:
        suppress_dialogs(True)
    if is_in_pie():
        return False                      # already playing
    _les().editor_request_begin_play()
    return True


def stop_play():
    """Request end-play. Returns False if not currently in PIE."""
    if not is_in_pie():
        return False
    _les().editor_request_end_play()
    return True
