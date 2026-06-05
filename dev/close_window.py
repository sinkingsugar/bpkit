"""Host-side: close (or key-dismiss) editor windows by title substring.
Runs LOCALLY (Win32), not via ue_run -- the channel may be frozen.

Usage:
    python dev/close_window.py "Blueprint Compilation Errors"        # WM_CLOSE
    python dev/close_window.py "Blueprint Compilation Errors" esc    # send ESC instead
"""
import sys, ctypes
from ctypes import wintypes

u32 = ctypes.windll.user32
WM_CLOSE = 0x0010
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK = {"enter": 0x0D, "esc": 0x1B}

EnumWindows = u32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def title(hwnd):
    n = u32.GetWindowTextLengthW(hwnd) + 1
    buf = ctypes.create_unicode_buffer(n)
    u32.GetWindowTextW(hwnd, buf, n)
    return buf.value


def main():
    if len(sys.argv) < 2:
        print("usage: close_window.py <title-substr> [esc|enter|close]")
        sys.exit(2)
    needle = sys.argv[1].lower()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "close").lower()
    hits = []

    def cb(hwnd, _):
        t = title(hwnd)
        if needle in t.lower() and u32.IsWindowVisible(hwnd):
            hits.append((hwnd, t))
        return True

    EnumWindows(EnumWindowsProc(cb), 0)
    if not hits:
        print("no visible window matching %r" % sys.argv[1])
        return
    for hwnd, t in hits:
        if mode in VK:
            u32.SetForegroundWindow(hwnd)
            u32.PostMessageW(hwnd, WM_KEYDOWN, VK[mode], 0)
            u32.PostMessageW(hwnd, WM_KEYUP, VK[mode], 0)
            print("sent %s -> hwnd=%s %r" % (mode, hex(hwnd), t))
        else:
            u32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            print("WM_CLOSE -> hwnd=%s %r" % (hex(hwnd), t))


if __name__ == "__main__":
    main()
