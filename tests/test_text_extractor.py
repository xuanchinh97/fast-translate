import unittest
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.text_extractor import (
    get_clipboard_text,
    set_clipboard_text,
    get_selected_text,
    wait_for_modifiers_released,
    release_modifiers,
    send_ctrl_c,
    make_key,
    VK_MENU,
    VK_CONTROL,
    VK_C
)
from src.config import config


class TestTextExtractor(unittest.TestCase):
    def setUp(self):
        self._orig_clip = get_clipboard_text()

    def tearDown(self):
        set_clipboard_text(self._orig_clip)

    def test_clipboard_unicode_read_write(self):
        """Kiểm tra đọc và ghi clipboard hỗ trợ đầy đủ tiếng Việt có dấu và Unicode"""
        test_str = "Kiểm tra trích xuất văn bản tiếng Việt: Xin chào thế giới 123! @#$"
        success = set_clipboard_text(test_str)
        self.assertTrue(success, "Writing Unicode text to clipboard must succeed")

        read_back = get_clipboard_text()
        self.assertEqual(read_back, test_str, "Read back text must match exactly")

    def test_make_key_input_structure(self):
        """Kiểm tra hàm tạo INPUT structure với virtual key và scan code chuẩn"""
        inp = make_key(VK_C, scan=0x2E, flags=0)
        self.assertEqual(inp.type, 1)
        self.assertEqual(inp.union.ki.wVk, VK_C)
        self.assertEqual(inp.union.ki.wScan, 0x2E)

    def test_wait_for_modifiers_timeout(self):
        """Kiểm tra hàm chờ nhả phím modifier không bị treo vô hạn"""
        t0 = time.time()
        wait_for_modifiers_released(timeout_sec=0.1)
        dur = time.time() - t0
        self.assertLess(dur, 0.3, "wait_for_modifiers_released must respect timeout")

    def test_get_selected_text_returns_empty_when_no_selection(self):
        """Kiểm tra khi không bôi đen chữ mới: get_selected_text trả về rỗng thay vì text cũ"""
        test_sample = "Old clipboard content from previous action"
        set_clipboard_text(test_sample)

        # Khi không có vùng chọn mới nào (sequence number không đổi), hàm phải trả về ""
        extracted = get_selected_text()
        self.assertEqual(extracted, "", "Must return empty string when no new text is selected")

    def test_get_selected_text_captures_when_selection_copied(self):
        """Kiểm tra khi có vùng chọn mới được copy: trích xuất đúng text mới"""
        from unittest.mock import patch
        test_sample = "Newly selected text"
        set_clipboard_text(test_sample)

        # Giả lập sequence number thay đổi (ứng dụng đích vừa hoàn thành copy vùng chọn)
        with patch("src.core.text_extractor.user32.GetClipboardSequenceNumber", side_effect=[100, 101, 101, 101]):
            extracted = get_selected_text()
        self.assertEqual(extracted, test_sample)

    def test_restore_clipboard_functionality(self):
        """Kiểm tra tùy chọn khôi phục clipboard cũ khi cấu hình bật"""
        config.set("restore_clipboard", True)
        set_clipboard_text("Old clipboard content")
        self.assertEqual(get_clipboard_text(), "Old clipboard content")


if __name__ == "__main__":
    unittest.main()
