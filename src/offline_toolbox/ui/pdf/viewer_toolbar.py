"""Adobe Acrobat-style Reader Toolbar for PDF navigation, zooming, and view modes."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class PDFViewerToolbar(QFrame):
    """
    Floating or docked Acrobat-style reader toolbar with page controls, zoom, and tools.
    """

    # Signals
    page_changed = Signal(int)             # 0-indexed page requested
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    zoom_preset_selected = Signal(str)     # "50%", "100%", "Fit Width", etc.
    fit_width_requested = Signal()
    fit_page_requested = Signal()
    toggle_continuous_requested = Signal(bool)  # True = continuous, False = single
    search_requested = Signal()
    print_requested = Signal()
    rotate_ccw_requested = Signal()
    rotate_cw_requested = Signal()
    add_text_requested = Signal()
    add_image_requested = Signal()
    clean_signature_requested = Signal()
    save_edits_requested = Signal()
    delete_selected_requested = Signal()
    format_font_requested = Signal()
    format_color_requested = Signal()
    
    add_form_text_requested = Signal()
    add_form_checkbox_requested = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("pdfViewerToolbar")
        self._total_pages: int = 0
        self._current_page: int = 0
        self._init_ui()
        self.set_document_loaded(False)

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        # ── Page Navigation ──
        self.prev_btn = QPushButton("◀", self)
        self.prev_btn.setToolTip("Previous Page (PageUp or Left Arrow)")
        self.prev_btn.setProperty("class", "toolIconBtn")
        self.prev_btn.setFixedSize(28, 28)
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        layout.addWidget(self.prev_btn)

        self.page_input = QLineEdit(self)
        self.page_input.setFixedWidth(42)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.setToolTip("Type page number and press Enter")
        self.page_input.returnPressed.connect(self._on_page_input_entered)
        layout.addWidget(self.page_input)

        self.page_total_lbl = QLabel("/ 0", self)
        self.page_total_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")
        layout.addWidget(self.page_total_lbl)

        self.next_btn = QPushButton("▶", self)
        self.next_btn.setToolTip("Next Page (PageDown or Right Arrow)")
        self.next_btn.setProperty("class", "toolIconBtn")
        self.next_btn.setFixedSize(28, 28)
        self.next_btn.clicked.connect(self._on_next_clicked)
        layout.addWidget(self.next_btn)

        layout.addWidget(self._make_divider())

        # ── Zoom Controls ──
        self.zoom_out_btn = QPushButton("−", self)
        self.zoom_out_btn.setToolTip("Zoom Out (Ctrl + −)")
        self.zoom_out_btn.setProperty("class", "toolIconBtn")
        self.zoom_out_btn.setFixedSize(28, 28)
        self.zoom_out_btn.clicked.connect(self.zoom_out_requested.emit)
        layout.addWidget(self.zoom_out_btn)

        self.zoom_combo = QComboBox(self)
        self.zoom_combo.setFixedWidth(95)
        self.zoom_combo.setToolTip("Select Zoom Level")
        self.zoom_combo.addItems([
            "Fit Width",
            "Fit Page",
            "50%",
            "75%",
            "100%",
            "125%",
            "150%",
            "200%",
            "300%",
            "400%",
        ])
        self.zoom_combo.setCurrentText("Fit Width")
        self.zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        layout.addWidget(self.zoom_combo)

        self.zoom_in_btn = QPushButton("+", self)
        self.zoom_in_btn.setToolTip("Zoom In (Ctrl + +)")
        self.zoom_in_btn.setProperty("class", "toolIconBtn")
        self.zoom_in_btn.setFixedSize(28, 28)
        self.zoom_in_btn.clicked.connect(self.zoom_in_requested.emit)
        layout.addWidget(self.zoom_in_btn)

        self.fit_width_btn = QPushButton("↔", self)
        self.fit_width_btn.setToolTip("Fit to Page Width")
        self.fit_width_btn.setProperty("class", "toolIconBtn")
        self.fit_width_btn.setFixedSize(28, 28)
        self.fit_width_btn.clicked.connect(self.fit_width_requested.emit)
        layout.addWidget(self.fit_width_btn)

        self.fit_page_btn = QPushButton("↕", self)
        self.fit_page_btn.setToolTip("Fit Entire Page in View")
        self.fit_page_btn.setProperty("class", "toolIconBtn")
        self.fit_page_btn.setFixedSize(28, 28)
        self.fit_page_btn.clicked.connect(self.fit_page_requested.emit)
        layout.addWidget(self.fit_page_btn)

        layout.addWidget(self._make_divider())

        # ── View Layout Mode (Continuous Scroll vs Single Page) ──
        self.continuous_btn = QPushButton("📜", self)
        self.continuous_btn.setToolTip("Toggle Continuous Vertical Scrolling")
        self.continuous_btn.setCheckable(True)
        self.continuous_btn.setChecked(True)
        self.continuous_btn.setProperty("class", "toolIconBtn")
        self.continuous_btn.setFixedSize(28, 28)
        self.continuous_btn.toggled.connect(self._on_continuous_toggled)
        layout.addWidget(self.continuous_btn)

        layout.addWidget(self._make_divider())

        # ── Quick Tools (Search & Rotation) ──
        self.rot_ccw_btn = QPushButton("↺", self)
        self.rot_ccw_btn.setToolTip("Rotate View 90° Counter-Clockwise")
        self.rot_ccw_btn.setProperty("class", "toolIconBtn")
        self.rot_ccw_btn.setFixedSize(28, 28)
        self.rot_ccw_btn.clicked.connect(self.rotate_ccw_requested.emit)
        layout.addWidget(self.rot_ccw_btn)

        self.rot_cw_btn = QPushButton("↻", self)
        self.rot_cw_btn.setToolTip("Rotate View 90° Clockwise")
        self.rot_cw_btn.setProperty("class", "toolIconBtn")
        self.rot_cw_btn.setFixedSize(28, 28)
        self.rot_cw_btn.clicked.connect(self.rotate_cw_requested.emit)
        layout.addWidget(self.rot_cw_btn)

        self.search_btn = QPushButton("🔍", self)
        self.search_btn.setToolTip("Find in Document (Ctrl + F)")
        self.search_btn.setProperty("class", "toolIconBtn")
        self.search_btn.setFixedSize(28, 28)
        self.search_btn.clicked.connect(self.search_requested.emit)
        layout.addWidget(self.search_btn)

        self.print_btn = QPushButton("🖨️", self)
        self.print_btn.setToolTip("Print Document (Ctrl + P)")
        self.print_btn.setProperty("class", "toolIconBtn")
        self.print_btn.setFixedSize(28, 28)
        self.print_btn.clicked.connect(self.print_requested.emit)
        layout.addWidget(self.print_btn)

        layout.addWidget(self._make_divider())

        # ── Edit PDF Tools (In-Place Text & Image Overlays) ──
        self.add_text_btn = QPushButton("✏️", self)
        self.add_text_btn.setToolTip("Add editable text box onto current page")
        self.add_text_btn.setProperty("class", "toolIconBtn")
        self.add_text_btn.setFixedSize(28, 28)
        self.add_text_btn.clicked.connect(self.add_text_requested.emit)
        layout.addWidget(self.add_text_btn)

        self.font_btn = QPushButton("🔤", self)
        self.font_btn.setToolTip("Select system font, size, and style (Bold, Italic, Underline)")
        self.font_btn.setProperty("class", "toolIconBtn")
        self.font_btn.setFixedSize(28, 28)
        self.font_btn.clicked.connect(self.format_font_requested.emit)
        layout.addWidget(self.font_btn)

        self.color_btn = QPushButton("🎨", self)
        self.color_btn.setToolTip("Select text color")
        self.color_btn.setProperty("class", "toolIconBtn")
        self.color_btn.setFixedSize(28, 28)
        self.color_btn.clicked.connect(self.format_color_requested.emit)
        layout.addWidget(self.color_btn)
        
        self.add_form_txt_btn = QPushButton("🔲", self)
        self.add_form_txt_btn.setToolTip("Add Acroform Text Field")
        self.add_form_txt_btn.setProperty("class", "toolIconBtn")
        self.add_form_txt_btn.setFixedSize(28, 28)
        self.add_form_txt_btn.clicked.connect(self.add_form_text_requested.emit)
        layout.addWidget(self.add_form_txt_btn)

        self.add_form_chk_btn = QPushButton("☑️", self)
        self.add_form_chk_btn.setToolTip("Add Acroform Checkbox")
        self.add_form_chk_btn.setProperty("class", "toolIconBtn")
        self.add_form_chk_btn.setFixedSize(28, 28)
        self.add_form_chk_btn.clicked.connect(self.add_form_checkbox_requested.emit)
        layout.addWidget(self.add_form_chk_btn)

        self.add_img_btn = QPushButton("🖼️", self)
        self.add_img_btn.setToolTip("Add / overlap image, signature, stamp, or logo (drag corners to resize)")
        self.add_img_btn.setProperty("class", "toolIconBtn")
        self.add_img_btn.setFixedSize(28, 28)
        self.add_img_btn.clicked.connect(self.add_image_requested.emit)
        layout.addWidget(self.add_img_btn)

        self.clean_sig_btn = QPushButton("🖋️", self)
        self.clean_sig_btn.setToolTip("Extract signature or handwritten text (Ctrl+M Curves & Multiply paper removal)")
        self.clean_sig_btn.setProperty("class", "toolIconBtn")
        self.clean_sig_btn.setFixedSize(28, 28)
        self.clean_sig_btn.clicked.connect(self.clean_signature_requested.emit)
        layout.addWidget(self.clean_sig_btn)
        
        self.delete_btn = QPushButton("🗑️", self)
        self.delete_btn.setToolTip("Delete selected item (or press Delete key)")
        self.delete_btn.setProperty("class", "toolIconBtn")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(self.delete_selected_requested.emit)
        layout.addWidget(self.delete_btn)

        self.save_edits_btn = QPushButton("💾 Embed Edits", self)
        self.save_edits_btn.setToolTip("Bake / embed all text and image overlays directly into the PDF")
        self.save_edits_btn.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; border-radius: 4px; padding: 4px 8px;")
        self.save_edits_btn.clicked.connect(self.save_edits_requested.emit)
        self.save_edits_btn.setEnabled(False)
        layout.addWidget(self.save_edits_btn)

        layout.addStretch(1)

    def _make_divider(self) -> QFrame:
        div = QFrame(self)
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFrameShadow(QFrame.Shadow.Sunken)
        div.setStyleSheet("color: #475569; margin: 4px 2px;")
        return div

    # ── Public API ──

    def set_document_loaded(self, loaded: bool):
        """Enable or grey out toolbar controls depending on whether a PDF is loaded."""
        self.page_input.setEnabled(loaded)
        self.prev_btn.setEnabled(loaded and self._current_page > 0)
        self.next_btn.setEnabled(loaded and self._current_page < self._total_pages - 1)

        self.zoom_out_btn.setEnabled(loaded)
        self.zoom_combo.setEnabled(loaded)
        self.zoom_in_btn.setEnabled(loaded)
        self.fit_width_btn.setEnabled(loaded)
        self.fit_page_btn.setEnabled(loaded)
        self.continuous_btn.setEnabled(loaded)

        self.rot_ccw_btn.setEnabled(loaded)
        self.rot_cw_btn.setEnabled(loaded)
        self.search_btn.setEnabled(loaded)
        self.print_btn.setEnabled(loaded)

        self.add_text_btn.setEnabled(loaded)
        self.font_btn.setEnabled(loaded)
        self.color_btn.setEnabled(loaded)
        self.delete_btn.setEnabled(loaded)
        self.add_img_btn.setEnabled(loaded)
        self.clean_sig_btn.setEnabled(loaded)
        self.add_form_txt_btn.setEnabled(loaded)
        self.add_form_chk_btn.setEnabled(loaded)

        if not loaded:
            self.save_edits_btn.setEnabled(False)

    def update_document_info(self, total_pages: int, current_page: int = 0):
        self._total_pages = total_pages
        self._current_page = current_page
        self.page_total_lbl.setText(f"/ {total_pages}")
        self.page_input.setText(str(current_page + 1) if total_pages > 0 else "0")
        self.set_document_loaded(total_pages > 0)

    def set_current_page(self, page_idx: int):
        self._current_page = page_idx
        self.page_input.setText(str(page_idx + 1))
        self._update_nav_buttons()

    def set_zoom_text(self, text: str):
        # Update combo text without firing signal
        self.zoom_combo.blockSignals(True)
        self.zoom_combo.setCurrentText(text)
        self.zoom_combo.blockSignals(False)

    # ── Handlers ──

    def _update_nav_buttons(self):
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(self._current_page < self._total_pages - 1)

    def _on_prev_clicked(self):
        if self._current_page > 0:
            self.page_changed.emit(self._current_page - 1)

    def _on_next_clicked(self):
        if self._current_page < self._total_pages - 1:
            self.page_changed.emit(self._current_page + 1)

    def _on_page_input_entered(self):
        txt = self.page_input.text().strip()
        if txt.isdigit():
            val = int(txt) - 1
            if 0 <= val < self._total_pages:
                self.page_changed.emit(val)
                return
        # Reset if invalid
        self.page_input.setText(str(self._current_page + 1))

    def _on_zoom_changed(self, text: str):
        if text == "Fit Width":
            self.fit_width_requested.emit()
        elif text == "Fit Page":
            self.fit_page_requested.emit()
        else:
            self.zoom_preset_selected.emit(text)

    def _on_continuous_toggled(self, checked: bool):
        self.continuous_btn.setText("📜" if checked else "📄")
        self.toggle_continuous_requested.emit(checked)
