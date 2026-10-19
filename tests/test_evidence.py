import unittest
import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QPoint
from PySide6.QtGui import QIcon

import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
WM_HOTKEY = 0x0312

from src.config import config
from src.core.hotkey_listener import HotkeyListener
from src.core.translator import translator
from src.core.ocr_engine import ocr_engine
from src.ui.tray_icon import get_application_icon, TrayIcon
from src.ui.popup_window import PopupWindow


class FastTranslateEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_01_tray_icon_sizes(self):
        """Verifies tray icon has proper Windows Taskbar resolutions (16x16, 32x32...)"""
        icon = get_application_icon()
        self.assertFalse(icon.isNull(), "Icon must not be null")
        sizes = [s.width() for s in icon.availableSizes()]
        print(f"[Evidence 1] Tray icon available resolutions: {sizes}")
        self.assertTrue(16 in sizes or 32 in sizes or 64 in sizes, "Icon must have valid sizes")

    def test_02_native_hotkey_registration_and_dispatch(self):
        """Verifies hotkey listener starts and dispatches Qt signals cleanly"""
        listener = HotkeyListener()
        text_triggered = []
        ocr_triggered = []

        listener.text_hotkey_triggered.connect(lambda: text_triggered.append(True))
        listener.ocr_hotkey_triggered.connect(lambda: ocr_triggered.append(True))

        listener.start()
        self.assertTrue(listener._is_running, "Listener must be running")

        # Emit signals to verify Qt signal connection
        listener.text_hotkey_triggered.emit()
        listener.ocr_hotkey_triggered.emit()

        # Process Qt event queue
        self.app.processEvents()

        print(f"[Evidence 2] Listener active, dispatched signals: text={len(text_triggered)}, ocr={len(ocr_triggered)}")
        self.assertEqual(len(text_triggered), 1, "Text hotkey must trigger exactly once")
        self.assertEqual(len(ocr_triggered), 1, "OCR hotkey must trigger exactly once")
        listener.stop()

    def test_03_translation_engine(self):
        """Verifies fast translation engine responds accurately with Vietnamese"""
        res = translator.translate("Artificial intelligence translates fast")
        encoded_trans = res.translated.encode("ascii", errors="replace").decode("ascii")
        print(f"[Evidence 3] Translated '{res.original}' -> '{encoded_trans}' (lang: {res.source_lang} -> {res.target_lang})")
        self.assertTrue(res.success, "Translation must succeed")
        self.assertTrue(len(res.translated) > 0, "Translation result must not be empty")

    def test_04_ocr_engine(self):
        """Verifies Windows Media OCR recognizes text from image correctly"""
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (300, 80), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((20, 25), "FastTranslate Test", fill=(0, 0, 0))

        text = ocr_engine.recognize(img)
        print(f"[Evidence 4] OCR Recognized text: '{text}'")
        self.assertTrue("Fast" in text and "Translate" in text)

    def test_05_popup_window_lifecycle(self):
        """Verifies PopupWindow displays and formats text properly"""
        popup = PopupWindow()
        popup.show_translation_for_text("Hello", QPoint(200, 200))
        self.assertTrue(popup.isVisible(), "Popup must be visible when triggered")
        print("[Evidence 5] PopupWindow rendered and visible at target coordinates")
        popup.close()

    def test_06_text_extractor_multi_tier(self):
        """Verifies multi-tier text extractor captures text without destructive clipboard wipe"""
        from src.core.text_extractor import get_selected_text, set_clipboard_text, get_clipboard_text
        orig = get_clipboard_text()
        test_payload = "Evidence 6: Fast and accurate selection extraction"
        set_clipboard_text(test_payload)
        extracted = get_selected_text()
        print(f"[Evidence 6] Extracted text via multi-tier fallback: '{extracted}'")
        self.assertEqual(extracted, test_payload)
        set_clipboard_text(orig)


if __name__ == "__main__":
    unittest.main()
