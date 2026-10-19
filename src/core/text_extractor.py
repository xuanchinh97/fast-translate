import ctypes
import time
import threading
from ctypes import wintypes
from typing import Optional
from src.config import config

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Configure Win32 API signatures
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.GetClipboardSequenceNumber.argtypes = []
user32.GetClipboardSequenceNumber.restype = wintypes.DWORD

# Virtual Key Codes
VK_MENU = 0x12       # ALT key
VK_LMENU = 0xA4      # Left ALT
VK_RMENU = 0xA5      # Right ALT
VK_CONTROL = 0x11    # CTRL key
VK_LCONTROL = 0xA2   # Left CTRL
VK_SHIFT = 0x10      # SHIFT key
VK_LSHIFT = 0xA0     # Left SHIFT
VK_RSHIFT = 0xA1     # Right SHIFT
VK_LWIN = 0x5B       # Left Windows
VK_RWIN = 0x5C       # Right Windows
VK_C = 0x43          # 'C' key

KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE = 0x0008

WM_COPY = 0x0301
SMTO_ABORTIFHUNG = 0x0002
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# SendInput structures
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]

INPUT_KEYBOARD = 1
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def get_clipboard_text() -> str:
    """Reads CF_UNICODETEXT directly from Windows Clipboard with automatic retry"""
    for _ in range(8):
        if user32.OpenClipboard(0):
            break
        kernel32.Sleep(10)
    else:
        return ""
    try:
        h_data = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data:
            return ""
        ptr = kernel32.GlobalLock(h_data)
        if not ptr:
            return ""
        try:
            return str(ctypes.wstring_at(ptr))
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()


def set_clipboard_text(text: str) -> bool:
    """Writes CF_UNICODETEXT directly to Windows Clipboard"""
    if text is None:
        return False
    data_bytes = (text + "\0").encode("utf-16le")
    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data_bytes))
    if not h_mem:
        return False
    ptr = kernel32.GlobalLock(h_mem)
    if not ptr:
        return False
    ctypes.memmove(ptr, data_bytes, len(data_bytes))
    kernel32.GlobalUnlock(h_mem)

    for _ in range(8):
        if user32.OpenClipboard(0):
            break
        kernel32.Sleep(10)
    else:
        return False
    try:
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def make_key(vk: int, scan: int = 0, flags: int = 0) -> INPUT:
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan or user32.MapVirtualKeyW(vk, 0)
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = 0
    return inp


def wait_for_modifiers_released(timeout_sec: float = 0.5):
    """Wait until physical Alt and Shift keys are released by the user"""
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        alt_pressed = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
        shift_pressed = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        if not (alt_pressed or shift_pressed):
            break
        time.sleep(0.015)


def release_modifiers():
    """Virtually release any stuck modifier keys with exact hardware scan codes"""
    # 1. Hardware scan codes for keybd_event
    user32.keybd_event(VK_LMENU, 0x38, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_RMENU, 0x38, KEYEVENTF_KEYUP | KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(VK_MENU, 0x38, KEYEVENTF_KEYUP, 0)

    user32.keybd_event(VK_LSHIFT, 0x2A, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_RSHIFT, 0x36, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0x2A, KEYEVENTF_KEYUP, 0)

    user32.keybd_event(VK_LCONTROL, 0x1D, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)

    # 2. Also send via SendInput if allowed
    try:
        inputs = [
            make_key(VK_LMENU, 0x38, KEYEVENTF_KEYUP),
            make_key(VK_RMENU, 0x38, KEYEVENTF_KEYUP | KEYEVENTF_EXTENDEDKEY),
            make_key(VK_MENU, 0x38, KEYEVENTF_KEYUP),
            make_key(VK_LSHIFT, 0x2A, KEYEVENTF_KEYUP),
            make_key(VK_SHIFT, 0x2A, KEYEVENTF_KEYUP),
        ]
        arr = (INPUT * len(inputs))(*inputs)
        user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    except Exception:
        pass


def send_ctrl_c():
    """Simulate Ctrl + C keystroke using dual SendInput + keybd_event with exact scan codes"""
    wait_for_modifiers_released(timeout_sec=0.5)
    release_modifiers()
    time.sleep(0.015)

    # Try SendInput first
    sent = False
    try:
        copy_inputs = [
            make_key(VK_CONTROL, 0x1D, 0),
            make_key(VK_C, 0x2E, 0),
            make_key(VK_C, 0x2E, KEYEVENTF_KEYUP),
            make_key(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP),
        ]
        arr = (INPUT * len(copy_inputs))(*copy_inputs)
        ret = user32.SendInput(len(copy_inputs), arr, ctypes.sizeof(INPUT))
        if ret == len(copy_inputs):
            sent = True
    except Exception:
        sent = False

    # Fallback to keybd_event with scan codes if SendInput was blocked (e.g. UIPI or privilege isolation)
    if not sent:
        user32.keybd_event(VK_CONTROL, 0x1D, 0, 0)
        user32.keybd_event(VK_C, 0x2E, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_C, 0x2E, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0x1D, KEYEVENTF_KEYUP, 0)


def send_wm_copy_to_focused_window():
    """Sends WM_COPY message directly to the focused control window"""
    try:
        fg = user32.GetForegroundWindow()
        if not fg:
            return
        gui = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
        tid = user32.GetWindowThreadProcessId(fg, None)
        target = fg
        if user32.GetGUIThreadInfo(tid, ctypes.byref(gui)) and gui.hwndFocus:
            target = gui.hwndFocus
        user32.SendMessageTimeoutW(target, WM_COPY, 0, 0, SMTO_ABORTIFHUNG, 150, None)
    except Exception:
        pass


def restore_clipboard_delayed(previous_text: str, delay_sec: float = 1.0):
    """Restore previous clipboard content after a delay so caller app finishes copy"""
    def _worker():
        time.sleep(delay_sec)
        try:
            set_clipboard_text(previous_text)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def get_selected_text() -> str:
    """
    Robust multi-tier extraction of selected text across all Windows applications:
    1. Records initial clipboard sequence number and content (DO NOT WIPE CLIPBOARD).
    2. Sends Ctrl+C via SendInput/keybd_event with hardware scan codes and modifier key release.
    3. Monitors GetClipboardSequenceNumber() for immediate arrival of newly copied text.
    4. If sequence hasn't changed within 150ms, sends WM_COPY to focused control as Fallback Tier 2.
    5. If still no new clipboard event, checks if clipboard already contains valid text as Fallback Tier 3.
    6. Automatically restores previous clipboard if configured and new text was copied.
    """
    restore = config.get("restore_clipboard", True)
    old_seq = user32.GetClipboardSequenceNumber()
    old_text = get_clipboard_text()

    # Tier 1: Send Ctrl+C with scan codes and modifier release
    send_ctrl_c()

    # Poll for sequence change (up to 200ms)
    t_end = time.time() + 0.20
    new_seq_detected = False
    while time.time() < t_end:
        if user32.GetClipboardSequenceNumber() != old_seq:
            new_seq_detected = True
            break
        time.sleep(0.015)

    # Tier 2: If no sequence change yet, attempt direct WM_COPY
    if not new_seq_detected:
        send_wm_copy_to_focused_window()
        t_end2 = time.time() + 0.15
        while time.time() < t_end2:
            if user32.GetClipboardSequenceNumber() != old_seq:
                new_seq_detected = True
                break
            time.sleep(0.015)

    # Extract text
    copied_text = ""
    if new_seq_detected:
        time.sleep(0.01)
        copied_text = get_clipboard_text().strip()
        # Restore old clipboard if requested and we had previous text
        if restore and old_text and old_text != copied_text:
            restore_clipboard_delayed(old_text)
    else:
        # Tier 3: If no new copy event occurred, check if clipboard already has text that user copied
        # This allows user to simply press Ctrl+C anywhere then Alt+D
        if old_text and old_text.strip():
            copied_text = old_text.strip()

    return copied_text
