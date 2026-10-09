import ctypes
import time
import threading
import pyperclip
from src.config import config

user32 = ctypes.windll.user32

# Virtual Key Codes
VK_MENU = 0x12       # ALT key
VK_CONTROL = 0x11    # CTRL key
VK_SHIFT = 0x10      # SHIFT key
VK_C = 0x43          # C key

KEYEVENTF_KEYUP = 0x0002


def wait_for_modifiers_released(timeout_sec: float = 0.25):
    """Wait until physical Alt and Shift keys are released by the user"""
    end_time = time.time() + timeout_sec
    while time.time() < end_time:
        alt_pressed = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
        shift_pressed = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
        if not (alt_pressed or shift_pressed):
            break
        time.sleep(0.015)


def release_modifiers():
    """Ensure modifier keys are not stuck down before simulating Ctrl+C"""
    user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def send_ctrl_c():
    """Simulate Ctrl + C keystroke using Windows API keybd_event"""
    wait_for_modifiers_released()
    release_modifiers()
    time.sleep(0.03)
    # Press Ctrl
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    # Press C
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.02)
    # Release C
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    # Release Ctrl
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)


def restore_clipboard_delayed(previous_text: str, delay_sec: float = 0.8):
    """Restore previous clipboard content after a delay so caller app finishes copy"""
    def _worker():
        time.sleep(delay_sec)
        try:
            pyperclip.copy(previous_text)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def get_selected_text() -> str:
    """
    Simulates Ctrl+C to grab the currently highlighted text anywhere in Windows.
    Preserves previous clipboard if configured.
    """
    restore = config.get("restore_clipboard", True)
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        old_clipboard = ""

    # Clear clipboard so we can detect new text arrival
    try:
        pyperclip.copy("")
    except Exception:
        pass

    time.sleep(0.03)
    send_ctrl_c()

    # Poll for new clipboard content (up to 350ms)
    copied_text = ""
    for _ in range(18):
        time.sleep(0.02)
        try:
            text = pyperclip.paste()
            if text and text.strip():
                copied_text = text.strip()
                break
        except Exception:
            pass

    # Restore previous clipboard if requested and we had previous text
    if restore and old_clipboard:
        restore_clipboard_delayed(old_clipboard)

    return copied_text
