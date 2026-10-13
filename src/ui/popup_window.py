from PySide6.QtCore import Qt, QPoint, QRunnable, QThreadPool, QObject, Signal, QTimer
from PySide6.QtGui import QCursor, QGuiApplication, QColor, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGraphicsDropShadowEffect, QFrame, QSizePolicy, QMenu
)
import pyperclip
from src.config import config
from src.core.translator import translator, TranslationResult
from src.core.tts_engine import tts_engine
from src.ui.styles import DARK_THEME


class TranslationSignals(QObject):
    finished = Signal(TranslationResult)


class TranslationTask(QRunnable):
    def __init__(self, text: str, src: str = "auto", tgt: str = "vi"):
        super().__init__()
        self.text = text
        self.src = src
        self.tgt = tgt
        self.signals = TranslationSignals()

    def run(self):
        result = translator.translate(self.text, src=self.src, tgt=self.tgt)
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

        # Cặp ngôn ngữ hiện tại
        self.source_lang = config.get("source_lang", "auto")
        self.target_lang = config.get("target_lang", "vi")
        self._detected_src_lang = None

        # Debounce timer tự động dịch sau khi người dùng dừng gõ 600ms
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(600)
        self._debounce_timer.timeout.connect(self._on_source_text_debounced)

        self.init_window_flags()
        self.init_ui()
        self.thread_pool = QThreadPool.globalInstance()

        # Kết nối trạng thái phát âm TTS
        tts_engine.speaking_started.connect(self._on_speaking_started)
        tts_engine.speaking_finished.connect(self._on_speaking_finished)

    def init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.resize(config.get("window_width", 400), config.get("window_height", 275))

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

        # Nút đổi chiều ngôn ngữ (Swap)
        self.swap_lang_btn = QPushButton("⇄")
        self.swap_lang_btn.setObjectName("SwapButton")
        self.swap_lang_btn.setToolTip("Đổi chiều ngôn ngữ (Anh ⇄ Việt)")
        self.swap_lang_btn.clicked.connect(self.swap_language_direction)

        # Badge ngôn ngữ (có thể click để chọn danh sách ngôn ngữ)
        self.lang_badge = QPushButton("AUTO ➔ VI")
        self.lang_badge.setObjectName("LangBadgeBtn")
        self.lang_badge.setToolTip("Click để chọn cặp ngôn ngữ dịch")
        self.lang_badge.clicked.connect(self.show_language_menu)

        header.addWidget(self.title_label)
        header.addWidget(self.swap_lang_btn)
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

        # Nút phát âm văn bản gốc
        self.speak_source_btn = QPushButton("🔊 Đọc")
        self.speak_source_btn.setObjectName("SmallActionButton")
        self.speak_source_btn.setToolTip("Nghe phát âm văn bản gốc")
        self.speak_source_btn.clicked.connect(self.speak_source_text)

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
        source_bar.addWidget(self.speak_source_btn)
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
        footer.setSpacing(6)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #71717a; font-size: 11px;")

        # Nút phát âm bản dịch
        self.speak_target_btn = QPushButton("🔊 Đọc")
        self.speak_target_btn.setObjectName("SmallActionButton")
        self.speak_target_btn.setToolTip("Nghe phát âm bản dịch")
        self.speak_target_btn.clicked.connect(self.speak_target_text)

        self.copy_btn = QPushButton("📋 Sao chép")
        self.copy_btn.setObjectName("CopyButton")
        self.copy_btn.clicked.connect(self.copy_translation)

        footer.addWidget(self.status_label)
        footer.addStretch()
        footer.addWidget(self.speak_target_btn)
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
        tts_engine.stop()
        self._debounce_timer.stop()
        self._is_programmatic_change = True
        self.source_edit.setPlainText("")
        self._is_programmatic_change = False
        self._last_translated_text = ""
        self.target_edit.setPlainText("Đã xóa nội dung. Nhập văn bản mới để dịch...")
        self.status_label.setText("0 ký tự")
        self._update_lang_badge_display()
        self.source_edit.setFocus()

    def swap_language_direction(self):
        """Đổi chiều ngôn ngữ giữa Nguồn và Đích (ví dụ AUTO->VI <-> VI->EN)"""
        tts_engine.stop()
        if self.target_lang.lower() == "vi":
            self.source_lang = "vi"
            self.target_lang = "en"
        else:
            self.source_lang = "auto"
            self.target_lang = "vi"

        self._detected_src_lang = None
        self._update_lang_badge_display()

        # Hoán đổi nội dung 2 ô nếu đã có kết quả dịch
        src_text = self.source_edit.toPlainText().strip()
        tgt_text = self.target_edit.toPlainText().strip()

        if tgt_text and not tgt_text.startswith("⏳") and not tgt_text.startswith("Chưa") and not tgt_text.startswith("Đang") and not tgt_text.startswith("Đã"):
            self._is_programmatic_change = True
            self.source_edit.setPlainText(tgt_text)
            self._is_programmatic_change = False
            self._trigger_translation(tgt_text)
        elif src_text:
            self._trigger_translation(src_text)

    def show_language_menu(self):
        """Hiển thị menu chọn các cặp ngôn ngữ phổ biến"""
        menu = QMenu(self)
        actions = [
            ("🌐 Tự động ➔ Tiếng Việt (AUTO ➔ VI)", "auto", "vi"),
            ("🔄 Tiếng Việt ➔ Tiếng Anh (VI ➔ EN)", "vi", "en"),
            ("🇺🇸 Tiếng Anh ➔ Tiếng Việt (EN ➔ VI)", "en", "vi"),
            ("🇯🇵 Tự động ➔ Tiếng Nhật (AUTO ➔ JA)", "auto", "ja"),
            ("🇰🇷 Tự động ➔ Tiếng Hàn (AUTO ➔ KO)", "auto", "ko"),
            ("🇨🇳 Tự động ➔ Tiếng Trung (AUTO ➔ ZH-CN)", "auto", "zh-cn"),
            ("🇫🇷 Tự động ➔ Tiếng Pháp (AUTO ➔ FR)", "auto", "fr"),
        ]

        for label, src, tgt in actions:
            action = menu.addAction(label)
            action.triggered.connect(lambda checked=False, s=src, t=tgt: self.set_language_pair(s, t))

        menu.exec(self.lang_badge.mapToGlobal(QPoint(0, self.lang_badge.height() + 4)))

    def set_language_pair(self, src: str, tgt: str):
        """Đặt cặp ngôn ngữ dịch tường minh"""
        tts_engine.stop()
        self.source_lang = src
        self.target_lang = tgt
        self._detected_src_lang = src if src != "auto" else None
        self._update_lang_badge_display()

        src_text = self.source_edit.toPlainText().strip()
        if src_text:
            self._trigger_translation(src_text)

    def _update_lang_badge_display(self):
        src_disp = (self._detected_src_lang or self.source_lang).upper()
        tgt_disp = self.target_lang.upper()
        self.lang_badge.setText(f"{src_disp} ➔ {tgt_disp}")

    def speak_source_text(self):
        """Phát âm văn bản gốc"""
        text = self.source_edit.toPlainText().strip()
        if not text:
            return
        lang = self._detected_src_lang or self.source_lang
        if lang == "auto":
            lang = "en"
        tts_engine.speak(text, lang)

    def speak_target_text(self):
        """Phát âm bản dịch"""
        text = self.target_edit.toPlainText().strip()
        if not text or text.startswith("⏳") or text.startswith("Chưa") or text.startswith("Đang") or text.startswith("Đã"):
            return
        lang = self.target_lang or "vi"
        tts_engine.speak(text, lang)

    def _on_speaking_started(self):
        self.status_label.setText("🔊 Đang phát âm...")

    def _on_speaking_finished(self):
        current_len = len(self.source_edit.toPlainText().strip())
        self.status_label.setText(f"{current_len} ký tự - Đã dịch" if current_len else "")

    def _trigger_translation(self, text: str):
        """Bắt đầu tác vụ dịch ngầm"""
        self._last_translated_text = text
        self.target_edit.setPlainText("⏳ Đang dịch...")
        self._update_lang_badge_display()
        self.status_label.setText(f"{len(text)} ký tự - Đang dịch...")

        # Async translation (retain reference to prevent GC)
        self._active_translation_task = TranslationTask(text, src=self.source_lang, tgt=self.target_lang)
        self._active_translation_task.signals.finished.connect(self._on_translation_finished)
        self.thread_pool.start(self._active_translation_task)

    def show_empty_prompt(self, target_pos: QPoint = None):
        tts_engine.stop()
        self._debounce_timer.stop()
        self._is_programmatic_change = True
        self.source_edit.setPlainText("")
        self._is_programmatic_change = False
        self._last_translated_text = ""

        self.target_edit.setPlainText(
            "Chưa phát hiện văn bản bôi đen.\n👉 Bạn có thể gõ trực tiếp vào ô trên (Ctrl+Enter để dịch)."
        )
        self._update_lang_badge_display()
        self.status_label.setText("Sẵn sàng nhập liệu")
        self.position_smartly(target_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        self.source_edit.setFocus()

    def show_translation_for_text(self, text: str, target_pos: QPoint = None):
        tts_engine.stop()
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
        if result.original != current_text:
            return

        if result.success:
            self.target_edit.setPlainText(result.translated)
            self._detected_src_lang = result.source_lang.lower()
            self._update_lang_badge_display()
            self.status_label.setText(f"{len(current_text)} ký tự - Đã dịch")
        else:
            self.target_edit.setPlainText(result.error_message or "Dịch không thành công")
            self.lang_badge.setText("LỖI")
            self.status_label.setText("Lỗi dịch thuật")

    def hide(self):
        tts_engine.stop()
        super().hide()

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
