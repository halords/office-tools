"""Interactive on-canvas overlay items for text and images with enhanced UX."""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QFontDatabase,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QColorDialog,
    QFontDialog,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QInputDialog,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)


class ResizableImageOverlayItem(QGraphicsObject):
    """
    Interactive image overlay with 4 corner resize handles, drag move, aspect ratio lock/toggle, and opacity.
    """

    deleted = Signal(object)
    HANDLE_SIZE = 14.0  # Generous handle size for easy grabbing

    def __init__(self, image_path: Path, page_index: int, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.page_index = page_index
        self._pixmap = QPixmap(str(image_path))
        self._width = float(min(220.0, max(80.0, float(self._pixmap.width()))))
        # Preserve original aspect ratio
        aspect = float(self._pixmap.height()) / max(1.0, float(self._pixmap.width()))
        self._height = self._width * aspect

        self._opacity = 1.0
        self._active_handle: Optional[str] = None
        self._resize_start_pos = QPointF()
        self._resize_start_geometry = (0.0, 0.0, self._width, self._height)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(100)

    def boundingRect(self) -> QRectF:
        pad = self.HANDLE_SIZE
        return QRectF(-pad, -pad, self._width + 2 * pad, self._height + 2 * pad)

    def set_overlay_opacity(self, opacity: float):
        self._opacity = max(0.1, min(1.0, opacity))
        self.setOpacity(self._opacity)
        self.update()

    def get_overlay_opacity(self) -> float:
        return self._opacity

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Draw Image
        target_rect = QRectF(0, 0, self._width, self._height)
        painter.drawPixmap(target_rect.toRect(), self._pixmap)

        # Selection outline and corner resize handles
        if self.isSelected():
            # Glowing dashed frame
            border_pen = QPen(QColor("#0284C7"), 2.0, Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(target_rect)

            # Draw 4 handles (TL, TR, BL, BR)
            handles = self._get_handle_rects()
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(QBrush(QColor("#0284C7")))
            for r in handles.values():
                painter.drawRoundedRect(r, 2.0, 2.0)

    def _get_handle_rects(self):
        hs = self.HANDLE_SIZE
        return {
            "tl": QRectF(-hs / 2, -hs / 2, hs, hs),
            "tr": QRectF(self._width - hs / 2, -hs / 2, hs, hs),
            "bl": QRectF(-hs / 2, self._height - hs / 2, hs, hs),
            "br": QRectF(self._width - hs / 2, self._height - hs / 2, hs, hs),
        }

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        for name, rect in self._get_handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def hoverMoveEvent(self, event):
        if self.isSelected():
            handle = self._get_handle_at(event.pos())
            if handle in ("tl", "br"):
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            elif handle in ("tr", "bl"):
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            handle = self._get_handle_at(event.pos())
            if handle:
                self._active_handle = handle
                self._resize_start_pos = event.scenePos()
                self._resize_start_geometry = (self.pos().x(), self.pos().y(), self._width, self._height)
                event.accept()
                return
        self._active_handle = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle:
            delta = event.scenePos() - self._resize_start_pos
            orig_x, orig_y, orig_w, orig_h = self._resize_start_geometry
            aspect = float(self._pixmap.height()) / max(1.0, float(self._pixmap.width()))

            if self._active_handle == "br":
                new_w = max(30.0, orig_w + delta.x())
                new_h = new_w * aspect
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.update()
            elif self._active_handle == "tr":
                new_w = max(30.0, orig_w + delta.x())
                new_h = new_w * aspect
                diff_h = new_h - orig_h
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x, orig_y - diff_h)
                self.update()
            elif self._active_handle == "bl":
                new_w = max(30.0, orig_w - delta.x())
                new_h = new_w * aspect
                diff_w = new_w - orig_w
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x - diff_w, orig_y)
                self.update()
            elif self._active_handle == "tl":
                new_w = max(30.0, orig_w - delta.x())
                new_h = new_w * aspect
                diff_w = new_w - orig_w
                diff_h = new_h - orig_h
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x - diff_w, orig_y - diff_h)
                self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleted.emit(self)
            event.accept()
        else:
            super().keyPressEvent(event)

    def update_image_source(self, new_path: Path):
        """Update the displayed image source with a newly processed image (e.g. signature transparent PNG)."""
        self.image_path = new_path
        self._pixmap = QPixmap(str(new_path))
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #1E293B; color: #F8FAFC; border: 1px solid #475569; padding: 4px; } QMenu::item:selected { background-color: #0284C7; }")
        
        act_clean = menu.addAction("🖋️ Extract Signature / Remove White Background (Curves Ctrl+M)…")
        act_opacity = menu.addAction("💧 Set Opacity / Transparency…")
        menu.addSeparator()
        act_del = menu.addAction("🗑️ Delete Image")

        action = menu.exec(event.screenPos())
        if action == act_clean:
            from offline_toolbox.ui.pdf.signature_dialog import SignatureCleanDialog
            dlg = SignatureCleanDialog(self.image_path)
            if dlg.exec():
                cleaned_path = dlg.get_cleaned_image_path()
                if cleaned_path and cleaned_path.exists():
                    self.update_image_source(cleaned_path)
        elif action == act_opacity:
            val, ok = QInputDialog.getInt(
                None, "Image Opacity", "Opacity % (10 - 100):", int(self._opacity * 100), 10, 100, 5
            )
            if ok:
                self.set_overlay_opacity(float(val) / 100.0)
        elif action == act_del:
            self.deleted.emit(self)


class EditableTextOverlayItem(QGraphicsTextItem):
    """
    Interactive draggable text overlay with dedicated top drag handle, OS font picker,
    color picker, bold, italic, and underline styling.
    """

    deleted = Signal(object)
    HANDLE_HEIGHT = 18.0

    def __init__(self, text: str, page_index: int, parent=None):
        super().__init__(text, parent)
        self.page_index = page_index
        self._font_family = "Arial"
        self._font_size = 14.0
        self._text_color = QColor("#000000")
        self._is_bold = False
        self._is_italic = False
        self._is_underline = False

        self._apply_font()
        self.setDefaultTextColor(self._text_color)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
            | QGraphicsItem.GraphicsItemFlag.ItemIsFocusable
        )
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setZValue(101)

    def _apply_font(self):
        f = QFont(self._font_family, int(self._font_size))
        f.setBold(self._is_bold)
        f.setItalic(self._is_italic)
        f.setUnderline(self._is_underline)
        self.setFont(f)
        self.update()

    def set_font_family(self, family: str):
        self._font_family = family
        self._apply_font()

    def get_font_family(self) -> str:
        return self._font_family

    def set_font_size(self, size: float):
        self._font_size = size
        self._apply_font()

    def get_font_size(self) -> float:
        return self._font_size

    def set_text_color(self, color: QColor):
        self._text_color = color
        self.setDefaultTextColor(color)
        self.update()

    def get_text_color(self) -> QColor:
        return self._text_color

    def set_bold(self, bold: bool):
        self._is_bold = bold
        self._apply_font()

    def is_bold(self) -> bool:
        return self._is_bold

    def set_italic(self, italic: bool):
        self._is_italic = italic
        self._apply_font()

    def is_italic(self) -> bool:
        return self._is_italic

    def set_underline(self, underline: bool):
        self._is_underline = underline
        self._apply_font()

    def is_underline(self) -> bool:
        return self._is_underline

    def boundingRect(self) -> QRectF:
        br = super().boundingRect()
        # Extend top by HANDLE_HEIGHT for the drag grip bar
        return QRectF(br.x(), br.y() - self.HANDLE_HEIGHT, br.width(), br.height() + self.HANDLE_HEIGHT)

    def _get_close_btn_rect(self) -> QRectF:
        br = super().boundingRect()
        sz = self.HANDLE_HEIGHT - 2.0
        return QRectF(br.right() - sz - 2.0, br.y() - self.HANDLE_HEIGHT + 1.0, sz, sz)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        br = super().boundingRect()
        handle_rect = QRectF(br.x(), br.y() - self.HANDLE_HEIGHT, br.width(), self.HANDLE_HEIGHT)

        if self.isSelected() or self.hasFocus():
            # Draw top Drag Grip Bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#0284C7")))
            painter.drawRoundedRect(handle_rect, 3.0, 3.0)

            # Grip icon text
            painter.setPen(QPen(QColor("#FFFFFF")))
            grip_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(grip_font)
            painter.drawText(handle_rect, Qt.AlignmentFlag.AlignCenter, "⋮⋮ DRAG")

            # Red ✕ Close / Delete button on the top right of the handle
            close_r = self._get_close_btn_rect()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#EF4444")))  # Bright red
            painter.drawRoundedRect(close_r, 2.0, 2.0)
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            close_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(close_font)
            painter.drawText(close_r, Qt.AlignmentFlag.AlignCenter, "✕")

            # Selection dashed box around text
            painter.setPen(QPen(QColor("#0284C7"), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(QBrush(QColor(2, 132, 199, 15)))
            painter.drawRect(br)

        super().paint(painter, option, widget)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (self.isSelected() or self.hasFocus()):
            if self._get_close_btn_rect().contains(event.pos()):
                self.deleted.emit(self)
                event.accept()
                return
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #1E293B; color: #F8FAFC; border: 1px solid #475569; padding: 4px; } QMenu::item:selected { background-color: #0284C7; }")

        act_font = menu.addAction("🔤 Font & Style (System OS Fonts)…")
        act_color = menu.addAction("🎨 Text Color…")
        menu.addSeparator()
        act_bold = menu.addAction("𝐁 Bold")
        act_bold.setCheckable(True)
        act_bold.setChecked(self.is_bold())

        act_italic = menu.addAction("𝐼 Italic")
        act_italic.setCheckable(True)
        act_italic.setChecked(self.is_italic())

        act_underline = menu.addAction("U̲ Underline")
        act_underline.setCheckable(True)
        act_underline.setChecked(self.is_underline())

        menu.addSeparator()
        act_del = menu.addAction("🗑️ Delete Text Box")

        action = menu.exec(event.screenPos())
        if action == act_font:
            # Native OS Font Dialog displaying all installed fonts
            curr_f = self.font()
            ok, selected_font = QFontDialog.getFont(curr_f, None, "Select Font from System")
            if ok:
                self._font_family = selected_font.family()
                self._font_size = float(selected_font.pointSize() if selected_font.pointSize() > 0 else 12)
                self._is_bold = selected_font.bold()
                self._is_italic = selected_font.italic()
                self._is_underline = selected_font.underline()
                self._apply_font()

        elif action == act_color:
            c = QColorDialog.getColor(self._text_color, None, "Select Text Color")
            if c.isValid():
                self.set_text_color(c)

        elif action == act_bold:
            self.set_bold(not self.is_bold())

        elif action == act_italic:
            self.set_italic(not self.is_italic())

        elif action == act_underline:
            self.set_underline(not self.is_underline())

        elif action == act_del:
            self.deleted.emit(self)


import uuid

class AcroformFieldOverlayItem(QGraphicsObject):
    """
    Interactive draggable/resizable acroform field overlay.
    """
    deleted = Signal(object)
    HANDLE_SIZE = 14.0

    def __init__(self, field_type: int, page_index: int, parent=None):
        super().__init__(parent)
        self.field_type = field_type
        self.page_index = page_index
        self.field_name = f"Field_{uuid.uuid4().hex[:6]}"
        
        import fitz
        self._width = 150.0 if field_type == fitz.PDF_WIDGET_TYPE_TEXT else 20.0
        self._height = 24.0 if field_type == fitz.PDF_WIDGET_TYPE_TEXT else 20.0

        self._active_handle = None
        self._resize_start_pos = QPointF()
        self._resize_start_geometry = (0.0, 0.0, self._width, self._height)

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(105)

    def boundingRect(self) -> QRectF:
        pad = self.HANDLE_SIZE
        return QRectF(-pad, -pad, self._width + 2 * pad, self._height + 2 * pad)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        import fitz
        target_rect = QRectF(0, 0, self._width, self._height)
        
        painter.setPen(QPen(QColor("#10B981"), 2.0))
        painter.setBrush(QBrush(QColor(16, 185, 129, 30)))
        painter.drawRect(target_rect)
        
        painter.setPen(QPen(QColor("#047857")))
        f = QFont("Segoe UI", 8)
        painter.setFont(f)
        label = "Text Field" if self.field_type == fitz.PDF_WIDGET_TYPE_TEXT else "Checkbox"
        painter.drawText(target_rect, Qt.AlignmentFlag.AlignCenter, label)

        if self.isSelected():
            handles = self._get_handle_rects()
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(QBrush(QColor("#10B981")))
            for r in handles.values():
                painter.drawRoundedRect(r, 2.0, 2.0)

    def _get_handle_rects(self):
        hs = self.HANDLE_SIZE
        return {
            "tl": QRectF(-hs / 2, -hs / 2, hs, hs),
            "tr": QRectF(self._width - hs / 2, -hs / 2, hs, hs),
            "bl": QRectF(-hs / 2, self._height - hs / 2, hs, hs),
            "br": QRectF(self._width - hs / 2, self._height - hs / 2, hs, hs),
        }

    def _get_handle_at(self, pos: QPointF) -> Optional[str]:
        for name, rect in self._get_handle_rects().items():
            if rect.contains(pos):
                return name
        return None

    def hoverMoveEvent(self, event):
        if self.isSelected():
            handle = self._get_handle_at(event.pos())
            if handle in ("tl", "br"):
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
            elif handle in ("tr", "bl"):
                self.setCursor(QCursor(Qt.CursorShape.SizeBDiagCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.isSelected():
            handle = self._get_handle_at(event.pos())
            if handle:
                self._active_handle = handle
                self._resize_start_pos = event.scenePos()
                self._resize_start_geometry = (self.pos().x(), self.pos().y(), self._width, self._height)
                event.accept()
                return
        self._active_handle = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._active_handle:
            delta = event.scenePos() - self._resize_start_pos
            orig_x, orig_y, orig_w, orig_h = self._resize_start_geometry

            if self._active_handle == "br":
                new_w = max(20.0, orig_w + delta.x())
                new_h = max(20.0, orig_h + delta.y())
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.update()
            elif self._active_handle == "tr":
                new_w = max(20.0, orig_w + delta.x())
                new_h = max(20.0, orig_h - delta.y())
                diff_h = new_h - orig_h
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x, orig_y - diff_h)
                self.update()
            elif self._active_handle == "bl":
                new_w = max(20.0, orig_w - delta.x())
                new_h = max(20.0, orig_h + delta.y())
                diff_w = new_w - orig_w
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x - diff_w, orig_y)
                self.update()
            elif self._active_handle == "tl":
                new_w = max(20.0, orig_w - delta.x())
                new_h = max(20.0, orig_h - delta.y())
                diff_w = new_w - orig_w
                diff_h = new_h - orig_h
                self.prepareGeometryChange()
                self._width = new_w
                self._height = new_h
                self.setPos(orig_x - diff_w, orig_y - diff_h)
                self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._active_handle:
            self._active_handle = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.deleted.emit(self)
            event.accept()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #1E293B; color: #F8FAFC; border: 1px solid #475569; padding: 4px; } QMenu::item:selected { background-color: #0284C7; }")
        
        act_del = menu.addAction("🗑️ Delete Field")
        action = menu.exec(event.screenPos())
        if action == act_del:
            self.deleted.emit(self)
