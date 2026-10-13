import unittest
import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from src.config import config
from src.ui.settings_dialog import SettingsDialog, HotkeyEdit


class TestSettingsDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self._orig_config = config.data.copy()
        self.dialog = SettingsDialog()

    def tearDown(self):
        self.dialog.close()
        config.data = self._orig_config.copy()
        config.save()

    def test_hotkey_edit_initial_value(self):
        """Kiểm tra HotkeyEdit khởi tạo đúng định dạng viết hoa"""
        hk = HotkeyEdit("alt+d")
        self.assertEqual(hk.get_hotkey(), "alt+d")
        self.assertEqual(hk.text(), "ALT+D")

    def test_hotkey_edit_recording_key(self):
        """Kiểm tra quá trình ghi nhận phím tắt khi người dùng bấm phím"""
        hk = HotkeyEdit("alt+d")
        hk._start_recording()
        self.assertTrue(hk._is_recording)

        # Mô phỏng bấm Ctrl + Alt + T
        event = QKeyEvent(
            QKeyEvent.Type.KeyPress,
            Qt.Key.Key_T,
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
            "t"
        )
        hk.keyPressEvent(event)
        self.assertFalse(hk._is_recording)
        self.assertIn("ctrl", hk.get_hotkey())
        self.assertIn("alt", hk.get_hotkey())
        self.assertIn("t", hk.get_hotkey())

    def test_hotkey_edit_escape_cancels(self):
        """Bấm Esc hủy quá trình ghi, giữ nguyên hotkey cũ"""
        hk = HotkeyEdit("alt+d")
        hk._start_recording()
        esc_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        hk.keyPressEvent(esc_event)
        self.assertFalse(hk._is_recording)
        self.assertEqual(hk.get_hotkey(), "alt+d")

    def test_hotkey_edit_backspace_clears(self):
        """Bấm Backspace/Delete xóa hotkey"""
        hk = HotkeyEdit("alt+d")
        hk._start_recording()
        bs_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Backspace, Qt.KeyboardModifier.NoModifier)
        hk.keyPressEvent(bs_event)
        self.assertFalse(hk._is_recording)
        self.assertEqual(hk.get_hotkey(), "")
        self.assertEqual(hk.text(), "CHƯA ĐẶT")

    def test_reset_defaults(self):
        """Kiểm tra nút đặt lại mặc định khôi phục các giá trị chuẩn"""
        self.dialog.edit_hk_text.set_hotkey("ctrl+shift+x")
        self.dialog.chk_autostart.setChecked(False)

        self.dialog._reset_defaults()
        self.assertEqual(self.dialog.edit_hk_text.get_hotkey(), "alt+d")
        self.assertEqual(self.dialog.edit_hk_ocr.get_hotkey(), "alt+shift+d")
        self.assertTrue(self.dialog.chk_autostart.isChecked())
        self.assertTrue(self.dialog.chk_autoclose.isChecked())
        self.assertTrue(self.dialog.chk_clipboard.isChecked())

    @patch("src.ui.settings_dialog.set_autostart")
    def test_save_settings_emits_and_persists(self, mock_set_autostart):
        """Kiểm tra lưu cài đặt phát tín hiệu settings_saved và cập nhật config"""
        signal_received = []
        self.dialog.settings_saved.connect(lambda: signal_received.append(True))

        self.dialog.edit_hk_text.set_hotkey("alt+t")
        self.dialog.edit_hk_ocr.set_hotkey("alt+shift+o")
        self.dialog._select_combo_data(self.dialog.combo_src, "en")
        self.dialog._select_combo_data(self.dialog.combo_tgt, "ja")
        self.dialog.chk_autostart.setChecked(False)

        self.dialog._save_settings()

        self.assertTrue(len(signal_received) > 0, "settings_saved signal should be emitted")
        self.assertEqual(config.get("hotkey_text"), "alt+t")
        self.assertEqual(config.get("hotkey_ocr"), "alt+shift+o")
        self.assertEqual(config.get("source_lang"), "en")
        self.assertEqual(config.get("target_lang"), "ja")
        self.assertFalse(config.get("autostart_with_windows"))
        mock_set_autostart.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
