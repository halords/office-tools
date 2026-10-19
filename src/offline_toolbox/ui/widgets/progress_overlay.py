"""Translucent progress overlay widget for long-running background tasks."""

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Property,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ProgressOverlay(QWidget):
    """Semi-transparent overlay that covers its parent widget with a spinner and status text."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setVisible(False)

        self._message: str = "Processing…"
        self._progress: float = -1.0  # -1 means indeterminate
        self._spin_angle: int = 0

        # Spinner animation timer
        self._spin_timer = QTimer(self)
        self._spin_timer.setInterval(30)
        self._spin_timer.timeout.connect(self._tick_spinner)

        # Fade-in animation
        self._opacity: float = 0.0
        self._fade_anim = QPropertyAnimation(self, b"overlayOpacity", self)
        self._fade_anim.setDuration(200)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ── Qt property for opacity animation ──
    def _get_opacity(self) -> float:
        return self._opacity

    def _set_opacity(self, val: float):
        self._opacity = val
        self.update()

    overlayOpacity = Property(float, _get_opacity, _set_opacity)

    # ── Public API ──
    def show_progress(self, message: str = "Processing…"):
        """Show the overlay with an indeterminate spinner."""
        self._message = message
        self._progress = -1.0
        self._spin_angle = 0
        self.resize(self.parentWidget().size())
        self.raise_()
        self.setVisible(True)
        self._spin_timer.start()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def update_progress(self, progress: float, message: str = ""):
        """Update determinate progress (0.0 → 1.0) and optional message."""
        self._progress = max(0.0, min(1.0, progress))
        if message:
            self._message = message
        self.update()

    def hide_progress(self):
        """Fade out and hide the overlay."""
        self._spin_timer.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_done)
        self._fade_anim.start()

    def _on_fade_out_done(self):
        self.setVisible(False)
        try:
            self._fade_anim.finished.disconnect(self._on_fade_out_done)
        except RuntimeError:
            pass

    # ── Internal ──
    def _tick_spinner(self):
        self._spin_angle = (self._spin_angle + 6) % 360
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def paintEvent(self, event):
        if self._opacity <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background scrim
        scrim = QColor(0, 0, 0, int(140 * self._opacity))
        painter.fillRect(self.rect(), scrim)

        cx = self.width() // 2
        cy = self.height() // 2

        # Card background
        card_w, card_h = 260, 160
        card_rect = QRect(cx - card_w // 2, cy - card_h // 2, card_w, card_h)
        card_color = QColor(30, 30, 40, int(230 * self._opacity))
        painter.setBrush(card_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(card_rect, 16, 16)

        # Spinner arc
        spinner_size = 40
        spinner_rect = QRect(cx - spinner_size // 2, cy - 46, spinner_size, spinner_size)
        pen = QPen(QColor(100, 180, 255, int(255 * self._opacity)))
        pen.setWidth(4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(spinner_rect, self._spin_angle * 16, 270 * 16)

        # Status text
        painter.setPen(QColor(220, 220, 230, int(255 * self._opacity)))
        font = QFont("Segoe UI", 11)
        painter.setFont(font)
        text_rect = QRect(card_rect.x() + 16, cy + 4, card_w - 32, 30)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._message)

        # Determinate progress bar
        if self._progress >= 0:
            bar_w = card_w - 48
            bar_h = 6
            bar_x = cx - bar_w // 2
            bar_y = cy + 36
            # Track
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(60, 60, 80, int(200 * self._opacity)))
            painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)
            # Fill
            fill_w = max(4, int(bar_w * self._progress))
            painter.setBrush(QColor(100, 180, 255, int(255 * self._opacity)))
            painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        painter.end()
