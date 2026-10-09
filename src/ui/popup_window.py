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


class PopupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.is_pinned = False
        self._drag_pos = None

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
        self.resize(config.get("window_width", 380), config.get("window_height", 240))

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
        card_layout.setSpacing(8)

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

        # --- Source Text (Collapsible/compact) ---
        self.source_edit = QTextEdit()
        self.source_edit.setObjectName("SourceText")
        self.source_edit.setReadOnly(True)
        self.source_edit.setMaximumHeight(65)
        self.source_edit.setPlaceholderText("Văn bản gốc...")
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

    def show_empty_prompt(self, target_pos: QPoint = None):
        self.source_edit.setPlainText("")
        self.target_edit.setPlainText(
            "Chưa phát hiện văn bản nào được bôi đen.\n\n👉 Cách dùng: Hãy bôi đen một đoạn chữ bất kỳ rồi bấm Alt+D."
        )
        self.lang_badge.setText("CHƯA BÔI ĐEN")
        self.status_label.setText("Hướng dẫn")
        self.position_smartly(target_pos)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_translation_for_text(self, text: str, target_pos: QPoint = None):
        text = text.strip()
        if not text:
            self.show_empty_prompt(target_pos)
            return

        self.source_edit.setPlainText(text)
        self.target_edit.setPlainText("⏳ Đang dịch...")
        self.lang_badge.setText("AUTO ➔ VI")
        self.status_label.setText(f"{len(text)} ký tự")

        self.position_smartly(target_pos)
        self.show()
        self.raise_()
        self.activateWindow()

        # Async translation (retain reference to prevent GC)
        self._active_translation_task = TranslationTask(text)
        self._active_translation_task.signals.finished.connect(self._on_translation_finished)
        self.thread_pool.start(self._active_translation_task)

    def _on_translation_finished(self, result: TranslationResult):
        if result.success:
            self.target_edit.setPlainText(result.translated)
            self.lang_badge.setText(f"{result.source_lang} ➔ {result.target_lang}")
        else:
            self.target_edit.setPlainText(result.error_message or "Dịch không thành công")
            self.lang_badge.setText("LỖI")

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
