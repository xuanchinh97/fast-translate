from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QColor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QGroupBox, QGraphicsDropShadowEffect,
    QWidget, QFrame
)
from src.config import config
from src.core.autostart import is_autostart_enabled, set_autostart
from src.ui.styles import DARK_THEME


class HotkeyEdit(QLineEdit):
    """Ô nhập liệu hỗ trợ bấm tổ hợp phím trực quan"""
    hotkey_changed = Signal(str)

    def __init__(self, current_hotkey: str = "", parent=None):
        super().__init__(parent)
        self._current_hotkey = current_hotkey.strip().lower()
        self.setText(self._format_display(self._current_hotkey))
        self.setReadOnly(True)
        self._is_recording = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_normal_style()

    def _format_display(self, hk: str) -> str:
        return hk.upper() if hk else "CHƯA ĐẶT"

    def get_hotkey(self) -> str:
        return self._current_hotkey

    def set_hotkey(self, hk: str):
        self._current_hotkey = hk.strip().lower()
        self.setText(self._format_display(self._current_hotkey))

    def _apply_normal_style(self):
        self.setStyleSheet("""
            QLineEdit {
                background-color: #24242e;
                border: 1px solid #3d3d4e;
                border-radius: 6px;
                color: #60a5fa;
                font-family: 'Segoe UI', sans-serif;
                font-weight: 600;
                font-size: 12px;
                padding: 6px 10px;
                text-align: center;
            }
            QLineEdit:hover {
                border-color: #4f4f65;
                background-color: #292934;
            }
        """)

    def _apply_recording_style(self):
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2c2238;
                border: 2px solid #a855f7;
                border-radius: 6px;
                color: #e9d5ff;
                font-family: 'Segoe UI', sans-serif;
                font-weight: bold;
                font-size: 12px;
                padding: 5px 10px;
            }
        """)

    def mousePressEvent(self, event):
        self._start_recording()

    def focusOutEvent(self, event):
        if self._is_recording:
            self._stop_recording(self._current_hotkey)
        super().focusOutEvent(event)

    def _start_recording(self):
        self._is_recording = True
        self.setText("Nhấn tổ hợp phím...")
        self._apply_recording_style()

    def _stop_recording(self, new_hotkey: str):
        self._is_recording = False
        self._current_hotkey = new_hotkey.strip().lower()
        self.setText(self._format_display(self._current_hotkey))
        self._apply_normal_style()
        self.hotkey_changed.emit(self._current_hotkey)

    def keyPressEvent(self, event: QKeyEvent):
        if not self._is_recording:
            super().keyPressEvent(event)
            return

        key = event.key()

        # Bấm Esc để hủy ghi phím
        if key == Qt.Key.Key_Escape:
            self._stop_recording(self._current_hotkey)
            return

        # Bấm Backspace hoặc Delete để xóa phím tắt
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self._stop_recording("")
            return

        # Bỏ qua nếu chỉ bấm riêng các phím bổ trợ
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        modifiers = []
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("ctrl")
        if mods & Qt.KeyboardModifier.AltModifier:
            modifiers.append("alt")
        if mods & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("shift")
        if mods & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("win")

        # Map tên phím chính
        key_name = ""
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_name = chr(key).lower()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_name = chr(key).lower()
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_name = f"f{key - Qt.Key.Key_F1 + 1}"
        elif key == Qt.Key.Key_Space:
            key_name = "space"

        if key_name and modifiers:
            result_hotkey = "+".join(modifiers + [key_name])
            self._stop_recording(result_hotkey)


class SettingsDialog(QDialog):
    """Cửa sổ cài đặt FastTranslate"""
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt FastTranslate")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.resize(440, 480)
        self.setStyleSheet(DARK_THEME + """
            QDialog {
                background-color: #1a1a20;
            }
            QGroupBox {
                border: 1px solid #333342;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 10px;
                color: #93c5fd;
                font-size: 11px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QComboBox {
                background-color: #24242e;
                border: 1px solid #3d3d4e;
                border-radius: 6px;
                color: #f1f5f9;
                padding: 5px 10px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e24;
                border: 1px solid #3d3d4e;
                color: #f1f5f9;
                selection-background-color: #2563eb;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #4a4a5e;
                background-color: #24242e;
            }
            QCheckBox::indicator:checked {
                background-color: #2563eb;
                border-color: #3b82f6;
            }
        """)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Header Title
        header = QHBoxLayout()
        title_label = QLabel("⚡ CÀI ĐẶT FASTTRANSLATE")
        title_label.setStyleSheet("color: #60a5fa; font-size: 14px; font-weight: bold; letter-spacing: 0.5px;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)

        # --- Section 1: Phím tắt toàn cục ---
        hk_group = QGroupBox("PHÍM TẮT TOÀN CỤC (HOTKEYS)")
        hk_layout = QVBoxLayout(hk_group)
        hk_layout.setSpacing(10)

        # Hotkey Text
        row_text = QHBoxLayout()
        lbl_text = QLabel("Dịch văn bản bôi đen:")
        lbl_text.setStyleSheet("color: #d1d5db; font-size: 12px;")
        self.edit_hk_text = HotkeyEdit(config.get("hotkey_text", "alt+d"))
        row_text.addWidget(lbl_text)
        row_text.addStretch()
        row_text.addWidget(self.edit_hk_text)
        hk_layout.addLayout(row_text)

        # Hotkey OCR
        row_ocr = QHBoxLayout()
        lbl_ocr = QLabel("Chụp màn hình OCR:")
        lbl_ocr.setStyleSheet("color: #d1d5db; font-size: 12px;")
        self.edit_hk_ocr = HotkeyEdit(config.get("hotkey_ocr", "alt+shift+d"))
        row_ocr.addWidget(lbl_ocr)
        row_ocr.addStretch()
        row_ocr.addWidget(self.edit_hk_ocr)
        hk_layout.addLayout(row_ocr)

        tip_label = QLabel("👉 Nhấp vào ô trên rồi bấm tổ hợp phím mong muốn (Esc để hủy).")
        tip_label.setStyleSheet("color: #71717a; font-size: 10px; font-style: italic;")
        hk_layout.addWidget(tip_label)

        layout.addWidget(hk_group)

        # --- Section 2: Ngôn ngữ mặc định ---
        lang_group = QGroupBox("NGÔN NGỮ MẶC ĐỊNH")
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(10)

        # Nguồn
        row_src = QHBoxLayout()
        lbl_src = QLabel("Ngôn ngữ nguồn:")
        lbl_src.setStyleSheet("color: #d1d5db; font-size: 12px;")
        self.combo_src = QComboBox()
        self.combo_src.addItem("Tự động phát hiện (Auto)", "auto")
        self.combo_src.addItem("Tiếng Anh (English)", "en")
        self.combo_src.addItem("Tiếng Việt (Vietnamese)", "vi")
        self._select_combo_data(self.combo_src, config.get("source_lang", "auto"))
        row_src.addWidget(lbl_src)
        row_src.addStretch()
        row_src.addWidget(self.combo_src)
        lang_layout.addLayout(row_src)

        # Đích
        row_tgt = QHBoxLayout()
        lbl_tgt = QLabel("Ngôn ngữ đích:")
        lbl_tgt.setStyleSheet("color: #d1d5db; font-size: 12px;")
        self.combo_tgt = QComboBox()
        self.combo_tgt.addItem("Tiếng Việt (vi)", "vi")
        self.combo_tgt.addItem("Tiếng Anh (en)", "en")
        self.combo_tgt.addItem("Tiếng Nhật (ja)", "ja")
        self.combo_tgt.addItem("Tiếng Hàn (ko)", "ko")
        self.combo_tgt.addItem("Tiếng Trung (zh-cn)", "zh-cn")
        self.combo_tgt.addItem("Tiếng Pháp (fr)", "fr")
        self._select_combo_data(self.combo_tgt, config.get("target_lang", "vi"))
        row_tgt.addWidget(lbl_tgt)
        row_tgt.addStretch()
        row_tgt.addWidget(self.combo_tgt)
        lang_layout.addLayout(row_tgt)

        layout.addWidget(lang_group)

        # --- Section 3: Tùy chọn hệ thống ---
        sys_group = QGroupBox("TÙY CHỌN HỆ THỐNG")
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setSpacing(8)

        self.chk_autostart = QCheckBox("Khởi động cùng Windows sau khi mở máy")
        self.chk_autostart.setChecked(is_autostart_enabled())
        sys_layout.addWidget(self.chk_autostart)

        self.chk_autoclose = QCheckBox("Tự đóng cửa sổ popup khi bấm chuột ra ngoài")
        self.chk_autoclose.setChecked(config.get("auto_close_on_focus_loss", True))
        sys_layout.addWidget(self.chk_autoclose)

        self.chk_clipboard = QCheckBox("Khôi phục nội dung Clipboard cũ sau khi lấy văn bản")
        self.chk_clipboard.setChecked(config.get("restore_clipboard", True))
        sys_layout.addWidget(self.chk_clipboard)

        layout.addWidget(sys_group)

        layout.addStretch()

        # --- Footer Buttons ---
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_default = QPushButton("↺ Đặt lại mặc định")
        self.btn_default.setObjectName("SmallActionButton")
        self.btn_default.clicked.connect(self._reset_defaults)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Lưu cài đặt")
        self.btn_save.setObjectName("CopyButton")
        self.btn_save.clicked.connect(self._save_settings)

        btn_bar.addWidget(self.btn_default)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_cancel)
        btn_bar.addWidget(self.btn_save)
        layout.addLayout(btn_bar)

    def _select_combo_data(self, combo: QComboBox, data_val: str):
        for i in range(combo.count()):
            if combo.itemData(i) == data_val:
                combo.setCurrentIndex(i)
                return

    def _reset_defaults(self):
        """Khôi phục các thông số về mặc định ban đầu"""
        self.edit_hk_text.set_hotkey("alt+d")
        self.edit_hk_ocr.set_hotkey("alt+shift+d")
        self._select_combo_data(self.combo_src, "auto")
        self._select_combo_data(self.combo_tgt, "vi")
        self.chk_autostart.setChecked(True)
        self.chk_autoclose.setChecked(True)
        self.chk_clipboard.setChecked(True)

    def _save_settings(self):
        """Lưu toàn bộ cài đặt vào config.json và áp dụng ngay"""
        hk_text = self.edit_hk_text.get_hotkey() or "alt+d"
        hk_ocr = self.edit_hk_ocr.get_hotkey() or "alt+shift+d"
        src_lang = self.combo_src.currentData()
        tgt_lang = self.combo_tgt.currentData()
        autostart_val = self.chk_autostart.isChecked()
        autoclose_val = self.chk_autoclose.isChecked()
        clipboard_val = self.chk_clipboard.isChecked()

        config.set("hotkey_text", hk_text)
        config.set("hotkey_ocr", hk_ocr)
        config.set("source_lang", src_lang)
        config.set("target_lang", tgt_lang)
        config.set("autostart_with_windows", autostart_val)
        config.set("auto_close_on_focus_loss", autoclose_val)
        config.set("restore_clipboard", clipboard_val)

        # Cập nhật registry / startup shortcut
        set_autostart(autostart_val)

        self.settings_saved.emit()
        self.accept()
