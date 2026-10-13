import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint
from src.core.tts_engine import tts_engine
from src.ui.popup_window import PopupWindow


class TestTTSAndSwap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.popup = PopupWindow()

    def tearDown(self):
        self.popup.close()

    def test_tts_engine_initialized(self):
        """Kiểm tra TTSEngine khởi tạo và nhận diện giọng đọc Windows"""
        self.assertIsNotNone(tts_engine)
        has_en = tts_engine.has_offline_voice_for("en")
        self.assertTrue(has_en, "Should have English offline voice on Windows")

    def test_swap_language_direction(self):
        """Kiểm tra nút đổi chiều ngôn ngữ VI <-> EN"""
        # Mặc định target_lang là vi
        self.assertEqual(self.popup.target_lang.lower(), "vi")

        # Đổi chiều sang VI -> EN
        self.popup.swap_language_direction()
        self.assertEqual(self.popup.source_lang.lower(), "vi")
        self.assertEqual(self.popup.target_lang.lower(), "en")
        self.assertIn("VI ➔ EN", self.popup.lang_badge.text())

        # Đổi chiều ngược lại sang AUTO -> VI
        self.popup.swap_language_direction()
        self.assertEqual(self.popup.target_lang.lower(), "vi")
        self.assertIn("➔ VI", self.popup.lang_badge.text())

    def test_set_language_pair(self):
        """Kiểm tra đặt cặp ngôn ngữ dịch tùy chọn (ví dụ Nhật, Hàn)"""
        self.popup.set_language_pair("auto", "ja")
        self.assertEqual(self.popup.target_lang.lower(), "ja")
        self.assertIn("AUTO ➔ JA", self.popup.lang_badge.text())

    def test_swap_swaps_text_when_available(self):
        """Kiểm tra đổi chiều tự động chuyển text kết quả sang ô input"""
        self.popup.source_edit.setPlainText("Hello world")
        self.popup.target_edit.setPlainText("Xin chào thế giới")

        self.popup.swap_language_direction()
        # Ô gốc phải nhận nội dung tiếng Việt "Xin chào thế giới"
        self.assertEqual(self.popup.source_edit.toPlainText(), "Xin chào thế giới")
        self.assertEqual(self.popup.source_lang, "vi")
        self.assertEqual(self.popup.target_lang, "en")

    def test_tts_buttons_trigger_speak(self):
        """Kiểm tra gọi speak_source_text và speak_target_text không gây crash"""
        self.popup.source_edit.setPlainText("Hello")
        self.popup.target_edit.setPlainText("Xin chào")

        # Gọi hàm phát âm (không lỗi)
        self.popup.speak_source_text()
        self.popup.speak_target_text()
        tts_engine.stop()


if __name__ == "__main__":
    unittest.main()
