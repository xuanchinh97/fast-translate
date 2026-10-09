from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from src.config import config
from src.core.autostart import is_autostart_enabled, set_autostart


def get_application_icon() -> QIcon:
    """Returns the crisp multi-resolution .ico icon if available, or fallback QIcon"""
    icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "icon.ico"
    if icon_path.exists():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon

    # Fallback programmatic icon
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(37, 99, 235))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setFont(QFont("Segoe UI", 30, QFont.Weight.Bold))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    text_action_triggered = Signal()
    ocr_action_triggered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(get_application_icon())
        self.setToolTip("FastTranslate - Dịch thuật nhanh Windows")
        self.init_menu()
        self.activated.connect(self._on_activated)

    def init_menu(self):
        menu = QMenu()

        title_action = menu.addAction("⚡ FastTranslate")
        title_action.setEnabled(False)

        menu.addSeparator()

        text_hk = config.get("hotkey_text", "alt+d").upper()
        ocr_hk = config.get("hotkey_ocr", "alt+shift+d").upper()

        text_act = menu.addAction(f"Dịch văn bản bôi đen ({text_hk})")
        text_act.triggered.connect(self.text_action_triggered.emit)

        ocr_act = menu.addAction(f"Chụp màn hình OCR ({ocr_hk})")
        ocr_act.triggered.connect(self.ocr_action_triggered.emit)

        menu.addSeparator()

        clip_act = menu.addAction("Khôi phục clipboard cũ")
        clip_act.setCheckable(True)
        clip_act.setChecked(config.get("restore_clipboard", True))
        clip_act.toggled.connect(lambda val: config.set("restore_clipboard", val))

        autoclose_act = menu.addAction("Tự đóng khi bấm ra ngoài")
        autoclose_act.setCheckable(True)
        autoclose_act.setChecked(config.get("auto_close_on_focus_loss", True))
        autoclose_act.toggled.connect(lambda val: config.set("auto_close_on_focus_loss", val))

        autostart_act = menu.addAction("Khởi động cùng Windows")
        autostart_act.setCheckable(True)
        autostart_act.setChecked(is_autostart_enabled())
        autostart_act.toggled.connect(self._handle_autostart_toggle)

        menu.addSeparator()

        quit_act = menu.addAction("Thoát")
        quit_act.triggered.connect(QApplication.instance().quit)

        self.setContextMenu(menu)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            text_hk = config.get("hotkey_text", "alt+d").upper()
            ocr_hk = config.get("hotkey_ocr", "alt+shift+d").upper()
            self.showMessage(
                "FastTranslate",
                f"Đang hoạt động!\n👉 {text_hk}: Dịch từ bôi đen\n👉 {ocr_hk}: Chụp màn hình OCR",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )

    def _handle_autostart_toggle(self, enabled: bool):
        from src.core.autostart import set_autostart
        set_autostart(enabled)
        config.set("autostart_with_windows", enabled)

    def notify_started(self):
        """Displays balloon notification in Windows Notification Center confirming app is active"""
        text_hk = config.get("hotkey_text", "alt+d").upper()
        ocr_hk = config.get("hotkey_ocr", "alt+shift+d").upper()
        self.showMessage(
            "FastTranslate - Đã khởi động",
            f"Ứng dụng đang chạy ngầm!\n• {text_hk}: Dịch văn bản bôi đen\n• {ocr_hk}: Chụp màn hình OCR",
            QSystemTrayIcon.MessageIcon.Information,
            3500
        )
