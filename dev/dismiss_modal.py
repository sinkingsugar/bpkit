"""dismiss_modal - HOST-SIDE modal rescue. Run in the EXTERNAL interpreter, NOT via
ue_run: when a Slate modal is up, the editor's game thread is blocked in a nested
loop, so remote_execution can't run -- the dismissal must come from another process
over Win32, which is independent of that blocked thread.

How a Slate modal looks in Win32: the editor's main top-level window (class
'UnrealWindow') becomes DISABLED while a second 'UnrealWindow' (the dialog) stays
ENABLED + visible and grabs the foreground. So: if some editor window is disabled
and another is enabled, the enabled one is the modal -> post it a key.

Usage:
    python dev/dismiss_modal.py probe     # list editor windows, detect modal (safe)
    python dev/dismiss_modal.py enter     # dismiss via Enter (default button)
    python dev/dismiss_modal.py esc       # dismiss via Escape (cancel)
"""
import sys, ctypes
from ctypes import wintypes

u32 = ctypes.windll.user32
u32.IsWindowVisible.argtypes = [wintypes.HWND]
u32.IsWindowEnabled.argtypes = [wintypes.HWND]
u32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
u32.GetWindow.restype = wintypes.HWND

WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_RETURN, VK_ESCAPE = 0x0D, 0x1B
GW_OWNER = 4
EDITOR_CLASS = "UnrealWindow"

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _text(hwnd, fn, n=512):
    buf = ctypes.create_unicode_buffer(n)
    fn(hwnd, buf, n)
    return buf.value


def editor_windows():
    out = []

    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        cls = _text(hwnd, u32.GetClassNameW, 256)
        if cls != EDITOR_CLASS:
            return True
        out.append({
            "hwnd": hwnd,
            "title": _text(hwnd, u32.GetWindowTextW),
            "enabled": bool(u32.IsWindowEnabled(hwnd)),
            "owner": u32.GetWindow(hwnd, GW_OWNER),
        })
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def find_modal(wins):
    """A modal exists iff some editor window is disabled (the blocked main window)
    AND another is enabled. Return the enabled child-ish window (has an owner)."""
    if not any(not w["enabled"] for w in wins):
        return None
    cands = [w for w in wins if w["enabled"]]
    # prefer one that has an owner (true dialog) else the foreground enabled one
    owned = [w for w in cands if w["owner"]]
    pool = owned or cands
    fg = u32.GetForegroundWindow()
    for w in pool:
        if w["hwnd"] == fg:
            return w
    return pool[0] if pool else None


def dismiss(hwnd, vk):
    u32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    u32.PostMessageW(hwnd, WM_KEYUP, vk, 0)


def main():
    action = (sys.argv[1] if len(sys.argv) > 1 else "probe").lower()
    wins = editor_windows()
    print("editor ('UnrealWindow') top-level windows: %d" % len(wins))
    for w in wins:
        print("  hwnd=%s enabled=%s owner=%s title=%r" %
              (hex(w["hwnd"] or 0), w["enabled"], hex(w["owner"] or 0), w["title"][:60]))
    modal = find_modal(wins)
    if not modal:
        print("=> no modal detected (no disabled main window).")
        return
    print("=> MODAL detected: hwnd=%s title=%r" % (hex(modal["hwnd"]), modal["title"]))
    if action in ("enter", "esc"):
        vk = VK_RETURN if action == "enter" else VK_ESCAPE
        dismiss(modal["hwnd"], vk)
        print("=> posted %s to modal." % action.upper())
    else:
        print("=> probe only; pass 'enter' or 'esc' to dismiss.")


if __name__ == "__main__":
    main()
