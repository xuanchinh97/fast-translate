import sys
import time
import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import QWidget
from src.config import config

user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

HOTKEY_ID_TEXT = 1001
HOTKEY_ID_OCR = 1002


def parse_hotkey(s: str) -> tuple[int, int]:
    parts = [p.strip().lower() for p in s.split("+")]
    mods = MOD_NOREPEAT
    vk = 0
    for p in parts:
        if p == "alt":
            mods |= MOD_ALT
        elif p == "ctrl":
            mods |= MOD_CONTROL
        elif p == "shift":
            mods |= MOD_SHIFT
        elif p == "win":
            mods |= MOD_WIN
        elif p.startswith("f") and p[1:].isdigit():
            vk = 0x70 + (int(p[1:]) - 1)
        elif len(p) == 1:
            vk = ord(p.upper())
    return mods, vk


class HotkeyListener(QWidget):
    """
    Dual-engine Hotkey Listener:
    1. Primary: Windows Kernel RegisterHotKey via Top-Level QWidget nativeEvent (immune to antivirus/hook blocking)
    2. Secondary: Python keyboard low-level hook (fast fallback)
    Debounced with 350ms window to prevent duplicate triggering.
    """
    text_hotkey_triggered = Signal()
    ocr_hotkey_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(None, Qt.WindowType.Window)
        self.hwnd = int(self.winId())
        self._is_running = False
        self._last_trigger_text = 0.0
        self._last_trigger_ocr = 0.0

    def _on_text_pressed(self):
        now = time.time()
        if now - self._last_trigger_text < 0.35:
            return
        self._last_trigger_text = now
        try:
            from src.main import log
            log("[Hotkey] Triggered: Text (Alt+D)")
        except Exception:
            pass
        self.text_hotkey_triggered.emit()

    def _on_ocr_pressed(self):
        now = time.time()
        if now - self._last_trigger_ocr < 0.35:
            return
        self._last_trigger_ocr = now
        try:
            from src.main import log
            log("[Hotkey] Triggered: OCR (Alt+Shift+D)")
        except Exception:
            pass
        self.ocr_hotkey_triggered.emit()

    def start(self):
        if self._is_running:
            return

        text_hk = config.get("hotkey_text", "alt+d").strip().lower()
        ocr_hk = config.get("hotkey_ocr", "alt+shift+d").strip().lower()

        m1, k1 = parse_hotkey(text_hk)
        m2, k2 = parse_hotkey(ocr_hk)

        # 1. Register with Windows Kernel on this top-level HWND
        r1 = user32.RegisterHotKey(self.hwnd, HOTKEY_ID_TEXT, m1, k1)
        r2 = user32.RegisterHotKey(self.hwnd, HOTKEY_ID_OCR, m2, k2)

        try:
            from src.main import log
            log(f"[Hotkey] Windows Kernel Register: Text({text_hk} -> {r1}), OCR({ocr_hk} -> {r2}) [HWND={self.hwnd}]")
        except Exception:
            pass

        # 2. Also register keyboard module hook as complementary engine
        try:
            import keyboard
            keyboard.add_hotkey(text_hk, self._on_text_pressed, suppress=False)
            keyboard.add_hotkey(ocr_hk, self._on_ocr_pressed, suppress=False)
            try:
                from src.main import log
                log(f"[Hotkey] Low-level keyboard hook active: Text({text_hk}), OCR({ocr_hk})")
            except Exception:
                pass
        except Exception as e:
            try:
                from src.main import log
                log(f"[Hotkey] Low-level hook registration skipped: {e}")
            except Exception:
                pass

        self._is_running = True

    def nativeEvent(self, eventType, message):
        """Processes Windows Kernel WM_HOTKEY messages dispatched directly to this HWND"""
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_TEXT:
                    self._on_text_pressed()
                    return True, 0
                elif msg.wParam == HOTKEY_ID_OCR:
                    self._on_ocr_pressed()
                    return True, 0
        return super().nativeEvent(eventType, message)

    def stop(self):
        if self._is_running:
            user32.UnregisterHotKey(self.hwnd, HOTKEY_ID_TEXT)
            user32.UnregisterHotKey(self.hwnd, HOTKEY_ID_OCR)
            try:
                import keyboard
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
            self._is_running = False
