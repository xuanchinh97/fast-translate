from PySide6.QtCore import Qt, QPoint, QRect, Signal, QSize
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QCursor, QGuiApplication, QFont, QImage
from PySide6.QtWidgets import QWidget
from PIL import Image
import io


class SnippingWidget(QWidget):
    # Emits (PIL.Image, QPoint target_location)
    snippet_captured = Signal(object, QPoint)
    snippet_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False
        self._background_pixmap = None

    def start_snipping(self):
        """Prepare screenshot background and display fullscreen across all monitors"""
        # Calculate bounding box of all screens
        screens = QGuiApplication.screens()
        if not screens:
            return

        combined_geo = QRect()
        for s in screens:
            combined_geo = combined_geo.united(s.geometry())

        # Grab entire desktop
        primary_screen = QGuiApplication.primaryScreen()
        self._background_pixmap = primary_screen.grabWindow(
            0,
            combined_geo.x(),
            combined_geo.y(),
            combined_geo.width(),
            combined_geo.height()
        )

        self.setGeometry(combined_geo)
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False

        self.show()
        self.raise_()
        self.activateWindow()

    def get_selection_rect(self) -> QRect:
        if not self._start_pos or not self._current_pos:
            return QRect()
        return QRect(self._start_pos, self._current_pos).normalized()

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.get_selection_rect()

        # 1. Draw base desktop snapshot
        if self._background_pixmap:
            painter.drawPixmap(0, 0, self._background_pixmap)

        # 2. Draw darkened overlay
        overlay_color = QColor(0, 0, 0, 110)
        painter.fillRect(self.rect(), overlay_color)

        # 3. Draw clear cutout if user is selecting
        if not rect.isEmpty() and self._background_pixmap:
            # Clear darkness from selection rect by redrawing the background portion
            painter.drawPixmap(rect, self._background_pixmap, rect)

            # Draw vibrant blue border
            pen = QPen(QColor(59, 130, 246), 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)

            # Draw size badge
            size_text = f"{rect.width()} × {rect.height()}"
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.setBrush(QColor(20, 20, 25, 200))

            badge_w, badge_h = 75, 20
            badge_x = rect.x()
            badge_y = rect.y() - badge_h - 4
            if badge_y < 10:
                badge_y = rect.y() + 6

            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)
            painter.drawText(QRect(badge_x, badge_y, badge_w, badge_h), Qt.AlignmentFlag.AlignCenter, size_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            rect = self.get_selection_rect()
            self.hide()

            if rect.width() > 10 and rect.height() > 10 and self._background_pixmap:
                # Crop pixmap
                cropped_pixmap = self._background_pixmap.copy(rect)
                qimage = cropped_pixmap.toImage().convertToFormat(cropped_pixmap.toImage().Format.Format_RGBA8888)
                
                # Direct raw buffer conversion (much faster than saving to PNG)
                width = qimage.width()
                height = qimage.height()
                raw_bytes = bytes(qimage.constBits())
                pil_img = Image.frombytes("RGBA", (width, height), raw_bytes)

                # Global position for popup placement (bottom-left or bottom-right of snip)
                global_target_pos = self.mapToGlobal(QPoint(rect.x(), rect.bottom()))
                self.snippet_captured.emit(pil_img, global_target_pos)
            else:
                self.snippet_cancelled.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.snippet_cancelled.emit()
        else:
            super().keyPressEvent(event)
