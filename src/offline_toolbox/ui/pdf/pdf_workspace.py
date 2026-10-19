"""Acrobat-style Native Desktop PDF Workspace with multi-page continuous scroll, zoom engine, and search."""

import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from offline_toolbox.core.models import CompressionPreset
from offline_toolbox.jobs.manager import JobManager
from offline_toolbox.pdf.editor import ImageOverlay, TextOverlay
from offline_toolbox.pdf.renderer import PDFRenderer
from offline_toolbox.pdf.service import PDFService
from offline_toolbox.ui.pdf.overlay_items import EditableTextOverlayItem, ResizableImageOverlayItem
from offline_toolbox.ui.pdf.search_bar import PDFSearchBar
from offline_toolbox.ui.pdf.viewer_toolbar import PDFViewerToolbar
from offline_toolbox.ui.widgets.progress_overlay import ProgressOverlay


class PDFViewerCanvas(QGraphicsView):
    """
    Native Desktop PDF Viewport with Continuous Scroll, Focal Zoom, Page Shadows, and Search Highlights.
    """

    page_changed = Signal(int)       # 0-indexed visible page
    zoom_changed = Signal(float)     # Current zoom factor (e.g. 1.0 = 100%)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setBackgroundBrush(QBrush(QColor("#1E293B")))  # Acrobat dark slate canvas

        self._doc_path: Optional[Path] = None
        self._total_pages: int = 0
        self._current_page_idx: int = 0
        self._is_continuous: bool = True
        self._zoom_factor: float = 1.0

        # Tracking items
        self._page_items: List[QGraphicsPixmapItem] = []
        self._page_shadow_items: List[QGraphicsRectItem] = []
        self._page_rects: List[QRectF] = []
        self._highlight_items: List[QGraphicsRectItem] = []
        self._search_matches: List[Tuple[int, fitz.Rect]] = []  # (page_idx, rect)
        self._active_match_idx: int = -1

        # Interactive Overlay Items (Text & Image)
        self._overlay_items: List[QGraphicsItem] = []

        # Track scrollbar to update visible page index
        self.verticalScrollBar().valueChanged.connect(self._on_scroll_changed)

    # ── Document Setup & Rendering ──────────────────────────────────────────

    def load_document(self, doc_path: Path, total_pages: int):
        """Set up and render document pages in continuous or single-page mode."""
        self._doc_path = doc_path
        self._total_pages = total_pages
        self._current_page_idx = 0
        self._clear_highlights()
        self.render_all_pages()

    def render_all_pages(self):
        """Render pages onto the scene with drop shadows and page gaps."""
        self._scene.clear()
        self._page_items.clear()
        self._page_shadow_items.clear()
        self._page_rects.clear()
        self._highlight_items.clear()

        if not self._doc_path or self._total_pages == 0:
            return

        gap = 20.0
        current_y = 20.0
        max_width = 0.0

        doc = None
        try:
            doc = fitz.open(str(self._doc_path))

            pages_to_render = range(self._total_pages) if self._is_continuous else [self._current_page_idx]

            for p_idx in pages_to_render:
                page = doc[p_idx]
                pix = page.get_pixmap(dpi=150, alpha=False)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)

                pw = float(pixmap.width())
                ph = float(pixmap.height())
                max_width = max(max_width, pw)

                # Page shadow / border card
                shadow_rect = self._scene.addRect(
                    QRectF(0, current_y, pw, ph),
                    QPen(QColor("#475569"), 1.0),
                    QBrush(QColor("#0F172A")),
                )
                shadow_rect.setZValue(1)

                # Actual page pixmap
                p_item = self._scene.addPixmap(pixmap)
                p_item.setPos(0, current_y)
                p_item.setZValue(2)

                self._page_items.append(p_item)
                self._page_shadow_items.append(shadow_rect)
                self._page_rects.append(QRectF(0, current_y, pw, ph))

                current_y += ph + gap

            # Set scene rect with generous horizontal padding so pages are nicely centered
            scene_w = max_width + 80.0
            scene_h = current_y + 40.0
            # Center the pages horizontally in scene
            for item in self._page_items:
                item.setX((scene_w - item.pixmap().width()) / 2.0)
            for shadow in self._page_shadow_items:
                shadow.setX((scene_w - shadow.rect().width()) / 2.0)
            for i, r in enumerate(self._page_rects):
                x_off = (scene_w - r.width()) / 2.0
                self._page_rects[i] = QRectF(x_off, r.y(), r.width(), r.height())

            self.setSceneRect(0, 0, scene_w, scene_h)

        except Exception as exc:
            print(f"Error rendering PDF pages: {exc}")
        finally:
            if doc:
                doc.close()

    def set_continuous_mode(self, continuous: bool):
        """Toggle between continuous vertical scroll and single-page display."""
        if self._is_continuous == continuous:
            return
        self._is_continuous = continuous
        self.render_all_pages()
        self.jump_to_page(self._current_page_idx)

    # ── Page Navigation ─────────────────────────────────────────────────────

    def jump_to_page(self, page_idx: int):
        """Scroll smoothly to center the requested page in the viewport."""
        if page_idx < 0 or page_idx >= self._total_pages:
            return
        self._current_page_idx = page_idx

        if not self._is_continuous:
            self.render_all_pages()
            return

        if page_idx < len(self._page_rects):
            target_rect = self._page_rects[page_idx]
            self.centerOn(target_rect.center())
            self.page_changed.emit(page_idx)

    def _on_scroll_changed(self):
        """Detect which page is currently most visible in the viewport center."""
        if not self._is_continuous or not self._page_rects:
            return

        # Viewport center in scene coords
        center_scene_pt = self.mapToScene(self.viewport().rect().center())
        y = center_scene_pt.y()

        closest_idx = 0
        min_dist = float("inf")
        for i, rect in enumerate(self._page_rects):
            dist = abs(rect.center().y() - y)
            if dist < min_dist:
                min_dist = dist
                closest_idx = i

        if closest_idx != self._current_page_idx:
            self._current_page_idx = closest_idx
            self.page_changed.emit(closest_idx)

    # ── Zoom Engine ─────────────────────────────────────────────────────────

    def set_zoom(self, factor: float):
        """Apply absolute zoom factor (e.g. 1.0 = 100%)."""
        factor = max(0.25, min(5.0, factor))
        self._zoom_factor = factor
        self.resetTransform()
        self.scale(factor, factor)
        self.zoom_changed.emit(self._zoom_factor)

    def zoom_in(self):
        self.set_zoom(self._zoom_factor * 1.2)

    def zoom_out(self):
        self.set_zoom(self._zoom_factor * 0.833)

    def fit_width(self):
        """Scale pages so document width comfortably fits viewport width."""
        if not self._page_rects:
            return
        max_page_w = max(r.width() for r in self._page_rects)
        vw = float(self.viewport().width() - 40)
        if max_page_w > 0:
            scale = vw / max_page_w
            self.set_zoom(scale)

    def fit_page(self):
        """Scale document so full page is visible inside viewport."""
        if not self._page_rects:
            return
        cur_rect = self._page_rects[min(self._current_page_idx, len(self._page_rects) - 1)]
        vw = float(self.viewport().width() - 40)
        vh = float(self.viewport().height() - 40)
        if cur_rect.width() > 0 and cur_rect.height() > 0:
            scale = min(vw / cur_rect.width(), vh / cur_rect.height())
            self.set_zoom(scale)

    def wheelEvent(self, event):
        """Interactive focal zoom with Ctrl+Wheel; vertical scroll otherwise."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            zoom_step = 1.15 if delta > 0 else (1.0 / 1.15)
            new_zoom = max(0.25, min(5.0, self._zoom_factor * zoom_step))
            self._zoom_factor = new_zoom
            self.scale(zoom_step, zoom_step)
            self.zoom_changed.emit(self._zoom_factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Handle canvas mouse clicks: clear search highlights on blank click, allow item interaction."""
        clicked_item = self.itemAt(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            # If user clicked on blank canvas or on page background (not on an overlay or search highlight)
            if clicked_item is None or clicked_item in self._page_items or clicked_item in self._page_shadow_items:
                # Clear active search highlights
                if self._highlight_items:
                    self._clear_highlights()
                # Clear selection of overlay items
                self._scene.clearSelection()

        super().mousePressEvent(event)

    # ── Search & In-Page Text Highlights ────────────────────────────────────

    def search_text(self, query: str) -> int:
        """Search all document pages for text query and highlight matches on canvas."""
        self._clear_highlights()
        self._search_matches.clear()
        self._active_match_idx = -1

        if not self._doc_path or not query.strip():
            return 0

        doc = None
        try:
            doc = fitz.open(str(self._doc_path))
            for p_idx in range(self._total_pages):
                page = doc[p_idx]
                rects = page.search_for(query)
                for r in rects:
                    self._search_matches.append((p_idx, r))

            # Create visual highlight overlays for all matches
            for p_idx, r in self._search_matches:
                if p_idx < len(self._page_rects):
                    page_rect = self._page_rects[p_idx]
                    # Convert PDF point coordinates (72 dpi) to 150 dpi scene coordinates
                    dpi_scale = 150.0 / 72.0
                    hx = page_rect.x() + (r.x0 * dpi_scale)
                    hy = page_rect.y() + (r.y0 * dpi_scale)
                    hw = (r.x1 - r.x0) * dpi_scale
                    hh = (r.y1 - r.y0) * dpi_scale

                    h_item = self._scene.addRect(
                        QRectF(hx, hy, hw, hh),
                        QPen(QColor(245, 158, 11, 200), 1.0),
                        QBrush(QColor(254, 240, 138, 150)),  # Yellow highlight
                    )
                    h_item.setZValue(10)
                    self._highlight_items.append(h_item)

            if self._search_matches:
                self.next_search_match()

            return len(self._search_matches)
        except Exception as e:
            print(f"Search error: {e}")
            return 0
        finally:
            if doc:
                doc.close()

    def next_search_match(self):
        if not self._search_matches:
            return
        self._active_match_idx = (self._active_match_idx + 1) % len(self._search_matches)
        self._focus_search_match(self._active_match_idx)

    def prev_search_match(self):
        if not self._search_matches:
            return
        self._active_match_idx = (self._active_match_idx - 1 + len(self._search_matches)) % len(self._search_matches)
        self._focus_search_match(self._active_match_idx)

    def _focus_search_match(self, match_idx: int):
        if match_idx < 0 or match_idx >= len(self._highlight_items):
            return
        # Brighten active highlight
        for i, item in enumerate(self._highlight_items):
            if i == match_idx:
                item.setBrush(QBrush(QColor(245, 158, 11, 220)))  # Orange active
            else:
                item.setBrush(QBrush(QColor(254, 240, 138, 150)))  # Yellow normal

        active_item = self._highlight_items[match_idx]
        self.centerOn(active_item)

    def _clear_highlights(self):
        for item in self._highlight_items:
            self._scene.removeItem(item)
        self._highlight_items.clear()

    # ── Interactive Overlay Operations (Text & Image) ─────────────────────────

    def add_text_overlay(self, page_idx: int) -> Optional[EditableTextOverlayItem]:
        """Place an editable text box onto the specified page."""
        if page_idx < 0 or page_idx >= len(self._page_rects):
            return None

        page_rect = self._page_rects[page_idx]
        item = EditableTextOverlayItem("Double click to edit text", page_idx)
        # Position near center of page
        item.setPos(page_rect.x() + page_rect.width() / 4.0, page_rect.y() + 100.0)
        self._scene.addItem(item)
        self._overlay_items.append(item)
        item.deleted.connect(self._remove_overlay_item)
        item.setSelected(True)
        return item

    def add_image_overlay(self, page_idx: int, image_path: Path) -> Optional[ResizableImageOverlayItem]:
        """Place a resizable, draggable image overlay onto the specified page."""
        if page_idx < 0 or page_idx >= len(self._page_rects):
            return None

        page_rect = self._page_rects[page_idx]
        item = ResizableImageOverlayItem(image_path, page_idx)
        # Position near center of page
        item.setPos(page_rect.x() + page_rect.width() / 4.0, page_rect.y() + 150.0)
        self._scene.addItem(item)
        self._overlay_items.append(item)
        item.deleted.connect(self._remove_overlay_item)
        item.setSelected(True)
        item.setSelected(True)
        return item

    def add_acroform_overlay(self, page_idx: int, field_type: int):
        """Place an interactive acroform field onto the specified page."""
        if page_idx < 0 or page_idx >= len(self._page_rects):
            return None

        page_rect = self._page_rects[page_idx]
        from offline_toolbox.ui.pdf.overlay_items import AcroformFieldOverlayItem
        item = AcroformFieldOverlayItem(field_type, page_idx)
        # Position near center of page
        item.setPos(page_rect.x() + page_rect.width() / 4.0, page_rect.y() + 200.0)
        self._scene.addItem(item)
        self._overlay_items.append(item)
        item.deleted.connect(self._remove_overlay_item)
        item.setSelected(True)
        return item

    def _remove_overlay_item(self, item):
        if item in self._overlay_items:
            self._overlay_items.remove(item)
            self._scene.removeItem(item)

    def has_pending_overlays(self) -> bool:
        return len(self._overlay_items) > 0

    def get_pending_overlays(self) -> Tuple[List[TextOverlay], List[ImageOverlay], List]:
        """
        Convert all interactive canvas overlay items into PDF point coordinate models (72 DPI).
        Scene coordinates are at 150 DPI.
        """
        text_overlays: List[TextOverlay] = []
        image_overlays: List[ImageOverlay] = []
        acroform_overlays: List = []
        dpi_scale = 72.0 / 150.0

        for item in self._overlay_items:
            p_idx = item.page_index
            if p_idx >= len(self._page_rects):
                continue
            page_rect = self._page_rects[p_idx]

            # Relative position on the page in scene units
            rel_x = item.scenePos().x() - page_rect.x()
            rel_y = item.scenePos().y() - page_rect.y()

            # Convert to PDF points
            pdf_x = rel_x * dpi_scale
            pdf_y = rel_y * dpi_scale

            if isinstance(item, EditableTextOverlayItem):
                txt = item.toPlainText()
                if txt.strip():
                    br = item.boundingRect()
                    pdf_w = br.width() * dpi_scale
                    pdf_h = br.height() * dpi_scale
                    qc = item.get_text_color()
                    rgb = (qc.redF(), qc.greenF(), qc.blueF())
                    text_overlays.append(
                        TextOverlay(
                            page_index=p_idx,
                            x=pdf_x,
                            y=pdf_y,
                            width=pdf_w,
                            height=pdf_h,
                            text=txt,
                            font_family=item.get_font_family(),
                            font_size=item.get_font_size(),
                            color=rgb,
                            is_bold=item.is_bold(),
                            is_italic=item.is_italic(),
                            is_underline=item.is_underline(),
                        )
                    )
            elif isinstance(item, ResizableImageOverlayItem):
                br = item.boundingRect()
                # Use internal width/height
                pdf_w = item._width * dpi_scale
                pdf_h = item._height * dpi_scale
                image_overlays.append(
                    ImageOverlay(
                        page_index=p_idx,
                        x=pdf_x,
                        y=pdf_y,
                        width=pdf_w,
                        height=pdf_h,
                        image_path=item.image_path,
                        opacity=item.get_overlay_opacity(),
                    )
                )
            else:
                from offline_toolbox.ui.pdf.overlay_items import AcroformFieldOverlayItem
                if isinstance(item, AcroformFieldOverlayItem):
                    pdf_w = item._width * dpi_scale
                    pdf_h = item._height * dpi_scale
                    from offline_toolbox.pdf.editor import AcroformOverlay
                    acroform_overlays.append(
                        AcroformOverlay(
                            page_index=p_idx,
                            x=pdf_x,
                            y=pdf_y,
                            width=pdf_w,
                            height=pdf_h,
                            field_type=item.field_type,
                            field_name=item.field_name,
                        )
                    )

        return text_overlays, image_overlays, acroform_overlays

    def clear_overlay_items(self):
        for item in self._overlay_items:
            self._scene.removeItem(item)
        self._overlay_items.clear()


class PDFWorkspace(QWidget):
    """
    Full-featured Native Adobe Acrobat-style Desktop PDF Workspace.
    Includes Reader HUD Toolbar, Floating Search Bar, Bookmarks/TOC, and High-Fidelity Viewing.
    """

    document_loaded = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pdf_path: Optional[Path] = None
        self._current_pdf_path: Optional[Path] = None
        self._is_modified: bool = False
        self._page_count: int = 0
        self._current_page_idx: int = 0
        self._init_ui()
        self._setup_shortcuts()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── 1. Top Action Toolbar (File & Document Operations) ──
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.open_btn = QPushButton("📂 Open PDF", self)
        self.open_btn.setProperty("class", "secondaryBtn")
        self.open_btn.clicked.connect(self._on_open_pdf)
        top_bar.addWidget(self.open_btn)

        self.save_btn = QPushButton("💾 Save", self)
        self.save_btn.setProperty("class", "secondaryBtn")
        self.save_btn.setToolTip("Save changes directly into the current PDF file (Ctrl+S)")
        self.save_btn.clicked.connect(self._on_save)
        top_bar.addWidget(self.save_btn)

        # Tools Dropdown Button
        self.tools_btn = QPushButton("🛠️ Tools ▾", self)
        self.tools_btn.setProperty("class", "secondaryBtn")
        self.tools_menu = QMenu(self)
        
        # Actions for Tools Menu
        self.save_as_act = self.tools_menu.addAction("💾 Save As…")
        self.save_as_act.triggered.connect(self._on_save_as)
        
        self.print_act = self.tools_menu.addAction("🖨️ Print…")
        self.print_act.triggered.connect(self._on_print)
        
        self.tools_menu.addSeparator()
        
        self.rot_tool_act = self.tools_menu.addAction("🔄 Rotate Pages…")
        self.rot_tool_act.triggered.connect(self._open_rotate_dialog)
        
        self.reorder_pages_act = self.tools_menu.addAction("🔀 Rearrange Pages…")
        self.reorder_pages_act.triggered.connect(self._open_reorder_dialog)
        
        self.delete_pages_act = self.tools_menu.addAction("🗑️ Delete Pages…")
        self.delete_pages_act.triggered.connect(self._open_delete_dialog)
        
        self.tools_menu.addSeparator()
        
        self.export_img_act = self.tools_menu.addAction("🖼️ PDF to JPEG…")
        self.export_img_act.triggered.connect(self._open_export_images_dialog)
        
        self.compress_act = self.tools_menu.addAction("🗜️ Compress PDF")
        self.compress_act.triggered.connect(self._compress_current)
        
        self.word_act = self.tools_menu.addAction("📄 Convert to Word (.docx)")
        self.word_act.triggered.connect(self._convert_to_word)

        self.tools_btn.setMenu(self.tools_menu)
        top_bar.addWidget(self.tools_btn)

        top_bar.addStretch(1)

        self.page_lbl = QLabel("No PDF loaded", self)
        self.page_lbl.setObjectName("pageInfoLbl")
        top_bar.addWidget(self.page_lbl)

        layout.addLayout(top_bar)

        # ── 2. Acrobat Reader Floating/Docked Toolbar ──
        self.reader_toolbar = PDFViewerToolbar(self)
        self.reader_toolbar.page_changed.connect(self._on_toolbar_page_jump)
        self.reader_toolbar.zoom_in_requested.connect(self._on_zoom_in)
        self.reader_toolbar.zoom_out_requested.connect(self._on_zoom_out)
        self.reader_toolbar.fit_width_requested.connect(self._on_fit_width)
        self.reader_toolbar.fit_page_requested.connect(self._on_fit_page)
        self.reader_toolbar.zoom_preset_selected.connect(self._on_zoom_preset)
        self.reader_toolbar.toggle_continuous_requested.connect(self._on_continuous_toggled)
        self.reader_toolbar.rotate_ccw_requested.connect(lambda: self._rotate_all(270))
        self.reader_toolbar.rotate_cw_requested.connect(lambda: self._rotate_all(90))
        self.reader_toolbar.search_requested.connect(self._show_search_bar)
        self.reader_toolbar.print_requested.connect(self._on_print)
        self.reader_toolbar.add_text_requested.connect(self._on_add_text_clicked)
        self.reader_toolbar.format_font_requested.connect(self._on_format_font_clicked)
        self.reader_toolbar.format_color_requested.connect(self._on_format_color_clicked)
        self.reader_toolbar.add_image_requested.connect(self._on_add_image_clicked)
        self.reader_toolbar.clean_signature_requested.connect(self._on_clean_signature_clicked)
        self.reader_toolbar.delete_selected_requested.connect(self._on_delete_selected_clicked)
        self.reader_toolbar.save_edits_requested.connect(self._on_embed_edits_clicked)
        self.reader_toolbar.add_form_text_requested.connect(self._on_add_form_text_field)
        self.reader_toolbar.add_form_checkbox_requested.connect(self._on_add_form_checkbox)
        layout.addWidget(self.reader_toolbar)

        # ── 3. Central Splitter: Left Tabs (Pages + Bookmarks) & Canvas ──
        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # Left Tab Widget
        self.sidebar_tabs = QTabWidget(self)
        self.sidebar_tabs.setFixedWidth(200)

        # Tab 1: Thumbnails
        self.thumb_list = QListWidget(self)
        self.thumb_list.setIconSize(QSize(120, 160))
        self.thumb_list.currentRowChanged.connect(self._on_thumb_selected)
        self.thumb_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.thumb_list.customContextMenuRequested.connect(self._on_thumb_context_menu)
        self.sidebar_tabs.addTab(self.thumb_list, "📑 Pages")

        # Tab 2: Bookmarks / Outline Tree
        self.toc_tree = QTreeWidget(self)
        self.toc_tree.setHeaderLabel("Outline")
        self.toc_tree.itemClicked.connect(self._on_toc_item_clicked)
        self.sidebar_tabs.addTab(self.toc_tree, "🔖 Outline")

        splitter.addWidget(self.sidebar_tabs)

        # Right Container with Canvas and Floating Search Bar
        canvas_container = QWidget(self)
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)

        self.canvas = PDFViewerCanvas(self)
        self.canvas.page_changed.connect(self._on_canvas_page_changed)
        self.canvas.zoom_changed.connect(self._on_canvas_zoom_changed)
        canvas_layout.addWidget(self.canvas)

        splitter.addWidget(canvas_container)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter, stretch=1)

        # Floating Search Bar positioned on top of the canvas
        self.search_bar = PDFSearchBar(self.canvas)
        self.search_bar.search_requested.connect(self._on_search_text)
        self.search_bar.next_match_requested.connect(self.canvas.next_search_match)
        self.search_bar.prev_match_requested.connect(self.canvas.prev_search_match)
        self.search_bar.closed.connect(self.canvas._clear_highlights)

        # Progress overlay (covers entire workspace)
        self._progress_overlay = ProgressOverlay(self)
        self._job_manager = JobManager()

        # Initially disable all document-dependent action buttons until a PDF is opened
        self._set_document_actions_enabled(False)

    def _set_document_actions_enabled(self, enabled: bool):
        """Grey out or enable action buttons based on whether a document is loaded."""
        self.save_btn.setEnabled(enabled)
        self.tools_btn.setEnabled(enabled)
        
        self.save_as_act.setEnabled(enabled)
        self.print_act.setEnabled(enabled)
        self.rot_tool_act.setEnabled(enabled)
        self.reorder_pages_act.setEnabled(enabled)
        self.delete_pages_act.setEnabled(enabled)
        self.export_img_act.setEnabled(enabled)
        self.compress_act.setEnabled(enabled)
        self.word_act.setEnabled(enabled)

    def _setup_shortcuts(self):
        """Acrobat standard keyboard shortcuts."""
        # Find: Ctrl+F
        sc_find = QShortcut(QKeySequence("Ctrl+F"), self)
        sc_find.activated.connect(self._show_search_bar)

        # Save: Ctrl+S
        sc_save = QShortcut(QKeySequence("Ctrl+S"), self)
        sc_save.activated.connect(self._on_save)

        # Save As: Ctrl+Shift+S
        sc_save_as = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        sc_save_as.activated.connect(self._on_save_as)

        # Print: Ctrl+P
        sc_print = QShortcut(QKeySequence("Ctrl+P"), self)
        sc_print.activated.connect(self._on_print)

        # Zoom in: Ctrl++ / Ctrl+=
        sc_zin = QShortcut(QKeySequence("Ctrl++"), self)
        sc_zin.activated.connect(self._on_zoom_in)
        sc_zin2 = QShortcut(QKeySequence("Ctrl+="), self)
        sc_zin2.activated.connect(self._on_zoom_in)

        # Zoom out: Ctrl+-
        sc_zout = QShortcut(QKeySequence("Ctrl+-"), self)
        sc_zout.activated.connect(self._on_zoom_out)

        # Fit Page: Ctrl+0
        sc_fpage = QShortcut(QKeySequence("Ctrl+0"), self)
        sc_fpage.activated.connect(self._on_fit_page)

        # Fit Width: Ctrl+1
        sc_fwidth = QShortcut(QKeySequence("Ctrl+1"), self)
        sc_fwidth.activated.connect(self._on_fit_width)

        # Next/Prev Page: PageDown / PageUp
        sc_pgdn = QShortcut(QKeySequence("Page_Down"), self)
        sc_pgdn.activated.connect(lambda: self.canvas.jump_to_page(self._current_page_idx + 1))
        sc_pgup = QShortcut(QKeySequence("Page_Up"), self)
        sc_pgup.activated.connect(lambda: self.canvas.jump_to_page(self._current_page_idx - 1))

    # ── Document Loading & TOC ──────────────────────────────────────────────

    def load_pdf(self, pdf_path: Path):
        meta_res = PDFService.inspect(pdf_path)
        if meta_res.is_err():
            QMessageBox.critical(self, "Error Loading PDF", meta_res.error.message)
            return

        meta = meta_res.value
        if self._original_pdf_path is None or not self._is_modified:
            self._original_pdf_path = pdf_path

        self._current_pdf_path = pdf_path
        self._page_count = meta.page_count
        status_mod = " *" if self._is_modified else ""
        self.page_lbl.setText(f"{self._original_pdf_path.name}{status_mod} ({self._page_count} pages)")

        # Update reader toolbar
        self.reader_toolbar.update_document_info(self._page_count, 0)
        self._set_document_actions_enabled(True)
        self.document_loaded.emit(True)

        # Populate thumbnails
        self.thumb_list.clear()
        for i in range(self._page_count):
            item = QListWidgetItem(f"Page {i + 1}")
            thumb_res = PDFRenderer.render_thumbnail_to_pixmap(pdf_path, i, max_size=120)
            if thumb_res.is_ok():
                item.setIcon(QIcon(thumb_res.value))
            self.thumb_list.addItem(item)

        # Populate Bookmarks / Table of Contents
        self._populate_toc(pdf_path)

        # Clear any unsaved overlays
        self.canvas.clear_overlay_items()
        self.reader_toolbar.save_edits_btn.setEnabled(False)

        # Render document pages into Acrobat canvas
        self.canvas.load_document(pdf_path, self._page_count)
        self.canvas.fit_width()

        if self._page_count > 0:
            self.thumb_list.setCurrentRow(0)

    def _populate_toc(self, pdf_path: Path):
        """Extract and display PDF Table of Contents / Outline."""
        self.toc_tree.clear()
        doc = None
        try:
            doc = fitz.open(str(pdf_path))
            toc = doc.get_toc()  # [[lvl, title, page, ...], ...]
            if not toc:
                item = QTreeWidgetItem(["No outline available"])
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.toc_tree.addTopLevelItem(item)
                return

            items_by_level = {0: self.toc_tree}
            for entry in toc:
                lvl, title, page = entry[0], entry[1], entry[2]
                tree_item = QTreeWidgetItem([title])
                tree_item.setData(0, Qt.ItemDataRole.UserRole, page - 1)  # 0-indexed

                parent = items_by_level.get(lvl - 1, self.toc_tree)
                if isinstance(parent, QTreeWidget):
                    parent.addTopLevelItem(tree_item)
                else:
                    parent.addChild(tree_item)
                items_by_level[lvl] = tree_item

            self.toc_tree.expandAll()
        except Exception as exc:
            print(f"Error reading TOC: {exc}")
        finally:
            if doc:
                doc.close()

    def _on_toc_item_clicked(self, item: QTreeWidgetItem, column: int):
        page_idx = item.data(0, Qt.ItemDataRole.UserRole)
        if page_idx is not None and 0 <= page_idx < self._page_count:
            self.canvas.jump_to_page(page_idx)

    # ── Page Synchronization ────────────────────────────────────────────────

    def _on_thumb_selected(self, row: int):
        if row >= 0 and row != self._current_page_idx:
            self.canvas.jump_to_page(row)

    def _on_canvas_page_changed(self, page_idx: int):
        """Synchronize reader toolbar and thumbnails when scrolling through canvas."""
        self._current_page_idx = page_idx
        self.reader_toolbar.set_current_page(page_idx)

        # Block signals to avoid feedback loop
        self.thumb_list.blockSignals(True)
        self.thumb_list.setCurrentRow(page_idx)
        self.thumb_list.blockSignals(False)

        status_mod = " *" if self._is_modified else ""
        name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
        self.page_lbl.setText(f"{name}{status_mod} (Page {page_idx + 1} of {self._page_count})")

    def _on_toolbar_page_jump(self, page_idx: int):
        self.canvas.jump_to_page(page_idx)

    # ── Zoom Handlers ───────────────────────────────────────────────────────

    def _on_zoom_in(self):
        self.canvas.zoom_in()

    def _on_zoom_out(self):
        self.canvas.zoom_out()

    def _on_fit_width(self):
        self.canvas.fit_width()

    def _on_fit_page(self):
        self.canvas.fit_page()

    def _on_zoom_preset(self, text: str):
        try:
            val = float(text.replace("%", "").strip()) / 100.0
            self.canvas.set_zoom(val)
        except ValueError:
            pass

    def _on_canvas_zoom_changed(self, factor: float):
        pct = int(round(factor * 100))
        self.reader_toolbar.set_zoom_text(f"{pct}%")

    def _on_continuous_toggled(self, continuous: bool):
        self.canvas.set_continuous_mode(continuous)

    # ── Search Handlers ─────────────────────────────────────────────────────

    def _show_search_bar(self):
        self.search_bar.show_bar()
        self._reposition_search_bar()

    def _reposition_search_bar(self):
        """Anchor search bar to top-right of canvas viewport."""
        cw = self.canvas.viewport().width()
        sb_w = self.search_bar.width() or 280
        self.search_bar.move(max(10, cw - sb_w - 20), 10)

    def _on_search_text(self, query: str):
        total_matches = self.canvas.search_text(query)
        current = 0 if total_matches > 0 else -1
        self.search_bar.set_match_status(current, total_matches)

    # ── Standard Actions ────────────────────────────────────────────────────

    def _on_open_pdf(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF Document", "", "PDF Files (*.pdf)")
        if file_path:
            self._is_modified = False
            self._original_pdf_path = Path(file_path)
            self.load_pdf(Path(file_path))

    def _on_save(self):
        """Save changes directly into the current PDF file."""
        if not self._current_pdf_path or not self._original_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        # If there are pending overlays, embed them first
        if self.canvas.has_pending_overlays():
            success = self._on_embed_edits_clicked()
            if not success:
                return

        # If the working copy is different from the original file (e.g. after rotate/delete),
        # we must overwrite the original to actually save the structural changes.
        if self._current_pdf_path.resolve() != self._original_pdf_path.resolve():
            import shutil
            shutil.copy2(self._current_pdf_path, self._original_pdf_path)
            self._current_pdf_path = self._original_pdf_path
            # Reload to point the canvas to the original file
            self.load_pdf(self._original_pdf_path)

        self._is_modified = False
        name = self._original_pdf_path.name
        self.page_lbl.setText(f"{name} (Page {self._current_page_idx + 1} of {self._page_count})")
        QMessageBox.information(self, "Saved", f"Document saved successfully:\n{self._original_pdf_path.name}")

    def _on_save_as(self):
        if not self._current_pdf_path or not self._original_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        # If there are pending overlays, embed them into the working copy first!
        if self.canvas.has_pending_overlays():
            success = self._on_embed_edits_clicked()
            if not success:
                return

        default_name = f"{self._original_pdf_path.stem}_edited.pdf"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF As",
            default_name,
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        import shutil
        target = Path(save_path)
        shutil.copy2(self._current_pdf_path, target)
        self._is_modified = False
        self._original_pdf_path = target
        self._current_pdf_path = target
        self.load_pdf(target)
        QMessageBox.information(self, "Saved", f"Document saved successfully to:\n{target.name}")

    def _open_rotate_dialog(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        from offline_toolbox.filesystem.temporary import TempFileManager
        from offline_toolbox.ui.pdf.rotate_dialog import RotatePagesDialog

        dlg = RotatePagesDialog(
            total_pages=self._page_count,
            current_page_index=self._current_page_idx,
            parent=self,
        )

        if dlg.exec():
            delta = dlg.get_rotation_delta()
            target_indices = dlg.get_target_page_indices()

            temp_mgr = TempFileManager()
            run_dir = temp_mgr.create_run_directory("session_rot_")
            temp_target = temp_mgr.create_temp_file(run_dir, ".pdf")

            from offline_toolbox.pdf.pages import rotate_pages
            res = rotate_pages(
                source_path=self._current_pdf_path,
                target_path=temp_target,
                rotation_delta=delta,
                page_indices=target_indices,
            )

            if res.is_ok():
                self._is_modified = True
                self.load_pdf(res.value)
            else:
                QMessageBox.critical(self, "Rotation Failed", res.error.message)

    def _open_export_images_dialog(self):
        if not self._current_pdf_path or self._page_count == 0:
            return

        from offline_toolbox.ui.pdf.page_ops_dialogs import ExportPdfImagesDialog
        dlg = ExportPdfImagesDialog(
            total_pages=self._page_count,
            current_page_index=self._current_page_idx,
            default_output_dir=self._current_pdf_path.parent,
            parent=self,
        )

        if dlg.exec():
            fmt = dlg.get_target_format()
            dpi = dlg.get_dpi()
            out_dir = dlg.get_output_directory()
            target_indices = dlg.get_target_page_indices()

            self._progress_overlay.show_progress("Exporting PDF pages to images…")
            try:
                res = PDFService.to_images(
                    source_path=self._current_pdf_path,
                    output_directory=out_dir,
                    target_format=fmt,
                    dpi=dpi,
                    page_indices=target_indices,
                )
                self._progress_overlay.hide_progress()
                if res.is_ok():
                    files = res.value
                    msg = f"Successfully exported {len(files)} page image(s) to:\n{out_dir}\n\nFiles:\n"
                    msg += "\n".join(f.name for f in files[:5])
                    if len(files) > 5:
                        msg += f"\n… and {len(files) - 5} more."
                    QMessageBox.information(self, "Images Exported", msg)
                else:
                    QMessageBox.critical(self, "Export Failed", res.error.message)
            except Exception as e:
                self._progress_overlay.hide_progress()
                QMessageBox.critical(self, "Export Error", str(e))

    def _open_delete_dialog(self, preselected_page: Optional[int] = None):
        if not self._current_pdf_path or self._page_count <= 1:
            QMessageBox.information(
                self,
                "Cannot Delete",
                "The PDF must contain at least 2 pages before any page can be deleted.",
            )
            return

        from offline_toolbox.ui.pdf.page_ops_dialogs import DeletePagesDialog
        cur_p = preselected_page if preselected_page is not None else self._current_page_idx
        dlg = DeletePagesDialog(total_pages=self._page_count, current_page_index=cur_p, parent=self)

        if dlg.exec():
            remaining_indices = dlg.get_remaining_page_indices()
            if not remaining_indices:
                return

            from offline_toolbox.filesystem.temporary import TempFileManager
            from offline_toolbox.pdf.pages import reorder_and_delete_pages

            temp_mgr = TempFileManager()
            run_dir = temp_mgr.create_run_directory("session_delete_")
            temp_target = temp_mgr.create_temp_file(run_dir, ".pdf")

            res = reorder_and_delete_pages(
                source_path=self._current_pdf_path,
                target_path=temp_target,
                ordered_page_indices=remaining_indices,
            )
            if res.is_ok():
                self._is_modified = True
                self.load_pdf(res.value)
                QMessageBox.information(
                    self,
                    "Pages Deleted",
                    f"Selected pages deleted successfully.\nDocument now has {len(remaining_indices)} page(s).",
                )
            else:
                QMessageBox.critical(self, "Delete Failed", res.error.message)

    def _open_reorder_dialog(self, preselected_page: Optional[int] = None):
        if not self._current_pdf_path or self._page_count <= 1:
            QMessageBox.information(
                self,
                "Cannot Rearrange",
                "The document needs at least 2 pages to be rearranged.",
            )
            return

        from offline_toolbox.ui.pdf.page_ops_dialogs import ReorderPagesDialog
        cur_p = preselected_page if preselected_page is not None else self._current_page_idx
        dlg = ReorderPagesDialog(total_pages=self._page_count, current_page_index=cur_p, parent=self)

        if dlg.exec():
            new_order = dlg.get_ordered_page_indices()
            if new_order == list(range(self._page_count)):
                return  # No change

            from offline_toolbox.filesystem.temporary import TempFileManager
            from offline_toolbox.pdf.pages import reorder_and_delete_pages

            temp_mgr = TempFileManager()
            run_dir = temp_mgr.create_run_directory("session_reorder_")
            temp_target = temp_mgr.create_temp_file(run_dir, ".pdf")

            res = reorder_and_delete_pages(
                source_path=self._current_pdf_path,
                target_path=temp_target,
                ordered_page_indices=new_order,
            )
            if res.is_ok():
                self._is_modified = True
                self.load_pdf(res.value)
                QMessageBox.information(
                    self,
                    "Pages Rearranged",
                    "PDF pages were rearranged successfully.",
                )
            else:
                QMessageBox.critical(self, "Rearrange Failed", res.error.message)

    def _on_thumb_context_menu(self, pos):
        item = self.thumb_list.itemAt(pos)
        if not item or not self._current_pdf_path:
            return

        row = self.thumb_list.row(item)
        menu = QMenu(self)

        act_goto = menu.addAction(f"📄 Jump to Page {row + 1}")
        act_goto.triggered.connect(lambda: self.canvas.jump_to_page(row))

        menu.addSeparator()

        act_reorder = menu.addAction(f"🔀 Move / Rearrange Page {row + 1}…")
        act_reorder.triggered.connect(lambda: self._open_reorder_dialog(preselected_page=row))

        act_delete = menu.addAction(f"🗑️ Delete Page {row + 1}…")
        act_delete.triggered.connect(lambda: self._open_delete_dialog(preselected_page=row))

        menu.addSeparator()

        act_export = menu.addAction(f"🖼️ Export Page {row + 1} as JPEG…")
        act_export.triggered.connect(lambda: self._export_single_page_jpeg(row))

        menu.exec(self.thumb_list.viewport().mapToGlobal(pos))

    def _export_single_page_jpeg(self, page_idx: int):
        if not self._current_pdf_path:
            return
        out_dir = self._current_pdf_path.parent
        from offline_toolbox.core.models import ImageFormat
        res = PDFService.to_images(
            source_path=self._current_pdf_path,
            output_directory=out_dir,
            target_format=ImageFormat.JPEG,
            dpi=150,
            page_indices=[page_idx],
        )
        if res.is_ok():
            QMessageBox.information(
                self,
                "Export Complete",
                f"Page {page_idx + 1} exported to JPEG:\n{res.value[0].name}",
            )
        else:
            QMessageBox.critical(self, "Export Failed", res.error.message)

    def _rotate_all(self, delta: int = 90):
        if not self._current_pdf_path:
            return

        from offline_toolbox.filesystem.temporary import TempFileManager
        from offline_toolbox.pdf.pages import rotate_pages

        temp_mgr = TempFileManager()
        run_dir = temp_mgr.create_run_directory("session_rot_all_")
        temp_target = temp_mgr.create_temp_file(run_dir, ".pdf")

        res = rotate_pages(
            source_path=self._current_pdf_path,
            target_path=temp_target,
            rotation_delta=delta,
            page_indices=None,
        )
        if res.is_ok():
            self._is_modified = True
            self.load_pdf(res.value)
        else:
            QMessageBox.critical(self, "Rotation Failed", res.error.message)

    def _compress_current(self):
        if not self._current_pdf_path:
            return
        res = PDFService.compress(self._current_pdf_path, CompressionPreset.BALANCED)
        if res.is_ok():
            orig_size = self._current_pdf_path.stat().st_size
            new_size = res.value.stat().st_size
            pct = max(0.0, (1.0 - (new_size / orig_size)) * 100)
            QMessageBox.information(
                self,
                "Compression Complete",
                f"Saved to: {res.value.name}\nSize reduced by {pct:.1f}% ({orig_size // 1024} KB → {new_size // 1024} KB)",
            )
            self.load_pdf(res.value)
        else:
            QMessageBox.critical(self, "Compression Failed", res.error.message)

    # ── Document Printing (QPrinter & QPrintDialog) ──────────────────────────

    def _on_print(self):
        if not self._current_pdf_path or self._page_count == 0:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first before printing.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setDocName(self._current_pdf_path.stem)

        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle(f"Print — {self._current_pdf_path.name}")
        dlg.setMinMax(1, self._page_count)
        dlg.setOption(QPrintDialog.PrintDialogOption.PrintSelection, False)
        dlg.setOption(QPrintDialog.PrintDialogOption.PrintCurrentPage, True)
        dlg.setOption(QPrintDialog.PrintDialogOption.PrintPageRange, True)

        if not dlg.exec():
            return

        # Determine target pages from dialog selection
        print_range = printer.printRange()
        if print_range == QPrinter.PrintRange.CurrentPage:
            pages_to_print = [self._current_page_idx]
        elif print_range == QPrinter.PrintRange.PageRange:
            from_p = max(0, printer.fromPage() - 1)
            to_p = min(self._page_count - 1, printer.toPage() - 1)
            pages_to_print = list(range(from_p, to_p + 1))
        else:
            pages_to_print = list(range(self._page_count))

        if not pages_to_print:
            QMessageBox.warning(self, "Print Warning", "No valid pages selected to print.")
            return

        # Execute high-resolution print job
        self._progress_overlay.show_progress("Printing document…")
        doc = None
        try:
            painter = QPainter(printer)
            page_rect = printer.pageLayout().paintRectPixels(printer.resolution())
            doc = fitz.open(str(self._current_pdf_path))

            for i, p_idx in enumerate(pages_to_print):
                self._progress_overlay.update_progress(
                    (i + 1) / len(pages_to_print),
                    f"Printing page {p_idx + 1} of {self._page_count}…"
                )
                if i > 0:
                    printer.newPage()

                page = doc[p_idx]
                # Render at 300 DPI for crisp physical printout
                pix = page.get_pixmap(dpi=300, alpha=False)
                qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)

                # Scale to fit paper printable area while preserving aspect ratio
                scaled = qimg.scaled(
                    page_rect.width(),
                    page_rect.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                # Center on paper sheet
                x_off = page_rect.x() + (page_rect.width() - scaled.width()) / 2
                y_off = page_rect.y() + (page_rect.height() - scaled.height()) / 2
                painter.drawImage(int(x_off), int(y_off), scaled)

            painter.end()
            self._progress_overlay.hide_progress()
            p_name = printer.printerName() or "Printer"
            QMessageBox.information(
                self,
                "Printing Complete",
                f"Successfully sent {len(pages_to_print)} page(s) to '{p_name}'.",
            )
        except Exception as exc:
            self._progress_overlay.hide_progress()
            QMessageBox.critical(self, "Printing Error", f"Failed to complete print job:\n{exc}")
        finally:
            if doc:
                doc.close()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._progress_overlay.resize(self.size())
        if self.search_bar.isVisible():
            self._reposition_search_bar()

    # ── Word Conversion (Background Thread) ─────────────────────────────────

    def _convert_to_word(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Word Document",
            f"{self._current_pdf_path.stem}.docx",
            "Word Document (*.docx)",
        )
        if not save_path:
            return

        self.word_btn.setEnabled(False)
        self._progress_overlay.show_progress("Converting PDF to Word…")

        target_path = Path(save_path)
        source_path = self._current_pdf_path
        job_id = f"pdf2word_{uuid.uuid4().hex[:8]}"

        def _run_conversion():
            def _on_prog(curr, total, msg):
                frac = curr / max(1, total)
                worker.report_progress(frac, msg)

            return PDFService.to_word(
                source_path=source_path,
                output_path=target_path,
                enable_ocr_fallback=True,
                progress_callback=_on_prog,
            )

        worker = self._job_manager.submit_job(job_id, _run_conversion)
        worker.signals.progress.connect(self._on_word_progress)
        worker.signals.finished.connect(self._on_word_done)
        worker.signals.error.connect(self._on_word_error)

    def _on_word_progress(self, job_id: str, progress: float, message: str):
        self._progress_overlay.update_progress(progress, message)

    def _on_word_done(self, job_id: str, result):
        self._progress_overlay.hide_progress()
        self.word_btn.setEnabled(True)

        if result.is_ok():
            QMessageBox.information(
                self,
                "Conversion Complete",
                f"Successfully converted to Word document:\n{result.value.name}",
            )
        else:
            QMessageBox.critical(self, "Conversion Failed", result.error.message)

    def _on_word_error(self, job_id: str, error_msg: str):
        self._progress_overlay.hide_progress()
        self.word_btn.setEnabled(True)
        QMessageBox.critical(self, "Conversion Failed", f"An unexpected error occurred:\n{error_msg}")

    # ── PDF In-Place Overlay Handlers (Text & Image) ─────────────────────────

    def _on_add_text_clicked(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        item = self.canvas.add_text_overlay(self._current_page_idx)
        if item:
            self.reader_toolbar.save_edits_btn.setEnabled(True)
            self._is_modified = True
            name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
            self.page_lbl.setText(f"{name} * (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_add_image_clicked(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        img_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image to Overlap / Stamp",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;PNG Files with Transparency (*.png);;All Files (*.*)",
        )
        if not img_file:
            return

        item = self.canvas.add_image_overlay(self._current_page_idx, Path(img_file))
        if item:
            self.reader_toolbar.save_edits_btn.setEnabled(True)
            self._is_modified = True
            name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
            self.page_lbl.setText(f"{name} * (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_clean_signature_clicked(self):
        """Extract signature or handwritten name photo, strip white paper with Curves (Ctrl+M), and overlay."""
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return

        # Check if an existing image overlay is already selected
        selected_imgs = [item for item in self.canvas._scene.selectedItems() if isinstance(item, ResizableImageOverlayItem)]
        if selected_imgs:
            target_item = selected_imgs[0]
            from offline_toolbox.ui.pdf.signature_dialog import SignatureCleanDialog
            dlg = SignatureCleanDialog(target_item.image_path, parent=self)
            if dlg.exec():
                cleaned_path = dlg.get_cleaned_image_path()
                if cleaned_path and cleaned_path.exists():
                    target_item.update_image_source(cleaned_path)
                    self.reader_toolbar.save_edits_btn.setEnabled(True)
                    self._is_modified = True
            return

        # Otherwise pick a photo from disk
        img_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select Signature or Handwritten Name Photo",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.webp);;All Files (*.*)",
        )
        if not img_file:
            return

        from offline_toolbox.ui.pdf.signature_dialog import SignatureCleanDialog
        dlg = SignatureCleanDialog(Path(img_file), parent=self)
        if dlg.exec():
            cleaned_path = dlg.get_cleaned_image_path()
            if cleaned_path and cleaned_path.exists():
                item = self.canvas.add_image_overlay(self._current_page_idx, cleaned_path)
                if item:
                    self.reader_toolbar.save_edits_btn.setEnabled(True)
                    self._is_modified = True
                    name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
                    self.page_lbl.setText(f"{name} * (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_add_form_text_field(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return
        import fitz
        item = self.canvas.add_acroform_overlay(self._current_page_idx, fitz.PDF_WIDGET_TYPE_TEXT)
        if item:
            self.reader_toolbar.save_edits_btn.setEnabled(True)
            self._is_modified = True
            name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
            self.page_lbl.setText(f"{name} * (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_add_form_checkbox(self):
        if not self._current_pdf_path:
            QMessageBox.warning(self, "No Document", "Please load a PDF document first.")
            return
        import fitz
        item = self.canvas.add_acroform_overlay(self._current_page_idx, fitz.PDF_WIDGET_TYPE_CHECKBOX)
        if item:
            self.reader_toolbar.save_edits_btn.setEnabled(True)
            self._is_modified = True
            name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
            self.page_lbl.setText(f"{name} * (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_format_font_clicked(self):
        """Change font, size, bold, italic, and underline of selected text overlay, or all text overlays."""
        selected_items = [item for item in self.canvas._scene.selectedItems() if isinstance(item, EditableTextOverlayItem)]
        target_items = selected_items if selected_items else [item for item in self.canvas._overlay_items if isinstance(item, EditableTextOverlayItem)]

        if not target_items:
            QMessageBox.information(self, "No Text Box", "Please add or select a text box first to change its font.")
            return

        first = target_items[0]
        curr_font = first.font()
        from PySide6.QtWidgets import QFontDialog
        ok, selected_font = QFontDialog.getFont(curr_font, self, "Select Font from Operating System")
        if ok:
            for item in target_items:
                item.set_font_family(selected_font.family())
                item.set_font_size(float(selected_font.pointSize() if selected_font.pointSize() > 0 else 12))
                item.set_bold(selected_font.bold())
                item.set_italic(selected_font.italic())
                item.set_underline(selected_font.underline())

    def _on_format_color_clicked(self):
        """Change color of selected text overlay, or all text overlays."""
        selected_items = [item for item in self.canvas._scene.selectedItems() if isinstance(item, EditableTextOverlayItem)]
        target_items = selected_items if selected_items else [item for item in self.canvas._overlay_items if isinstance(item, EditableTextOverlayItem)]

        if not target_items:
            QMessageBox.information(self, "No Text Box", "Please add or select a text box first to change its color.")
            return

        first = target_items[0]
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(first.get_text_color(), self, "Select Text Color")
        if c.isValid():
            for item in target_items:
                item.set_text_color(c)

    def _on_delete_selected_clicked(self):
        """Remove currently selected text box(es) or image(s) from canvas."""
        selected_items = list(self.canvas._scene.selectedItems())
        to_delete = [item for item in selected_items if item in self.canvas._overlay_items]
        if not to_delete and self.canvas._overlay_items:
            # If nothing selected but only 1 overlay item exists, delete that one
            if len(self.canvas._overlay_items) == 1:
                to_delete = [self.canvas._overlay_items[0]]

        if not to_delete:
            QMessageBox.information(self, "No Selection", "Please click on a text box or image first to delete it.")
            return

        for item in to_delete:
            self.canvas._remove_overlay_item(item)

        # Update button state
        has_pending = self.canvas.has_pending_overlays()
        self.reader_toolbar.save_edits_btn.setEnabled(has_pending)
        if not has_pending:
            name = self._original_pdf_path.name if self._original_pdf_path else self._current_pdf_path.name
            self.page_lbl.setText(f"{name} (Page {self._current_page_idx + 1} of {self._page_count})")

    def _on_embed_edits_clicked(self) -> bool:
        """Bake / embed all text and image overlays directly into the PDF in-place. Returns True if successful."""
        if not self._current_pdf_path:
            return False

        text_overlays, image_overlays, acroform_overlays = self.canvas.get_pending_overlays()
        if not text_overlays and not image_overlays and not acroform_overlays:
            QMessageBox.information(self, "No Overlays", "No pending text, image, or form overlays to embed.")
            return True

        self._progress_overlay.show_progress("Embedding edits into PDF…")
        try:
            # Embed in-place into the current document
            res = PDFService.apply_overlays(
                source_path=self._current_pdf_path,
                target_path=self._current_pdf_path,
                text_overlays=text_overlays,
                image_overlays=image_overlays,
                acroform_overlays=acroform_overlays,
            )
            self._progress_overlay.hide_progress()

            if res.is_ok():
                self._is_modified = True
                self.canvas.clear_overlay_items()
                self.reader_toolbar.save_edits_btn.setEnabled(False)
                # Reload document to display baked changes
                self.load_pdf(self._current_pdf_path)
                QMessageBox.information(
                    self,
                    "Edits Embedded",
                    "Text and image overlays have been successfully baked directly into the PDF document.",
                )
                return True
            else:
                QMessageBox.critical(self, "Failed to Embed Edits", res.error.message)
                return False

        except Exception as exc:
            self._progress_overlay.hide_progress()
            QMessageBox.critical(self, "Error", f"Could not embed edits: {exc}")
            return False

