from PySide6.QtCore import Qt, QPoint, QRunnable, QThreadPool, QObject, Signal, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGraphicsDropShadowEffect, QFrame, QSizePolicy
)
import pyperclip
from src.config import config
from src.core.translator import translator, TranslationResult
from src.ui.styles import DARK_THEME


class TranslationSignals(QObject):
    finished = Signal(TranslationResult)


class TranslationTask(QRunnable):
    def __init__(self, text: str):
        super().__init__()
        self.text = text
        self.signals = TranslationSignals()

    def run(self):
        result = translator.translate(self.text)
        try:
            self.signals.finished.emit(result)
        except RuntimeError:
            pass


class SourceTextEdit(QTextEdit):
    """QTextEdit hỗ trợ chỉnh sửa văn bản gốc với phím tắt Ctrl+Enter và Esc"""
    submit_requested = Signal()
    escape_requested = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escape_requested.emit()
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.submit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class PopupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_pinned = False
        self._drag_pos = None
        self._is_programmatic_change = False
        self._last_translated_text = ""
        self._active_translation_task = None

        # Debounce timer tự động dịch sau khi người dùng dừng gõ 600ms
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(600)
        self._debounce_timer.timeout.connect(self._on_source_text_debounced)

        self.init_window_flags()
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

    def init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(config.get("window_width", 390), config.get("window_height", 270))

    def init_ui(self):
        # Outer layout with margins for drop shadow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Card container
        self.card = QWidget(self)
        self.card.setObjectName("MainCard")
        self.card.setStyleSheet(DARK_THEME)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(14, 10, 14, 12)
        card_layout.setSpacing(6)

        # --- Header ---
        header = QHBoxLayout()
        header.setSpacing(6)

        self.title_label = QLabel("FAST TRANSLATE")
        self.title_label.setObjectName("HeaderTitle")

        self.lang_badge = QLabel("AUTO ➔ VI")
        self.lang_badge.setObjectName("LangBadge")

        header.addWidget(self.title_label)
        header.addWidget(self.lang_badge)
        header.addStretch()

        self.pin_btn = QPushButton("📌")
        self.pin_btn.setObjectName("IconButton")
        self.pin_btn.setToolTip("Ghim cửa sổ (Không tự đóng)")
        self.pin_btn.clicked.connect(self.toggle_pin)

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("IconButton")
        self.close_btn.setToolTip("Đóng (Esc)")
        self.close_btn.clicked.connect(self.hide)

        header.addWidget(self.pin_btn)
        header.addWidget(self.close_btn)
        card_layout.addLayout(header)

        # --- Source Text Header & Quick Actions ---
        source_bar = QHBoxLayout()
        source_bar.setContentsMargins(0, 2, 0, 0)
        source_bar.setSpacing(4)

        source_title = QLabel("VĂN BẢN GỐC")
        source_title.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")

        self.retranslate_btn = QPushButton("🔄 Dịch lại")
        self.retranslate_btn.setObjectName("SmallActionButton")
        self.retranslate_btn.setToolTip("Dịch lại ngay lập tức (Ctrl+Enter)")
        self.retranslate_btn.clicked.connect(self.trigger_manual_translation)

        self.clear_btn = QPushButton("✕ Xóa")
        self.clear_btn.setObjectName("SmallActionButton")
        self.clear_btn.setToolTip("Xóa trắng ô nhập liệu")
        self.clear_btn.clicked.connect(self.clear_source_text)

        source_bar.addWidget(source_title)
        source_bar.addStretch()
        source_bar.addWidget(self.retranslate_btn)
        source_bar.addWidget(self.clear_btn)
        card_layout.addLayout(source_bar)

        # --- Source Text (Editable input) ---
        self.source_edit = SourceTextEdit()
        self.source_edit.setObjectName("SourceText")
        self.source_edit.setReadOnly(False)
        self.source_edit.setAcceptRichText(False)
        self.source_edit.setMinimumHeight(48)
        self.source_edit.setMaximumHeight(75)
        self.source_edit.setPlaceholderText("Nhập hoặc sửa văn bản cần dịch (Ctrl+Enter)...")
        self.source_edit.submit_requested.connect(self.trigger_manual_translation)
        self.source_edit.escape_requested.connect(self.hide)
        self.source_edit.textChanged.connect(self._on_source_text_changed)
        card_layout.addWidget(self.source_edit)

        # --- Translated Text ---
        self.target_edit = QTextEdit()
        self.target_edit.setObjectName("TranslatedText")
        self.target_edit.setReadOnly(True)
        self.target_edit.setPlaceholderText("Đang dịch...")
        card_layout.addWidget(self.target_edit)

        # --- Footer ---
        footer = QHBoxLayout()
        footer.setSpacing(8)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #71717a; font-size: 11px;")

        self.copy_btn = QPushButton("📋 Sao chép")
        self.copy_btn.setObjectName("CopyButton")
        self.copy_btn.clicked.connect(self.copy_translation)

        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.copy_btn)
        card_layout.addLayout(footer)

        outer_layout.addWidget(self.card)

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(shadow)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_btn.setProperty("pinned", "true" if self.is_pinned else "false")
        self.pin_btn.style().unpolish(self.pin_btn)
        self.pin_btn.style().polish(self.pin_btn)
        self.pin_btn.setToolTip("Bỏ ghim" if self.is_pinned else "Ghim cửa sổ")

    def copy_translation(self):
        text = self.target_edit.toPlainText().strip()
        if text:
            try:
                pyperclip.copy(text)
                self.copy_btn.setText("✓ Đã chép!")
                QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Sao chép"))
            except Exception as e:
                print(f"[Popup] Copy error: {e}")

    def position_smartly(self, target_pos: QPoint = None):
        """Position the popup near cursor or target point, avoiding screen overflow"""
        if not target_pos:
            target_pos = QCursor.pos()

        # Get screen containing target position
        screen = QGuiApplication.screenAt(target_pos) or QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        w = self.width()
        h = self.height()
        offset_x = 15
        offset_y = 15

        x = target_pos.x() + offset_x
        y = target_pos.y() + offset_y

        # Avoid right overflow
        if x + w > screen_geo.right():
            x = target_pos.x() - w - 10

        # Avoid bottom overflow
        if y + h > screen_geo.bottom():
            y = target_pos.y() - h - 10

        # Boundary checks
        x = max(screen_geo.left() + 10, min(x, screen_geo.right() - w - 10))
        y = max(screen_geo.top() + 10, min(y, screen_geo.bottom() - h - 10))

        self.move(x, y)

    def _on_source_text_changed(self):
        """Xử lý khi người dùng chỉnh sửa văn bản trong ô input"""
        if self._is_programmatic_change:
            return

        text = self.source_edit.toPlainText().strip()
        if not text:
            self.status_label.setText("0 ký tự")
            self._debounce_timer.stop()
            return

        self.status_label.setText(f"{len(text)} ký tự | Đang gõ...")
        self._debounce_timer.start(600)

    def _on_source_text_debounced(self):
        """Kích hoạt dịch tự động sau khi người dùng ngừng gõ 600ms"""
        text = self.source_edit.toPlainText().strip()
        if not text:
            self.target_edit.setPlainText("Nhập nội dung vào ô trên để dịch...")
            return
        if text == self._last_translated_text:
            return
        self._trigger_translation(text)

    def trigger_manual_translation(self):
        """Kích hoạt dịch thủ công ngay lập tức khi bấm nút Dịch lại hoặc phím tắt Ctrl+Enter"""
        self._debounce_timer.stop()
        text = self.source_edit.toPlainText().strip()
        if not text:
            self.target_edit.setPlainText("Vui lòng nhập nội dung cần dịch vào ô trên.")
            self.source_edit.setFocus()
            return
        self._trigger_translation(text)

    def clear_source_text(self):
        """Xóa nội dung ô input để nhập mới"""
        self._debounce_timer.stop()
        self._is_programmatic_change = True
        self.source_edit.setPlainText("")
        self._is_programmatic_change = False
        self._last_translated_text = ""
        self.target_edit.setPlainText("Đã xóa nội dung. Nhập văn bản mới để dịch...")
        self.status_label.setText("0 ký tự")
        self.lang_badge.setText("NHẬP TAY")
        self.source_edit.setFocus()

    def _trigger_translation(self, text: str):
        """Bắt đầu tác vụ dịch ngầm"""
        self._last_translated_text = text
        self.target_edit.setPlainText("⏳ Đang dịch...")
        self.lang_badge.setText("AUTO ➔ VI")
        self.status_label.setText(f"{len(text)} ký tự - Đang dịch...")

        # Async translation (retain reference to prevent GC)
        self._active_translation_task = TranslationTask(text)
        self._active_translation_task.signals.finished.connect(self._on_translation_finished)
        self.thread_pool.start(self._active_translation_task)

    def show_empty_prompt(self, target_pos: QPoint = None):
        self._debounce_timer.stop()
        self._is_programmatic_change = True
        self.source_edit.setPlainText("")
        self._is_programmatic_change = False
        self._last_translated_text = ""

        self.target_edit.setPlainText(
            "Chưa phát hiện văn bản bôi đen.\n👉 Bạn có thể gõ trực tiếp vào ô trên (Ctrl+Enter để dịch)."
        )
        self.lang_badge.setText("NHẬP TAY")
        self.status_label.setText("Sẵn sàng nhập liệu")
        self.position_smartly(target_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        self.source_edit.setFocus()

    def show_translation_for_text(self, text: str, target_pos: QPoint = None):
        text = text.strip()
        if not text:
            self.show_empty_prompt(target_pos)
            return

        self._debounce_timer.stop()
        self._is_programmatic_change = True
        self.source_edit.setPlainText(text)
        self._is_programmatic_change = False

        self.position_smartly(target_pos)
        self.show()
        self.raise_()
        self.activateWindow()

        self._trigger_translation(text)

    def _on_translation_finished(self, result: TranslationResult):
        current_text = self.source_edit.toPlainText().strip()
        # Nếu nội dung trong ô input đã đổi khác với kết quả vừa xong, bỏ qua để tránh ghi đè kết quả cũ
        if result.original != current_text:
            return

        if result.success:
            self.target_edit.setPlainText(result.translated)
            self.lang_badge.setText(f"{result.source_lang} ➔ {result.target_lang}")
            self.status_label.setText(f"{len(current_text)} ký tự - Đã dịch")
        else:
            self.target_edit.setPlainText(result.error_message or "Dịch không thành công")
            self.lang_badge.setText("LỖI")
            self.status_label.setText("Lỗi dịch thuật")

    # Drag window support
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # Auto close on focus loss (if not pinned)
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.ActivationChange:
            if not self.isActiveWindow() and not self.is_pinned:
                if config.get("auto_close_on_focus_loss", True):
                    # Slight delay so clicks on tray or other actions don't race
                    QTimer.singleShot(150, self._check_and_hide_if_inactive)

    def _check_and_hide_if_inactive(self):
        if not self.isActiveWindow() and not self.is_pinned:
            self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)
