"""Interactive Image Editor Workspace: Crop, Fit-to-Width, Slide/Position, Photo Presets (2x2, 4R, Passport), and Clean Signature."""

from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal, QThread
from PySide6.QtGui import QBrush, QColor, QCursor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.images.presets import PHOTO_PRESETS, fit_image_to_preset
from offline_toolbox.images.service import ImageService
from offline_toolbox.images.signature import clean_signature_and_remove_white


class CropOverlayView(QGraphicsView):
    """
    Interactive canvas displaying the loaded image with a movable/slidable crop window.
    Allows fitting to width, sliding vertically/horizontally across long images, and zooming.
    """

    position_changed = Signal(float, float)  # norm_x (0-1), norm_y (0-1)
    scale_changed = Signal(float)  # crop_scale (0.5 - 3.0)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor("#0F172A")))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._crop_frame: Optional[QGraphicsRectItem] = None

        self._orig_w: int = 0
        self._orig_h: int = 0
        self._target_w: int = 600
        self._target_h: int = 600
        self._norm_x: float = 0.5
        self._norm_y: float = 0.5
        self._crop_scale: float = 1.0  # 1.0 = base fit, 1.5x/2.0x = zoom in to frame face/head for 2x2
        self._crop_active: bool = False
        self._nametag_active: bool = False
        self._nametag_h_pct: float = 0.18

        self._banner_frame: Optional[QGraphicsRectItem] = None
        self._banner_text_item: Optional[QGraphicsSimpleTextItem] = None
        self._banner_name_pixmap_item: Optional[QGraphicsPixmapItem] = None
        self._banner_sig_pixmap_item: Optional[QGraphicsPixmapItem] = None

        # Preview properties for live banner
        self._preview_name_text: str = ""
        self._preview_name_pil: Optional[Image.Image] = None
        self._preview_name_scale: float = 1.0
        self._preview_sig_pil: Optional[Image.Image] = None
        self._preview_sig_scale: float = 1.0
        self._preview_sig_pos_y: float = 0.0

        self._is_dragging: bool = False
        self._last_mouse_pos = QPointF()

    def load_image(self, pixmap: QPixmap):
        self._scene.clear()
        self._crop_frame = None
        self._banner_frame = None
        self._banner_text_item = None
        self._banner_name_pixmap_item = None
        self._banner_sig_pixmap_item = None
        self._orig_w = pixmap.width()
        self._orig_h = pixmap.height()

        self._pixmap_item = self._scene.addPixmap(pixmap)
        self._pixmap_item.setZValue(1)

        self.setSceneRect(0, 0, self._orig_w, self._orig_h)
        self._update_crop_box()
        self.fit_in_view()

    def clear(self):
        self._scene.clear()
        self._pixmap_item = None
        self._crop_frame = None
        self._banner_frame = None
        self._banner_text_item = None
        self._banner_name_pixmap_item = None
        self._banner_sig_pixmap_item = None
        self._orig_w = 0
        self._orig_h = 0
        self.setSceneRect(0, 0, 0, 0)
        self.resetTransform()

    def fit_in_view(self):
        if self._orig_w > 0 and self._orig_h > 0:
            self.fitInView(0, 0, self._orig_w, self._orig_h, Qt.AspectRatioMode.KeepAspectRatio)

    def fit_to_width(self):
        """Fit image width strictly to viewport width so vertical length can be slid."""
        if self._orig_w > 0 and self.viewport().width() > 0:
            scale = float(self.viewport().width() - 20) / float(self._orig_w)
            self.resetTransform()
            self.scale(scale, scale)

    def set_target_aspect(self, target_w: int, target_h: int, active: bool = True):
        self._target_w = target_w
        self._target_h = target_h
        self._crop_active = active
        self._update_crop_box()

    def set_norm_position(self, norm_x: float, norm_y: float):
        self._norm_x = max(0.0, min(1.0, norm_x))
        self._norm_y = max(0.0, min(1.0, norm_y))
        self._update_crop_box()

    def calculate_scale_for_fit_width(self) -> float:
        """Calculates the crop_scale required so the crop box width exactly equals the photo's full width."""
        if self._orig_w == 0 or self._orig_h == 0 or self._target_w == 0 or self._target_h == 0:
            return 1.0

        if self._nametag_active:
            banner_h = max(24, int(round(self._target_h * max(0.10, min(0.35, self._nametag_h_pct)))))
            effective_h = float(self._target_h - banner_h)
        else:
            effective_h = float(self._target_h)
        effective_w = float(self._target_w)

        target_aspect = effective_w / max(1.0, effective_h)
        image_aspect = self._orig_w / float(self._orig_h)

        if image_aspect > target_aspect:
            base_box_h = float(self._orig_h)
            base_box_w = base_box_h * target_aspect
        else:
            base_box_w = float(self._orig_w)

        # For box_w to equal self._orig_w: base_box_w / scale = self._orig_w => scale = base_box_w / self._orig_w
        scale = base_box_w / float(self._orig_w)
        return max(0.3, min(4.0, scale))

    def set_crop_scale(self, scale: float):
        self._crop_scale = max(0.3, min(4.0, scale))
        self._update_crop_box()

    def get_crop_scale(self) -> float:
        return self._crop_scale

    def set_nametag_overlay(self, active: bool, height_pct: float = 0.18):
        self._nametag_active = active
        self._nametag_h_pct = height_pct
        self._update_crop_box()

    def update_nametag_content(
        self,
        name_text: str = "",
        name_pil: Optional[Image.Image] = None,
        name_scale: float = 1.0,
        sig_pil: Optional[Image.Image] = None,
        sig_scale: float = 1.0,
        sig_pos_y: float = 0.0,
    ):
        self._preview_name_text = name_text
        self._preview_name_pil = name_pil
        self._preview_name_scale = name_scale
        self._preview_sig_pil = sig_pil
        self._preview_sig_scale = sig_scale
        self._preview_sig_pos_y = sig_pos_y
        self._update_crop_box()

    def get_exact_crop_rect(self) -> Optional[Tuple[int, int, int, int]]:
        """Returns exact (left, top, right, bottom) pixel coordinates of the visual crop box."""
        if not self._crop_frame or self._orig_w == 0 or self._orig_h == 0:
            return None
        r = self._crop_frame.rect()
        left = int(round(r.left()))
        top = int(round(r.top()))
        right = int(round(r.right()))
        bottom = int(round(r.bottom()))
        return (left, top, right, bottom)

    def _clear_banner_subitems(self):
        if self._banner_text_item:
            self._scene.removeItem(self._banner_text_item)
            self._banner_text_item = None
        if self._banner_name_pixmap_item:
            self._scene.removeItem(self._banner_name_pixmap_item)
            self._banner_name_pixmap_item = None
        if self._banner_sig_pixmap_item:
            self._scene.removeItem(self._banner_sig_pixmap_item)
            self._banner_sig_pixmap_item = None

    def _update_crop_box(self):
        if not self._pixmap_item or not self._crop_active or self._orig_w == 0 or self._orig_h == 0:
            if self._crop_frame:
                self._scene.removeItem(self._crop_frame)
                self._crop_frame = None
            if self._banner_frame:
                self._scene.removeItem(self._banner_frame)
                self._banner_frame = None
            self._clear_banner_subitems()
            return

        # Target dimensions for the photo viewport (excluding banner if nametag active)
        if self._nametag_active:
            banner_h = max(24, int(round(self._target_h * max(0.10, min(0.35, self._nametag_h_pct)))))
            effective_h = float(self._target_h - banner_h)
        else:
            banner_h = 0
            effective_h = float(self._target_h)
        effective_w = float(self._target_w)

        target_aspect = effective_w / max(1.0, effective_h)
        image_aspect = self._orig_w / float(self._orig_h)

        if image_aspect > target_aspect:
            base_box_h = float(self._orig_h)
            base_box_w = base_box_h * target_aspect
        else:
            base_box_w = float(self._orig_w)
            base_box_h = base_box_w / target_aspect

        # Apply crop_scale (zoom out = larger crop window)
        safe_scale = max(0.01, min(5.0, self._crop_scale))
        box_w = base_box_w / safe_scale
        box_h = base_box_h / safe_scale

        slide_range_x = float(self._orig_w) - box_w
        slide_range_y = float(self._orig_h) - box_h

        x = slide_range_x * self._norm_x
        y = slide_range_y * self._norm_y

        if not self._crop_frame:
            self._crop_frame = self._scene.addRect(
                QRectF(x, y, box_w, box_h),
                QPen(QColor("#38BDF8"), 2.5, Qt.PenStyle.DashLine),
                QBrush(QColor(56, 189, 248, 25)),
            )
            self._crop_frame.setZValue(10)
        else:
            self._crop_frame.setRect(QRectF(x, y, box_w, box_h))

        # Show dedicated white space banner indicator with LIVE text and signature preview
        if self._nametag_active and banner_h > 0:
            banner_disp_h = box_h * (banner_h / effective_h)
            banner_y = y + box_h
            if not self._banner_frame:
                self._banner_frame = self._scene.addRect(
                    QRectF(x, banner_y, box_w, banner_disp_h),
                    QPen(QColor("#0284C7"), 2.0, Qt.PenStyle.SolidLine),
                    QBrush(QColor(255, 255, 255, 250)),
                )
                self._banner_frame.setZValue(11)
            else:
                self._banner_frame.setRect(QRectF(x, banner_y, box_w, banner_disp_h))

            # 1. Live Name Preview (Handwritten Pixmap OR Scalable Text)
            name_rendered_h = 0.0
            if self._preview_name_pil:
                if self._banner_text_item:
                    self._scene.removeItem(self._banner_text_item)
                    self._banner_text_item = None

                rgba = self._preview_name_pil.convert("RGBA")
                data = rgba.tobytes("raw", "RGBA")
                qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
                n_pix = QPixmap.fromImage(qimg)

                target_nw = box_w * 0.85 * max(0.4, min(1.8, self._preview_name_scale))
                target_nh = banner_disp_h * 0.38 * max(0.4, min(1.8, self._preview_name_scale))
                n_ratio = min(target_nw / float(rgba.width), target_nh / float(rgba.height))
                final_nw = max(1.0, float(rgba.width) * n_ratio)
                final_nh = max(1.0, float(rgba.height) * n_ratio)

                scaled_npix = n_pix.scaled(
                    int(round(final_nw)), int(round(final_nh)),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if not self._banner_name_pixmap_item:
                    self._banner_name_pixmap_item = self._scene.addPixmap(scaled_npix)
                    self._banner_name_pixmap_item.setZValue(12)
                else:
                    self._banner_name_pixmap_item.setPixmap(scaled_npix)

                nx = x + (box_w - scaled_npix.width()) / 2.0
                ny = banner_y + banner_disp_h - scaled_npix.height() - max(2.0, banner_disp_h * 0.08)
                self._banner_name_pixmap_item.setPos(nx, ny)
                name_rendered_h = float(scaled_npix.height())
            elif self._preview_name_text.strip():
                if self._banner_name_pixmap_item:
                    self._scene.removeItem(self._banner_name_pixmap_item)
                    self._banner_name_pixmap_item = None

                txt = self._preview_name_text.strip().upper()
                if not self._banner_text_item:
                    self._banner_text_item = self._scene.addSimpleText(txt)
                    self._banner_text_item.setZValue(12)
                    self._banner_text_item.setBrush(QBrush(QColor(0, 0, 0)))
                else:
                    self._banner_text_item.setText(txt)

                base_font_pt = max(6.0, banner_disp_h * 0.22 * max(0.4, min(2.0, self._preview_name_scale)))
                font = QFont("Arial", int(round(base_font_pt)), QFont.Weight.Bold)
                self._banner_text_item.setFont(font)

                t_rect = self._banner_text_item.boundingRect()
                tx = x + (box_w - t_rect.width()) / 2.0
                ty = banner_y + banner_disp_h - t_rect.height() - max(2.0, banner_disp_h * 0.08)
                self._banner_text_item.setPos(tx, ty)
                name_rendered_h = float(t_rect.height())
            else:
                if self._banner_text_item:
                    self._scene.removeItem(self._banner_text_item)
                    self._banner_text_item = None
                if self._banner_name_pixmap_item:
                    self._scene.removeItem(self._banner_name_pixmap_item)
                    self._banner_name_pixmap_item = None

            # 2. Live Signature Preview
            if self._preview_sig_pil:
                sig_rgba = self._preview_sig_pil.convert("RGBA")
                sig_data = sig_rgba.tobytes("raw", "RGBA")
                sig_qimg = QImage(sig_data, sig_rgba.width, sig_rgba.height, QImage.Format.Format_RGBA8888)
                s_pix = QPixmap.fromImage(sig_qimg)

                has_name = bool(self._preview_name_text.strip() or self._preview_name_pil)
                avail_w = box_w * 0.85 * max(0.3, min(2.5, self._preview_sig_scale))
                base_avail_h = (banner_disp_h - name_rendered_h - 4.0) if has_name else (banner_disp_h * 0.85)
                avail_h = max(8.0, base_avail_h) * max(0.3, min(2.5, self._preview_sig_scale))

                sig_ratio = min(avail_w / float(sig_rgba.width), avail_h / float(sig_rgba.height))
                final_sw = max(1.0, float(sig_rgba.width) * sig_ratio)
                final_sh = max(1.0, float(sig_rgba.height) * sig_ratio)

                scaled_spix = s_pix.scaled(
                    int(round(final_sw)), int(round(final_sh)),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                if not self._banner_sig_pixmap_item:
                    self._banner_sig_pixmap_item = self._scene.addPixmap(scaled_spix)
                    self._banner_sig_pixmap_item.setZValue(13)
                else:
                    self._banner_sig_pixmap_item.setPixmap(scaled_spix)

                sx = x + (box_w - scaled_spix.width()) / 2.0
                base_sy = banner_y + 2.0 if has_name else banner_y + (banner_disp_h - scaled_spix.height()) / 2.0
                y_nudge = self._preview_sig_pos_y * (banner_disp_h * 0.25)
                sy = max(banner_y - scaled_spix.height() * 0.3, min(banner_y + banner_disp_h - scaled_spix.height(), base_sy + y_nudge))
                self._banner_sig_pixmap_item.setPos(sx, sy)
            else:
                if self._banner_sig_pixmap_item:
                    self._scene.removeItem(self._banner_sig_pixmap_item)
                    self._banner_sig_pixmap_item = None
        else:
            if self._banner_frame:
                self._scene.removeItem(self._banner_frame)
                self._banner_frame = None
            self._clear_banner_subitems()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._crop_frame:
            click_scene = self.mapToScene(event.pos())
            rect = self._crop_frame.rect()
            if rect.contains(click_scene):
                self._is_dragging = True
                self._last_mouse_pos = click_scene
                self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._crop_frame:
            scene_pos = self.mapToScene(event.pos())
            delta = scene_pos - self._last_mouse_pos
            self._last_mouse_pos = scene_pos

            target_aspect = self._target_w / float(self._target_h)
            image_aspect = self._orig_w / float(self._orig_h)

            if image_aspect > target_aspect:
                base_box_h = float(self._orig_h)
                base_box_w = base_box_h * target_aspect
            else:
                base_box_w = float(self._orig_w)
                base_box_h = base_box_w / target_aspect

            safe_scale = max(0.2, min(5.0, self._crop_scale))
            box_w = min(float(self._orig_w), base_box_w / safe_scale)
            box_h = min(float(self._orig_h), base_box_h / safe_scale)

            max_slide_x = max(0.0, float(self._orig_w) - box_w)
            max_slide_y = max(0.0, float(self._orig_h) - box_h)

            new_x = self._norm_x
            new_y = self._norm_y

            if max_slide_x > 0:
                new_x = max(0.0, min(1.0, self._norm_x + (delta.x() / max_slide_x)))
            if max_slide_y > 0:
                new_y = max(0.0, min(1.0, self._norm_y + (delta.y() / max_slide_y)))

            if new_x != self._norm_x or new_y != self._norm_y:
                self.set_norm_position(new_x, new_y)
                self.position_changed.emit(self._norm_x, self._norm_y)

            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.85
            self.scale(factor, factor)
            event.accept()
        elif self._crop_active and not (event.modifiers() & Qt.KeyboardModifier.AltModifier):
            delta_scale = 0.05 if event.angleDelta().y() > 0 else -0.05
            new_scale = max(0.5, min(3.0, self._crop_scale + delta_scale))
            if new_scale != self._crop_scale:
                self.set_crop_scale(new_scale)
                self.scale_changed.emit(new_scale)
            event.accept()
        else:
            super().wheelEvent(event)


class BgRemovalThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, raw_image: Image.Image, bg_color: Optional[Tuple[int, int, int]] = None, parent=None):
        super().__init__(parent)
        self.raw_image = raw_image.copy()
        self.bg_color = bg_color

    def run(self):
        try:
            from offline_toolbox.images.bg_remover import remove_background
            # Run background removal offline
            result = remove_background(
                self.raw_image,
                bg_color=self.bg_color,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class ImageEditorWorkspace(QWidget):
    """
    Dedicated Image Editor for single and multi-photo editing:
    - Real-time preview with Fit to Width & sliding crop window for long photos (4R, 2x2, Passport)
    - Sliders to position/slide crop region across vertical or panoramic photos
    - Photoshop Curves (Ctrl+M) & Multiply paper removal for signatures and stamps
    - Instant export to JPG, PNG, WEBP, or direct PDF
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_image_path: Optional[Path] = None
        self._pil_image: Optional[Image.Image] = None
        self._signature_path: Optional[Path] = None
        self._signature_img: Optional[Image.Image] = None
        self._bg_thread: Optional[BgRemovalThread] = None
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # ── 1. Top Primary Toolbar ──
        toolbar_card = QFrame(self)
        toolbar_card.setStyleSheet(
            "background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 6px 12px;"
        )
        toolbar_layout = QHBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(4, 4, 4, 4)
        toolbar_layout.setSpacing(10)

        # Open File Button
        self.open_btn = QPushButton("📂 Open Image", toolbar_card)
        self.open_btn.setProperty("class", "primaryBtn")
        self.open_btn.clicked.connect(self._on_open_image)
        toolbar_layout.addWidget(self.open_btn)

        # Preset Size Selector
        preset_lbl = QLabel("Size:", toolbar_card)
        preset_lbl.setStyleSheet("color: #E2E8F0; font-weight: 600; font-size: 12px;")
        toolbar_layout.addWidget(preset_lbl)

        self.preset_combo = QComboBox(toolbar_card)
        self.preset_combo.addItem("None (Original)", None)
        for pid, preset in PHOTO_PRESETS.items():
            self.preset_combo.addItem(f"📐 {preset.name}", pid)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)
        toolbar_layout.addWidget(self.preset_combo)

        # Tools Dropdown
        self.tools_btn = QPushButton("🛠️ Crop & Adjust ▾", toolbar_card)
        self.tools_btn.setProperty("class", "secondaryBtn")
        self.tools_menu = QMenu(self)
        
        self.crop_mode_act = self.tools_menu.addAction("✅ Crop Fill Mode")
        self.crop_mode_act.setCheckable(True)
        self.crop_mode_act.setChecked(True)
        self.crop_mode_act.toggled.connect(self._on_crop_mode_toggled)
        self.crop_mode_chk = self.crop_mode_act # Keep reference for existing code
        
        self.tools_menu.addSeparator()
        
        fit_all_act = self.tools_menu.addAction("Fit Whole Photo")
        fit_all_act.triggered.connect(lambda: self.zoom_slider.setValue(100))
        
        face_act = self.tools_menu.addAction("Zoom to Face (2x2 / Passport)")
        face_act.triggered.connect(lambda: self.zoom_slider.setValue(160))
        
        fit_width_act = self.tools_menu.addAction("Fit Width")
        fit_width_act.triggered.connect(self._on_frame_fit_width_clicked)
        
        self.tools_btn.setMenu(self.tools_menu)
        toolbar_layout.addWidget(self.tools_btn)

        # Clear Image Button
        self.clear_btn = QPushButton("🗑️ Clear", toolbar_card)
        self.clear_btn.setProperty("class", "secondaryBtn")
        self.clear_btn.setToolTip("Clear currently loaded photo and reset canvas")
        self.clear_btn.clicked.connect(self._on_clear_image)
        toolbar_layout.addWidget(self.clear_btn)

        toolbar_layout.addStretch(1)

        # Export Buttons on Toolbar Right
        self.save_img_btn = QPushButton("💾 Save Image", toolbar_card)
        self.save_img_btn.setProperty("class", "primaryBtn")
        self.save_img_btn.clicked.connect(self._on_save_image)
        toolbar_layout.addWidget(self.save_img_btn)

        self.to_pdf_btn = QPushButton("📄 PDF", toolbar_card)
        self.to_pdf_btn.setProperty("class", "secondaryBtn")
        self.to_pdf_btn.clicked.connect(self._on_save_as_pdf)
        toolbar_layout.addWidget(self.to_pdf_btn)

        main_layout.addWidget(toolbar_card)

        # ── 2. Body Splitter (Canvas + Secondary Options Sidebar) ──
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left: Interactive Canvas + Bottom Canvas Status Bar
        canvas_container = QWidget(splitter)
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(6)

        self.canvas = CropOverlayView(canvas_container)
        self.canvas.position_changed.connect(self._on_canvas_pos_changed)
        self.canvas.scale_changed.connect(self._on_canvas_scale_changed)
        canvas_layout.addWidget(self.canvas, stretch=1)

        # Canvas bottom info & view tools
        canvas_bot_bar = QHBoxLayout()
        canvas_bot_bar.setSpacing(8)

        self.fit_view_btn = QPushButton("🔍 Fit View", canvas_container)
        self.fit_view_btn.setProperty("class", "secondaryBtn")
        self.fit_view_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.fit_view_btn.clicked.connect(lambda: self.canvas.fit_in_view())
        canvas_bot_bar.addWidget(self.fit_view_btn)

        self.fit_width_btn = QPushButton("↔ Fit Width", canvas_container)
        self.fit_width_btn.setProperty("class", "secondaryBtn")
        self.fit_width_btn.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.fit_width_btn.clicked.connect(lambda: self.canvas.fit_to_width())
        canvas_bot_bar.addWidget(self.fit_width_btn)

        self.btn_close_up = QPushButton("Close-up (2.2x)", canvas_container)
        self.btn_close_up.setProperty("class", "secondaryBtn")
        self.btn_close_up.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        self.btn_close_up.clicked.connect(lambda: self.zoom_slider.setValue(220))
        canvas_bot_bar.addWidget(self.btn_close_up)

        canvas_bot_bar.addStretch(1)

        self.img_info_lbl = QLabel("No image loaded", canvas_container)
        self.img_info_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")
        canvas_bot_bar.addWidget(self.img_info_lbl)

        canvas_layout.addLayout(canvas_bot_bar)
        splitter.addWidget(canvas_container)

        # Right: Tabbed Options Sidebar (320px)
        right_panel = QFrame(splitter)
        right_panel.setFixedWidth(320)
        right_panel.setProperty("class", "actionCard")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.right_tabs = QTabWidget(right_panel)
        self.right_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #334155; border-radius: 4px; background: #0F172A; }
            QTabBar::tab { background: #1E293B; color: #94A3B8; padding: 8px 12px; border: 1px solid #334155; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #0F172A; color: #38BDF8; font-weight: bold; }
        """)
        right_layout.addWidget(self.right_tabs)

        # Tab 1: Adjust & Background
        adjust_tab = QWidget()
        adjust_layout = QVBoxLayout(adjust_tab)
        adjust_layout.setSpacing(12)
        
        # Zoom & Slide Sliders
        zoom_row = QHBoxLayout()
        zoom_lbl = QLabel("🔍 Zoom:")
        zoom_lbl.setStyleSheet("color: #E2E8F0; font-weight: 600; font-size: 11px;")
        zoom_row.addWidget(zoom_lbl)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 300)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        zoom_row.addWidget(self.zoom_slider)
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(10, 300)
        self.zoom_spin.setValue(100)
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.setFixedWidth(70)
        self.zoom_spin.setStyleSheet("color: #38BDF8; background: #1E293B; border: 1px solid #475569; border-radius: 4px; padding: 2px 4px; font-weight: bold;")
        self.zoom_spin.valueChanged.connect(self._on_zoom_spin_changed)
        zoom_row.addWidget(self.zoom_spin)
        adjust_layout.addLayout(zoom_row)

        slide_row = QHBoxLayout()
        slide_lbl = QLabel("↕ Slide:")
        slide_lbl.setStyleSheet("color: #E2E8F0; font-weight: 600; font-size: 11px;")
        slide_row.addWidget(slide_lbl)
        self.pos_slider = QSlider(Qt.Orientation.Horizontal)
        self.pos_slider.setRange(0, 100)
        self.pos_slider.setValue(50)
        self.pos_slider.valueChanged.connect(self._on_slider_pos_changed)
        slide_row.addWidget(self.pos_slider)
        self.pos_val_lbl = QLabel("50%")
        self.pos_val_lbl.setStyleSheet("color: #38BDF8; font-weight: bold; min-width: 42px;")
        slide_row.addWidget(self.pos_val_lbl)
        adjust_layout.addLayout(slide_row)

        # Background Removal
        bg_card = QFrame()
        bg_card.setStyleSheet("background-color: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 8px;")
        bg_layout = QVBoxLayout(bg_card)
        
        self.bg_remove_chk = QCheckBox("Enable BG Removal & Color")
        self.bg_remove_chk.toggled.connect(self._on_bg_remove_toggled)
        bg_layout.addWidget(self.bg_remove_chk)
        
        color_row = QHBoxLayout()
        self._bg_color_rgb = (255, 255, 255)
        self.color_swatch_btn = QPushButton("⬜ Pure White")
        self.color_swatch_btn.setStyleSheet("background-color: #FFFFFF; color: #000000; font-size: 10px; padding: 3px; border-radius: 4px;")
        self.color_swatch_btn.clicked.connect(self._on_choose_bg_color)
        color_row.addWidget(self.color_swatch_btn, stretch=1)
        btn_c_blue = QPushButton("Blue")
        btn_c_blue.setStyleSheet("background-color: #1D4ED8; color: #FFF; font-size: 10px;")
        btn_c_blue.clicked.connect(lambda: self._set_bg_color(29, 78, 216, "Royal Blue"))
        color_row.addWidget(btn_c_blue)
        bg_layout.addLayout(color_row)
        
        self.apply_bg_btn = QPushButton("✨ Apply BG Removal")
        self.apply_bg_btn.setProperty("class", "secondaryBtn")
        self.apply_bg_btn.clicked.connect(self._on_apply_bg_removal)
        bg_layout.addWidget(self.apply_bg_btn)
        
        adjust_layout.addWidget(bg_card)
        adjust_layout.addStretch(1)
        self.right_tabs.addTab(adjust_tab, "🪄 Adjust")

        # Tab 2: Nametag
        nametag_tab = QWidget()
        nametag_layout = QVBoxLayout(nametag_tab)
        nametag_layout.setSpacing(8)
        
        self.nametag_chk = QCheckBox("Reserve bottom banner (Passport/ID)")
        self.nametag_chk.toggled.connect(self._on_nametag_toggled)
        nametag_layout.addWidget(self.nametag_chk)
        
        name_type_row = QHBoxLayout()
        name_type_row.addWidget(QLabel("Name:"))
        self.btn_load_name_img = QPushButton("🖋️ Upload…")
        self.btn_load_name_img.setProperty("class", "secondaryBtn")
        self.btn_load_name_img.clicked.connect(self._on_load_name_image)
        name_type_row.addWidget(self.btn_load_name_img)
        self.btn_clear_name_img = QPushButton("✕")
        self.btn_clear_name_img.setFixedWidth(24)
        self.btn_clear_name_img.clicked.connect(self._on_clear_name_image)
        name_type_row.addWidget(self.btn_clear_name_img)
        nametag_layout.addLayout(name_type_row)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. FIRST M. LAST")
        self.name_input.textChanged.connect(self._on_name_text_changed)
        nametag_layout.addWidget(self.name_input)
        
        self.name_status_lbl = QLabel("Using typed text")
        self.name_status_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        nametag_layout.addWidget(self.name_status_lbl)
        
        name_scale_row = QHBoxLayout()
        name_scale_row.addWidget(QLabel("Size:"))
        self.name_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.name_scale_slider.setRange(50, 180)
        self.name_scale_slider.setValue(100)
        self.name_scale_slider.valueChanged.connect(self._on_name_scale_changed)
        name_scale_row.addWidget(self.name_scale_slider, stretch=1)
        self.name_scale_val = QLabel("100%")
        self.name_scale_val.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: bold;")
        name_scale_row.addWidget(self.name_scale_val)
        nametag_layout.addLayout(name_scale_row)
        
        sig_header_row = QHBoxLayout()
        sig_header_row.addWidget(QLabel("Signature:"))
        self.load_sig_btn = QPushButton("🖋️ Upload…")
        self.load_sig_btn.setProperty("class", "secondaryBtn")
        self.load_sig_btn.clicked.connect(self._on_load_signature)
        sig_header_row.addWidget(self.load_sig_btn)
        self.clear_sig_btn = QPushButton("✕")
        self.clear_sig_btn.setFixedWidth(24)
        self.clear_sig_btn.clicked.connect(self._on_clear_signature)
        sig_header_row.addWidget(self.clear_sig_btn)
        nametag_layout.addLayout(sig_header_row)
        
        self.sig_status_lbl = QLabel("No signature loaded")
        self.sig_status_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        nametag_layout.addWidget(self.sig_status_lbl)
        
        sig_scale_row = QHBoxLayout()
        sig_scale_row.addWidget(QLabel("Scale:"))
        self.sig_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.sig_scale_slider.setRange(40, 220)
        self.sig_scale_slider.setValue(100)
        self.sig_scale_slider.valueChanged.connect(self._on_sig_scale_changed)
        sig_scale_row.addWidget(self.sig_scale_slider, stretch=1)
        self.sig_scale_val = QLabel("100%")
        self.sig_scale_val.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: bold;")
        sig_scale_row.addWidget(self.sig_scale_val)
        nametag_layout.addLayout(sig_scale_row)
        
        sig_pos_row = QHBoxLayout()
        sig_pos_row.addWidget(QLabel("Pos ↕:"))
        self.sig_pos_slider = QSlider(Qt.Orientation.Horizontal)
        self.sig_pos_slider.setRange(-100, 100)
        self.sig_pos_slider.setValue(0)
        self.sig_pos_slider.valueChanged.connect(self._on_sig_pos_changed)
        sig_pos_row.addWidget(self.sig_pos_slider, stretch=1)
        self.sig_pos_val = QLabel("0")
        self.sig_pos_val.setStyleSheet("color: #38BDF8; font-size: 10px; font-weight: bold;")
        sig_pos_row.addWidget(self.sig_pos_val)
        nametag_layout.addLayout(sig_pos_row)
        
        nametag_layout.addStretch(1)
        self.right_tabs.addTab(nametag_tab, "🏷️ Nametag")

        # Tab 3: Clean Ink
        sig_tab = QWidget()
        sig_layout = QVBoxLayout(sig_tab)
        sig_layout.setSpacing(8)
        
        self.clean_sig_btn = QPushButton("✂️ Clean Signature (Ctrl+M)")
        self.clean_sig_btn.setProperty("class", "secondaryBtn")
        self.clean_sig_btn.clicked.connect(self._on_clean_signature)
        sig_layout.addWidget(self.clean_sig_btn)
        
        self.clean_name_btn = QPushButton("✂️ Clean Name (Ctrl+M)")
        self.clean_name_btn.setProperty("class", "secondaryBtn")
        self.clean_name_btn.clicked.connect(self._on_clean_name)
        sig_layout.addWidget(self.clean_name_btn)
        
        sig_layout.addStretch(1)
        self.right_tabs.addTab(sig_tab, "✂️ Clean Ink")

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, stretch=1)
        self._name_path: Optional[Path] = None
        self._name_img: Optional[Image.Image] = None
        self._raw_pil_image: Optional[Image.Image] = None  # Original unmodified
        self._set_tools_enabled(False)

    def _set_tools_enabled(self, enabled: bool):
        self.fit_view_btn.setEnabled(enabled)
        self.fit_width_btn.setEnabled(enabled)
        self.zoom_slider.setEnabled(enabled)
        self.pos_slider.setEnabled(enabled)
        self.preset_combo.setEnabled(enabled)
        self.crop_mode_chk.setEnabled(enabled)
        self.bg_remove_chk.setEnabled(enabled)
        self.color_swatch_btn.setEnabled(enabled)
        self.apply_bg_btn.setEnabled(enabled)
        self.nametag_chk.setEnabled(enabled)
        self.btn_load_name_img.setEnabled(enabled)
        self.btn_clear_name_img.setEnabled(enabled)
        self.name_input.setEnabled(enabled)
        self.name_scale_slider.setEnabled(enabled)
        self.load_sig_btn.setEnabled(enabled)
        self.clear_sig_btn.setEnabled(enabled)
        self.sig_scale_slider.setEnabled(enabled)
        self.sig_pos_slider.setEnabled(enabled)
        self.clean_sig_btn.setEnabled(enabled)
        self.clean_name_btn.setEnabled(enabled)
        self.clear_btn.setEnabled(enabled)
        self.save_img_btn.setEnabled(enabled)
        self.to_pdf_btn.setEnabled(enabled)

    def _on_frame_fit_width_clicked(self):
        """Snaps crop box width to full photo width (ideal when framing 2x2 into Passport 35x45mm)."""
        scale = self.canvas.calculate_scale_for_fit_width()
        val = int(round(scale * 100))
        self.zoom_slider.setValue(val)

    def _on_clear_image(self):
        """Clear currently loaded photo and reset canvas."""
        self._current_image_path = None
        self._raw_pil_image = None
        self._pil_image = None
        self.canvas.clear()
        self.img_info_lbl.setText("No image loaded")
        self.bg_remove_chk.blockSignals(True)
        self.bg_remove_chk.setChecked(False)
        self.bg_remove_chk.blockSignals(False)
        self._set_tools_enabled(False)

    def load_image_path(self, path: Path):
        if not path.exists():
            return
        self._current_image_path = path
        self._raw_pil_image = Image.open(path)
        self._pil_image = self._raw_pil_image.copy()

        pix = QPixmap(str(path))
        self.canvas.load_image(pix)

        w, h = self._pil_image.size
        self.img_info_lbl.setText(f"{path.name} ({w} x {h} px)")
        self._set_tools_enabled(True)
        self._on_preset_selected()
        self._refresh_canvas_nametag()

    def _on_open_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image to Edit",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp *.tiff);;All Files (*.*)",
        )
        if file_path:
            self.load_image_path(Path(file_path))

    def _on_preset_selected(self):
        preset_id = self.preset_combo.currentData()
        if preset_id and preset_id in PHOTO_PRESETS:
            preset = PHOTO_PRESETS[preset_id]
            crop_active = self.crop_mode_chk.isChecked()

            if preset_id == "passport_2x2_embed":
                # Force the nametag banner so the crop box becomes a perfect 1:1 square.
                # Banner height = (531 - 413) / 531 ≈ 22.2%
                embed_pct = 1.0 - (float(preset.width_px) / float(preset.height_px))
                self.nametag_chk.blockSignals(True)
                self.nametag_chk.setChecked(True)
                self.nametag_chk.blockSignals(False)
                self.canvas.set_target_aspect(preset.width_px, preset.height_px, active=crop_active)
                self.canvas.set_nametag_overlay(True, height_pct=embed_pct)
                if self._pil_image:
                    self._on_frame_fit_width_clicked()
                    self.pos_slider.setValue(0)
            else:
                self.canvas.set_target_aspect(preset.width_px, preset.height_px, active=crop_active)
                self.canvas.set_nametag_overlay(self.nametag_chk.isChecked(), height_pct=0.18)
        else:
            self.canvas.set_target_aspect(600, 600, active=False)
            self.canvas.set_nametag_overlay(False)
        self._refresh_canvas_nametag()

    def _on_crop_mode_toggled(self, checked: bool):
        self._on_preset_selected()

    def _on_nametag_toggled(self, checked: bool):
        self.canvas.set_nametag_overlay(checked, height_pct=0.18)
        self._refresh_canvas_nametag()

    def _on_name_text_changed(self, text: str):
        if text != text.upper():
            cursor_pos = self.name_input.cursorPosition()
            self.name_input.blockSignals(True)
            self.name_input.setText(text.upper())
            self.name_input.setCursorPosition(cursor_pos)
            self.name_input.blockSignals(False)
        self._refresh_canvas_nametag()

    def _on_name_scale_changed(self, value: int):
        self.name_scale_val.setText(f"{value}%")
        self._refresh_canvas_nametag()

    def _on_sig_scale_changed(self, value: int):
        self.sig_scale_val.setText(f"{value}%")
        self._refresh_canvas_nametag()

    def _on_sig_pos_changed(self, value: int):
        self.sig_pos_val.setText(f"{value}")
        self._refresh_canvas_nametag()

    def _refresh_canvas_nametag(self):
        """Update live text and signature graphics inside the white space banner."""
        self.canvas.update_nametag_content(
            name_text=self.name_input.text().strip(),
            name_pil=self._name_img,
            name_scale=self.name_scale_slider.value() / 100.0,
            sig_pil=self._signature_img,
            sig_scale=self.sig_scale_slider.value() / 100.0,
            sig_pos_y=self.sig_pos_slider.value() / 100.0,
        )

    # ── Background Removal & Color Handlers ──
    def _on_bg_remove_toggled(self, checked: bool):
        if checked and self._raw_pil_image:
            self._apply_background_process()
        elif not checked and self._raw_pil_image:
            # Revert to original
            self._pil_image = self._raw_pil_image.copy()
            self._reload_canvas_pixmap()

    def _on_choose_bg_color(self):
        qc = QColorDialog.getColor(
            QColor(self._bg_color_rgb[0], self._bg_color_rgb[1], self._bg_color_rgb[2]),
            self,
            "Select Background Color",
        )
        if qc.isValid():
            self._set_bg_color(qc.red(), qc.green(), qc.blue(), qc.name())

    def _set_bg_color(self, r: int, g: int, b: int, name: str):
        self._bg_color_rgb = (r, g, b)
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        # Pick contrasting text color for button
        text_color = "#FFFFFF" if (r * 0.299 + g * 0.587 + b * 0.114) < 140 else "#000000"
        self.color_swatch_btn.setText(f"🎨 {name} ({hex_code})")
        self.color_swatch_btn.setStyleSheet(
            f"background-color: {hex_code}; color: {text_color}; font-weight: bold; font-size: 11px; padding: 3px 8px; border-radius: 4px;"
        )
        if self.bg_remove_chk.isChecked():
            self._apply_background_process()

    def _on_apply_bg_removal(self):
        self.bg_remove_chk.setChecked(True)
        self._apply_background_process()

    def _apply_background_process(self):
        if not self._raw_pil_image:
            return
        if self._bg_thread and self._bg_thread.isRunning():
            return

        self.apply_bg_btn.setText("⏳ Processing u2net…")
        self.apply_bg_btn.setEnabled(False)

        self._bg_thread = BgRemovalThread(
            raw_image=self._raw_pil_image,
            bg_color=self._bg_color_rgb,
            parent=self,
        )
        self._bg_thread.finished.connect(self._on_bg_removal_finished)
        self._bg_thread.error.connect(self._on_bg_removal_error)
        self._bg_thread.start()

    def _on_bg_removal_finished(self, processed: Image.Image):
        self._pil_image = processed
        self._reload_canvas_pixmap()
        self.apply_bg_btn.setText("✨ Apply BG Removal (Live)")
        self.apply_bg_btn.setEnabled(True)

    def _on_bg_removal_error(self, err_msg: str):
        self.apply_bg_btn.setText("✨ Apply BG Removal (Live)")
        self.apply_bg_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Failed to remove background:\n{err_msg}")

    def _reload_canvas_pixmap(self):
        if not self._pil_image:
            return
        # Convert PIL to QPixmap
        rgba = self._pil_image.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
        pix = QPixmap.fromImage(qimg)
        self.canvas.load_image(pix)
        self._on_preset_selected()

    # ── Handwritten Name Handlers ──
    def _on_load_name_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Handwritten Name Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)",
        )
        if not file_path:
            return
        p = Path(file_path)
        self._name_path = p
        try:
            self._name_img = Image.open(p)
            self.name_status_lbl.setText(f"Handwritten: {p.name}")
            self.name_status_lbl.setStyleSheet("color: #38BDF8; font-size: 10px;")
            self.nametag_chk.setChecked(True)
            self._refresh_canvas_nametag()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load name image:\n{e}")

    def _on_clear_name_image(self):
        self._name_path = None
        self._name_img = None
        self.name_status_lbl.setText("Using typed text")
        self.name_status_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        self._refresh_canvas_nametag()

    def _on_clean_name(self):
        target = self._name_path if (self._name_path and self._name_path.exists()) else self._current_image_path
        if not target:
            return
        from offline_toolbox.ui.pdf.signature_dialog import SignatureCleanDialog
        dlg = SignatureCleanDialog(target, parent=self)
        if dlg.exec():
            cleaned_path = dlg.get_cleaned_image_path()
            if cleaned_path and cleaned_path.exists():
                self._name_path = cleaned_path
                self._name_img = Image.open(cleaned_path)
                self.name_status_lbl.setText(f"Cleaned: {cleaned_path.name}")
                self.name_status_lbl.setStyleSheet("color: #38BDF8; font-size: 10px;")
                self.nametag_chk.setChecked(True)
                self._refresh_canvas_nametag()

    # ── Signature Handlers ──
    def _on_load_signature(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Signature Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp);;All Files (*.*)",
        )
        if not file_path:
            return
        p = Path(file_path)
        self._signature_path = p
        try:
            self._signature_img = Image.open(p)
            self.sig_status_lbl.setText(f"Loaded: {p.name}")
            self.sig_status_lbl.setStyleSheet("color: #38BDF8; font-size: 10px;")
            self.nametag_chk.setChecked(True)
            self._refresh_canvas_nametag()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load signature:\n{e}")

    def _on_clear_signature(self):
        self._signature_path = None
        self._signature_img = None
        self.sig_status_lbl.setText("No signature loaded")
        self.sig_status_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        self._refresh_canvas_nametag()

    def _on_clean_signature(self):
        target_to_clean = self._signature_path if (self._signature_path and self._signature_path.exists()) else self._current_image_path
        if not target_to_clean:
            return
        from offline_toolbox.ui.pdf.signature_dialog import SignatureCleanDialog
        dlg = SignatureCleanDialog(target_to_clean, parent=self)
        if dlg.exec():
            cleaned_path = dlg.get_cleaned_image_path()
            if cleaned_path and cleaned_path.exists():
                self._signature_path = cleaned_path
                self._signature_img = Image.open(cleaned_path)
                self.sig_status_lbl.setText(f"Cleaned: {cleaned_path.name}")
                self.sig_status_lbl.setStyleSheet("color: #38BDF8; font-size: 10px;")
                self.nametag_chk.setChecked(True)
                self._refresh_canvas_nametag()

    # ── Canvas & Slider Sync ──
    def _on_zoom_slider_changed(self, value: int):
        scale = value / 100.0
        self.zoom_spin.blockSignals(True)
        self.zoom_spin.setValue(value)
        self.zoom_spin.blockSignals(False)
        self.canvas.set_crop_scale(scale)

    def _on_zoom_spin_changed(self, value: int):
        scale = value / 100.0
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(value)
        self.zoom_slider.blockSignals(False)
        self.canvas.set_crop_scale(scale)

    def _on_canvas_scale_changed(self, scale: float):
        val = int(round(scale * 100))
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(val)
        self.zoom_slider.blockSignals(False)
        self.zoom_spin.blockSignals(True)
        self.zoom_spin.setValue(val)
        self.zoom_spin.blockSignals(False)

    def _on_slider_pos_changed(self, value: int):
        norm = value / 100.0
        pct = value
        self.pos_val_lbl.setText(f"{pct}%")
        self.canvas.set_norm_position(norm, norm)

    def _on_canvas_pos_changed(self, norm_x: float, norm_y: float):
        if self._pil_image:
            w, h = self._pil_image.size
            val = int(round(norm_y * 100)) if h >= w else int(round(norm_x * 100))
            self.pos_slider.blockSignals(True)
            self.pos_slider.setValue(val)
            self.pos_slider.blockSignals(False)
            self.pos_val_lbl.setText(f"{val}%")

    def _get_processed_pil(self) -> Optional[Image.Image]:
        if not self._pil_image:
            return None

        # Base photo: apply background removal if toggled on but not yet applied to _pil_image
        base_img = self._pil_image
        if self.bg_remove_chk.isChecked() and self._raw_pil_image:
            from offline_toolbox.images.bg_remover import remove_background
            base_img = remove_background(self._raw_pil_image, bg_color=self._bg_color_rgb)

        preset_id = self.preset_combo.currentData()
        if preset_id and preset_id in PHOTO_PRESETS:
            preset = PHOTO_PRESETS[preset_id]
            crop_fill = self.crop_mode_chk.isChecked()
            norm = self.pos_slider.value() / 100.0
            crop_scale = self.zoom_slider.value() / 100.0
            nametag_on = self.nametag_chk.isChecked()
            name_txt = self.name_input.text().strip()
            name_sc = self.name_scale_slider.value() / 100.0
            sig_sc = self.sig_scale_slider.value() / 100.0
            sig_py = self.sig_pos_slider.value() / 100.0

            # WYSIWYG exact crop box from canvas crop frame
            exact_box = self.canvas.get_exact_crop_rect() if crop_fill else None

            # For passport_2x2_embed, align to top and use correct banner proportions
            is_embed = preset_id == "passport_2x2_embed"
            if is_embed:
                nametag_on = True
                nametag_pct = 1.0 - (float(preset.width_px) / float(preset.height_px))
            else:
                nametag_pct = 0.18

            return fit_image_to_preset(
                base_img,
                target_width=preset.width_px,
                target_height=preset.height_px,
                fill_color=self._bg_color_rgb if self.bg_remove_chk.isChecked() else (255, 255, 255),
                crop_to_fill=crop_fill,
                offset_x=norm,
                offset_y=norm,
                crop_scale=crop_scale,
                exact_crop_box=exact_box,
                align_top=is_embed,
                nametag_enabled=nametag_on,
                nametag_height_pct=nametag_pct,
                name_text=name_txt,
                name_image=self._name_img,
                name_scale=name_sc,
                signature_image=self._signature_img,
                signature_scale=sig_sc,
                signature_pos_y=sig_py,
            )
        return base_img

    def _on_save_image(self):
        img = self._get_processed_pil()
        if not img:
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Processed Image",
            f"edited_{self._current_image_path.stem}.jpg" if self._current_image_path else "edited_photo.jpg",
            "JPEG Image (*.jpg);;PNG Image (*.png);;WebP Image (*.webp)",
        )
        if not out_path:
            return

        p = Path(out_path)
        fmt = "JPEG" if p.suffix.lower() in (".jpg", ".jpeg") else ("PNG" if p.suffix.lower() == ".png" else "WEBP")

        save_img = img
        if fmt == "JPEG" and save_img.mode == "RGBA":
            from offline_toolbox.images.color import flatten_alpha
            save_img = flatten_alpha(save_img)

        save_img.save(p, format=fmt, quality=95)
        QMessageBox.information(self, "Saved", f"Successfully saved image:\n{p.name}")

    def _on_save_as_pdf(self):
        img = self._get_processed_pil()
        if not img:
            return

        out_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save as PDF",
            f"{self._current_image_path.stem}.pdf" if self._current_image_path else "photo.pdf",
            "PDF Files (*.pdf)",
        )
        if not out_path:
            return

        from offline_toolbox.filesystem.temporary import TempFileManager
        tm = TempFileManager()
        run_dir = tm.create_run_directory("pdf_export_")
        temp_img = tm.create_temp_file(run_dir, ".png")
        img.save(temp_img, format="PNG")

        from offline_toolbox.pdf.service import PDFService
        res = PDFService.from_images([temp_img], output_path=Path(out_path))
        if res.is_ok():
            QMessageBox.information(self, "PDF Created", f"Successfully saved borderless PDF:\n{res.value.name}")
        else:
            QMessageBox.critical(self, "Error", res.error.message)
