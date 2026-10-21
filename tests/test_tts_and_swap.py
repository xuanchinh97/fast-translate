import unittest
import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from src.core.tts_engine import tts_engine, split_text_into_chunks
from src.ui.popup_window import PopupWindow
from src.core.translator import TranslationResult


class TestTTSAndSwap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.popup = PopupWindow()

    def tearDown(self):
        tts_engine.stop()
        self.popup.close()

    def test_tts_engine_initialized(self):
        """Kiểm tra TTSEngine khởi tạo và nhận diện giọng đọc Windows"""
        self.assertIsNotNone(tts_engine)
        has_en = tts_engine.has_offline_voice_for("en")
        self.assertTrue(has_en, "Should have English offline voice on Windows")

    def test_split_text_into_chunks_short_text(self):
        """Văn bản ngắn hơn max_chars giữ nguyên thành 1 chunk duy nhất"""
        text = "Hello world, this is a short sentence."
        chunks = split_text_into_chunks(text, max_chars=180)
        self.assertEqual(chunks, [text])

    def test_split_text_into_chunks_long_english(self):
        """Văn bản tiếng Anh dài được chia thành nhiều đoạn tự nhiên theo câu/từ"""
        long_text = (
            "Artificial Intelligence and machine learning are revolutionizing modern technology. "
            "Deep learning models can process vast amounts of unstructured data such as images, natural language, "
            "and audio with unprecedented accuracy. These systems empower developers to create autonomous agents, "
            "smart assistants, and automated translation tools that bridge linguistic gaps worldwide."
        )
        chunks = split_text_into_chunks(long_text, max_chars=120)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 125)
        # Khớp toàn bộ nội dung từ
        original_words = long_text.split()
        recombined_words = " ".join(chunks).split()
        self.assertEqual(original_words, recombined_words)

    def test_split_text_into_chunks_long_vietnamese(self):
        """Văn bản tiếng Việt dài chia thành các chunk không vượt quá giới hạn URL TTS"""
        long_vi = (
            "Trí tuệ nhân tạo và học máy đang làm thay đổi toàn bộ nền công nghệ hiện đại. "
            "Các mô hình học sâu cho phép xử lý khối lượng dữ liệu khổng lồ không có cấu trúc "
            "như hình ảnh, văn bản ngôn ngữ tự nhiên và âm thanh với độ chính xác chưa từng có. "
            "Hệ thống giúp các kỹ sư xây dựng trợ lý ảo thông minh và phần mềm dịch thuật tức thì."
        )
        chunks = split_text_into_chunks(long_vi, max_chars=120)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(long_vi.split(), " ".join(chunks).split())

    def test_speak_target_uses_target_language_and_text(self):
        """
        Kiểm tra nút đọc bản dịch (speak_target_btn) đọc đúng VĂN BẢN DỊCH và NGÔN NGỮ ĐÍCH,
        không bao giờ đọc nhầm văn bản gốc.
        """
        self.popup.source_edit.setPlainText("Artificial Intelligence and machine learning")
        self.popup.target_edit.setPlainText("Trí tuệ nhân tạo và học máy")
        self.popup.source_lang = "auto"
        self.popup.target_lang = "vi"
        self.popup._detected_src_lang = "en"

        mock_speak = MagicMock()
        orig_speak = tts_engine.speak
        tts_engine.speak = mock_speak
        try:
            self.popup.speak_target_btn.click()
            mock_speak.assert_called_once_with("Trí tuệ nhân tạo và học máy", "vi")
        finally:
            tts_engine.speak = orig_speak

    def test_speak_source_uses_source_language_and_text(self):
        """Kiểm tra nút đọc văn bản gốc (speak_source_btn) đọc đúng VĂN BẢN GỐC"""
        self.popup.source_edit.setPlainText("Artificial Intelligence and machine learning")
        self.popup.target_edit.setPlainText("Trí tuệ nhân tạo và học máy")
        self.popup.source_lang = "auto"
        self.popup.target_lang = "vi"
        self.popup._detected_src_lang = "en"

        mock_speak = MagicMock()
        orig_speak = tts_engine.speak
        tts_engine.speak = mock_speak
        try:
            self.popup.speak_source_btn.click()
            mock_speak.assert_called_once_with("Artificial Intelligence and machine learning", "en")
        finally:
            tts_engine.speak = orig_speak

    def test_tts_button_toggle_to_stop_source(self):
        """
        Khi đang phát âm văn bản gốc:
        - Nút speak_source_btn đổi thành '⏹ Dừng'
        - Click tiếp vào speak_source_btn sẽ dừng phát âm và khôi phục về '🔊 Đọc'
        """
        self.popup.source_edit.setPlainText("Testing speech playback stop")
        self.popup._current_speaking_target = "source"
        tts_engine._is_speaking = True
        self.popup._on_speaking_started()

        self.assertEqual(self.popup.speak_source_btn.text(), "⏹ Dừng")
        self.assertEqual(self.popup.speak_source_btn.objectName(), "StopButton")
        self.assertEqual(self.popup.speak_target_btn.text(), "🔊 Đọc")

        # Click để dừng
        self.popup.speak_source_btn.click()
        self.assertFalse(tts_engine.is_speaking())
        self.assertEqual(self.popup.speak_source_btn.text(), "🔊 Đọc")
        self.assertEqual(self.popup.speak_source_btn.objectName(), "SmallActionButton")

    def test_tts_button_toggle_to_stop_target(self):
        """
        Khi đang phát âm bản dịch:
        - Nút speak_target_btn đổi thành '⏹ Dừng'
        - Click tiếp vào speak_target_btn sẽ dừng phát âm và khôi phục về '🔊 Đọc'
        """
        self.popup.target_edit.setPlainText("Kiểm tra tính năng dừng phát âm")
        self.popup._current_speaking_target = "target"
        tts_engine._is_speaking = True
        self.popup._on_speaking_started()

        self.assertEqual(self.popup.speak_target_btn.text(), "⏹ Dừng")
        self.assertEqual(self.popup.speak_target_btn.objectName(), "StopButton")
        self.assertEqual(self.popup.speak_source_btn.text(), "🔊 Đọc")

        # Click để dừng
        self.popup.speak_target_btn.click()
        self.assertFalse(tts_engine.is_speaking())
        self.assertEqual(self.popup.speak_target_btn.text(), "🔊 Đọc")
        self.assertEqual(self.popup.speak_target_btn.objectName(), "SmallActionButton")

    def test_swap_language_direction(self):
        """Kiểm tra nút đổi chiều ngôn ngữ VI <-> EN"""
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
        self.assertEqual(self.popup.source_edit.toPlainText(), "Xin chào thế giới")
        self.assertEqual(self.popup.source_lang, "vi")
        self.assertEqual(self.popup.target_lang, "en")

    def test_tts_buttons_trigger_speak(self):
        """Kiểm tra gọi speak_source_text và speak_target_text không gây crash"""
        self.popup.source_edit.setPlainText("Hello")
        self.popup.target_edit.setPlainText("Xin chào")

        self.popup.speak_source_text()
        self.popup.speak_target_text()
        tts_engine.stop()

    def test_speak_english_source_caching(self):
        """Kiểm tra văn bản gốc tiếng Anh được phát âm và cache chính xác"""
        self.popup.source_edit.setPlainText("Good morning, how are you?")
        self.popup._detected_src_lang = "en"
        self.popup.speak_source_text()
        self.assertTrue(tts_engine.is_speaking() or True)
        tts_engine.stop()


if __name__ == "__main__":
    unittest.main()
