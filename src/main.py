import sys
import os
from pathlib import Path
import time
import traceback

# Ensure project root is in sys.path and is current working directory
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
    LOG_FILE = Path.home() / ".fast_translate" / "app.log"
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)
    LOG_FILE = PROJECT_ROOT / "app.log"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass
    try:
        if sys.stdout and not sys.stdout.closed:
            print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except Exception:
        pass


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    log("UNCAUGHT EXCEPTION:")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass


sys.excepthook = handle_uncaught_exception

# Fallback for stdout/stderr if executed without console
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from PySide6.QtCore import Qt, QPoint, QRunnable, QThreadPool, QObject, Signal, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from src.config import config
from src.core.hotkey_listener import HotkeyListener
from src.core.text_extractor import get_selected_text
from src.core.ocr_engine import ocr_engine
from src.core.autostart import is_autostart_enabled, enable_autostart
from src.ui.popup_window import PopupWindow
from src.ui.snipping_widget import SnippingWidget
from src.ui.tray_icon import TrayIcon
from src.ui.settings_dialog import SettingsDialog


class OCRTaskSignals(QObject):
    finished = Signal(str, QPoint)


class OCRTask(QRunnable):
    def __init__(self, pil_image, target_pos: QPoint):
        super().__init__()
        self.pil_image = pil_image
        self.target_pos = target_pos
        self.signals = OCRTaskSignals()

    def run(self):
        text = ocr_engine.recognize(self.pil_image)
        try:
            self.signals.finished.emit(text, self.target_pos)
        except RuntimeError:
            pass


class FastTranslateApp:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        # Single instance check via local named socket
        self.server_name = "FastTranslate_SingleInstance_Server_v2"
        self.local_server = None
        if not self._check_single_instance():
            log("[App] Another instance is already running. Exiting.")
            sys.exit(0)

        self.thread_pool = QThreadPool.globalInstance()

        # UI Components
        self.popup = PopupWindow()
        self.snipper = SnippingWidget()
        self.tray = TrayIcon()
        self.settings_dialog = SettingsDialog()
        self.hotkeys = HotkeyListener()

        self._bind_signals()

        # Check and ensure autostart if configured
        if config.get("autostart_with_windows", True) and not is_autostart_enabled():
            enable_autostart()

    def _check_single_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(500):
            # Another instance exists -> send wake-up signal to show popup
            try:
                socket.write(b"show\n")
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
            except Exception:
                pass
            return False

        # Create local server for this instance
        self.local_server = QLocalServer()
        self.local_server.removeServer(self.server_name)
        if not self.local_server.listen(self.server_name):
            log(f"[App] Warning: Could not listen on single instance server: {self.local_server.errorString()}")
        else:
            self.local_server.newConnection.connect(self._on_secondary_instance_ping)
        return True

    def _on_secondary_instance_ping(self):
        try:
            client = self.local_server.nextPendingConnection()
            if client:
                client.waitForReadyRead(300)
                client.close()
            log("[App] Received ping from run.bat / secondary instance -> triggering popup")
            self.handle_text_translation()
        except Exception as e:
            log(f"[App] Error handling secondary ping: {e}")

    def _bind_signals(self):
        # Hotkey bindings
        self.hotkeys.text_hotkey_triggered.connect(self.handle_text_translation)
        self.hotkeys.ocr_hotkey_triggered.connect(self.handle_ocr_capture)

        # Tray bindings
        self.tray.text_action_triggered.connect(self.handle_text_translation)
        self.tray.ocr_action_triggered.connect(self.handle_ocr_capture)
        self.tray.settings_action_triggered.connect(self.show_settings)

        # Settings dialog bindings
        self.settings_dialog.settings_saved.connect(self.handle_settings_saved)

        # Snipper bindings
        self.snipper.snippet_captured.connect(self.handle_snippet_captured)

    def show_settings(self):
        """Called when user clicks Settings in tray menu"""
        log("[App] show_settings triggered")
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def handle_settings_saved(self):
        """Called when user saves new settings from SettingsDialog"""
        log("[App] Settings saved, reloading hotkeys and tray labels...")
        self.hotkeys.reload()
        self.tray.update_labels()
        self.popup.source_lang = config.get("source_lang", "auto")
        self.popup.target_lang = config.get("target_lang", "vi")
        self.popup._update_lang_badge_display()
        try:
            self.tray.showMessage(
                "FastTranslate",
                "Đã lưu cài đặt và áp dụng phím tắt mới!",
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )
        except Exception:
            pass

    def handle_text_translation(self):
        """Called when user presses Alt+D or clicks tray action"""
        log("[App] handle_text_translation triggered")
        cursor_pos = QCursor.pos()
        text = get_selected_text()
        log(f"[App] Selected text extracted: {repr(text[:50]) if text else 'EMPTY'}")
        if text:
            self.popup.show_translation_for_text(text, cursor_pos)
        else:
            log("[App] No text captured, showing prompt popup")
            self.popup.show_empty_prompt(cursor_pos)

    def handle_ocr_capture(self):
        """Called when user presses Alt+Shift+D or clicks tray action"""
        log("[App] handle_ocr_capture triggered, opening snipper")
        self.snipper.start_snipping()

    def handle_snippet_captured(self, pil_image, target_pos: QPoint):
        """Called when user finishes snipping an area of the screen"""
        log("[App] Snippet captured, starting OCR task")
        # Immediately display popup in loading state
        self.popup.source_edit.setPlainText("🔍 Đang đọc chữ từ vùng chụp...")
        self.popup.target_edit.setPlainText("⏳ Vui lòng chờ...")
        self.popup.lang_badge.setText("OCR")
        self.popup.status_label.setText("Đang nhận diện...")
        self.popup.position_smartly(target_pos)
        self.popup.show()
        self.popup.raise_()
        self.popup.activateWindow()

        # Run OCR in background (retain reference to prevent GC)
        self._active_ocr_task = OCRTask(pil_image, target_pos)
        self._active_ocr_task.signals.finished.connect(self._on_ocr_finished)
        self.thread_pool.start(self._active_ocr_task)

    def _on_ocr_finished(self, text: str, target_pos: QPoint):
        log(f"[App] OCR finished, detected text length: {len(text) if text else 0}")
        if text and text.strip():
            self.popup.source_edit.setPlainText(text)
            self.popup.target_edit.setPlainText("⚡ Đang dịch sang tiếng Việt...")
            self.popup.status_label.setText(f"{len(text)} ký tự")
            self.popup.show_translation_for_text(text, target_pos)
        else:
            self.popup.source_edit.setPlainText("Không tìm thấy văn bản nào trong vùng chọn.")
            self.popup.target_edit.setPlainText("Mẹo: Hãy chụp vùng chứa chữ rõ nét, tránh nền quá phức tạp.")
            self.popup.lang_badge.setText("OCR: TRỐNG")
            self.popup.status_label.setText("")

    def run(self):
        log("[App] Starting application: showing tray icon")
        self.tray.show()
        log("[App] Starting hotkeys listener")
        self.hotkeys.start()
        # Show toast notification that app is active
        try:
            self.tray.notify_started()
        except Exception:
            pass
        log("[App] Entering main Qt event loop")
        ret = self.app.exec()
        log(f"[App] Qt event loop exited with code: {ret}")
        return ret


def main():
    log("[Main] FastTranslate starting...")
    app = FastTranslateApp()
    code = app.run()
    log(f"[Main] FastTranslate exiting with code: {code}")
    sys.exit(code)


if __name__ == "__main__":
    main()
