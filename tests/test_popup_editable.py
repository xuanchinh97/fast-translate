import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QKeyEvent
from src.ui.popup_window import PopupWindow, SourceTextEdit
from src.core.translator import TranslationResult


class TestPopupEditable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.popup = PopupWindow()

    def tearDown(self):
        self.popup.close()

    def test_source_edit_is_editable(self):
        """Kiểm tra ô văn bản gốc cho phép chỉnh sửa trực tiếp"""
        self.assertFalse(self.popup.source_edit.isReadOnly(), "source_edit must be editable (not read-only)")

    def test_source_edit_text_change_and_manual_translation(self):
        """Kiểm tra sửa nội dung và kích hoạt dịch lại thủ công"""
        self.popup.show_translation_for_text("Hello", QPoint(100, 100))
        self.app.processEvents()
        self.assertEqual(self.popup.source_edit.toPlainText(), "Hello")

        # Người dùng sửa nội dung trong ô input
        self.popup.source_edit.setPlainText("Good morning")
        self.assertEqual(self.popup.source_edit.toPlainText(), "Good morning")

        # Gọi dịch lại thủ công
        self.popup.trigger_manual_translation()
        self.assertEqual(self.popup._last_translated_text, "Good morning")
        self.assertIn("Đang dịch", self.popup.target_edit.toPlainText())

    def test_clear_source_text(self):
        """Kiểm tra nút xóa trắng ô input"""
        self.popup.source_edit.setPlainText("Some text to clear")
        self.popup.clear_source_text()
        self.assertEqual(self.popup.source_edit.toPlainText(), "")
        self.assertEqual(self.popup._last_translated_text, "")

    def test_ctrl_enter_shortcut_signal(self):
        """Kiểm tra phím tắt Ctrl+Enter kích hoạt tín hiệu submit_requested"""
        triggered = []
        self.popup.source_edit.submit_requested.connect(lambda: triggered.append(True))

        # Giả lập sự kiện gõ Ctrl+Enter
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Return,
            Qt.KeyboardModifier.ControlModifier,
            "\r"
        )
        self.popup.source_edit.keyPressEvent(event)
        self.assertTrue(len(triggered) == 1, "Ctrl+Enter must emit submit_requested signal")

    def test_esc_shortcut_signal(self):
        """Kiểm tra phím tắt Esc kích hoạt tín hiệu escape_requested"""
        triggered = []
        self.popup.source_edit.escape_requested.connect(lambda: triggered.append(True))

        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_Escape,
            Qt.KeyboardModifier.NoModifier,
            ""
        )
        self.popup.source_edit.keyPressEvent(event)
        self.assertTrue(len(triggered) == 1, "Esc must emit escape_requested signal")

    def test_retry_button_visibility_on_error(self):
        """Kiểm tra nút Thử lại: ẩn mặc định, chỉ hiện khi gặp lỗi"""
        self.popup.show()
        # Mặc định phải ẩn
        self.assertTrue(self.popup.retranslate_btn.isHidden(), "Retry button should be hidden by default")

        # Giả lập kết quả lỗi dịch
        error_res = TranslationResult(
            original="test",
            translated="",
            source_lang="EN",
            target_lang="VI",
            success=False,
            error_message="Lỗi mạng"
        )
        self.popup.source_edit.setPlainText("test")
        self.popup._on_translation_finished(error_res)
        self.assertFalse(self.popup.retranslate_btn.isHidden(), "Retry button must be visible on error")
        self.assertEqual(self.popup.retranslate_btn.text(), "↻ Thử lại")

        # Giả lập kết quả thành công
        success_res = TranslationResult(
            original="test",
            translated="thử nghiệm",
            source_lang="EN",
            target_lang="VI",
            success=True
        )
        self.popup._on_translation_finished(success_res)
        self.assertTrue(self.popup.retranslate_btn.isHidden(), "Retry button must be hidden on success")

    def test_empty_state_display(self):
        """Kiểm tra show_empty_prompt hiển thị đúng empty state và vô hiệu hóa nút copy"""
        self.popup.show_empty_prompt(QPoint(100, 100))
        self.assertEqual(self.popup.source_edit.toPlainText(), "")
        self.assertEqual(self.popup.target_edit.toPlainText(), "")
        self.assertEqual(self.popup.target_edit.property("state"), "empty")
        self.assertFalse(self.popup.copy_btn.isEnabled(), "Copy button must be disabled in empty state")
        self.assertIn("Chưa phát hiện chữ bôi đen", self.popup.status_label.text())

    def test_copy_button_state_and_visual_feedback(self):
        """Kiểm tra nút copy: disabled khi lỗi, enabled khi thành công và đổi text khi click"""
        # 1. Trạng thái lỗi: copy disabled
        error_res = TranslationResult("hello", "", "EN", "VI", success=False, error_message="Net error")
        self.popup.source_edit.setPlainText("hello")
        self.popup._on_translation_finished(error_res)
        self.assertFalse(self.popup.copy_btn.isEnabled())

        # 2. Trạng thái thành công: copy enabled
        success_res = TranslationResult("hello", "xin chào", "EN", "VI", success=True)
        self.popup.source_edit.setPlainText("hello")
        self.popup._on_translation_finished(success_res)
        self.assertTrue(self.popup.copy_btn.isEnabled())

        # 3. Click copy -> Đổi nhãn thành "✓ Đã chép!"
        self.popup.copy_btn.click()
        self.assertEqual(self.popup.copy_btn.text(), "✓ Đã chép!")
        self.assertEqual(self.popup.copy_btn.property("copied"), "true")

    def test_keyboard_navigation_shortcuts(self):
        """Kiểm tra phím tắt Ctrl+T đổi chiều ngôn ngữ từ ngoài popup"""
        self.assertEqual(self.popup.target_lang.lower(), "vi")
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier, "")
        self.popup.keyPressEvent(event)
        self.assertEqual(self.popup.source_lang.lower(), "vi")
        self.assertEqual(self.popup.target_lang.lower(), "en")


if __name__ == "__main__":
    unittest.main()
