"""Primary Desktop Application Window with navigation sidebar, theme switching, and logo integration."""

from pathlib import Path
from typing import List
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QIcon, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from offline_toolbox.core.models import CompressionPreset
from offline_toolbox.core.paths import get_resource_path
from offline_toolbox.pdf.service import PDFService
from offline_toolbox.ui.home.home_view import HomeView
from offline_toolbox.ui.images.image_editor_workspace import ImageEditorWorkspace
from offline_toolbox.ui.images.image_workspace import ImageWorkspace
from offline_toolbox.ui.pdf.pdf_workspace import PDFWorkspace
from offline_toolbox.ui.themes import DARK_THEME, LIGHT_THEME


class MainWindow(QMainWindow):
    """Production desktop main window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Offline Toolbox — 100% Local & Private")
        self.resize(1200, 800)
        self.setMinimumSize(960, 640)
        self.setAcceptDrops(True)

        self._is_dark_mode = True
        self._icon_path = get_resource_path("icons", "app_logo_64.png")
        self._ico_path = get_resource_path("icons", "app_logo.ico")

        if self._ico_path.exists():
            self.setWindowIcon(QIcon(str(self._ico_path)))
        elif self._icon_path.exists():
            self.setWindowIcon(QIcon(str(self._icon_path)))

        self._apply_theme()
        self._init_ui()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """Register global window shortcuts (e.g. F11 fullscreen toggle)."""
        self._fs_shortcut = QShortcut(QKeySequence("F11"), self)
        self._fs_shortcut.activated.connect(self._toggle_fullscreen)

        self._esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._esc_shortcut.activated.connect(self._exit_fullscreen)

        self._print_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        self._print_shortcut.activated.connect(self._handle_global_print)

    def _handle_global_print(self):
        if hasattr(self, "pdf_workspace"):
            self.pdf_workspace._on_print()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()

    def _apply_theme(self):
        if self._is_dark_mode:
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)

    def _toggle_theme(self):
        self._is_dark_mode = not self._is_dark_mode
        self._apply_theme()
        btn_text = "☀️  Light Mode" if self._is_dark_mode else "🌙  Dark Mode"
        self.theme_btn.setText(btn_text)

    def _init_ui(self):
        central_widget = QWidget(self)
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Navigation Sidebar
        sidebar = QFrame(self)
        sidebar.setObjectName("sidebarFrame")
        sidebar.setFixedWidth(230)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(12)

        # App Brand Header with Logo
        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(10)

        if self._icon_path.exists():
            logo_lbl = QLabel(sidebar)
            pix = QPixmap(str(self._icon_path)).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_lbl.setPixmap(pix)
            brand_layout.addWidget(logo_lbl)

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(2)
        brand_lbl = QLabel("Offline Toolbox", sidebar)
        brand_lbl.setObjectName("appTitle")
        version_lbl = QLabel("v0.1.0 • Desktop", sidebar)
        version_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        brand_text_layout.addWidget(brand_lbl)
        brand_text_layout.addWidget(version_lbl)

        brand_layout.addLayout(brand_text_layout)
        sidebar_layout.addLayout(brand_layout)
        sidebar_layout.addSpacing(10)

        # Nav Buttons
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.home_btn = QPushButton("🏠  Home", sidebar)
        self.home_btn.setProperty("class", "navBtn")
        self.home_btn.setCheckable(True)
        self.home_btn.setChecked(True)
        self.btn_group.addButton(self.home_btn, 0)
        sidebar_layout.addWidget(self.home_btn)

        self.pdf_btn = QPushButton("📄  PDF Workspace", sidebar)
        self.pdf_btn.setProperty("class", "navBtn")
        self.pdf_btn.setCheckable(True)
        self.btn_group.addButton(self.pdf_btn, 1)
        sidebar_layout.addWidget(self.pdf_btn)

        self.img_btn = QPushButton("🖼️  Batch Images", sidebar)
        self.img_btn.setProperty("class", "navBtn")
        self.img_btn.setCheckable(True)
        self.btn_group.addButton(self.img_btn, 2)
        sidebar_layout.addWidget(self.img_btn)

        self.editor_btn = QPushButton("🎨  Image Editor", sidebar)
        self.editor_btn.setProperty("class", "navBtn")
        self.editor_btn.setCheckable(True)
        self.btn_group.addButton(self.editor_btn, 3)
        sidebar_layout.addWidget(self.editor_btn)

        sidebar_layout.addStretch(1)

        # Theme Toggle Button
        self.theme_btn = QPushButton("☀️  Light Mode", sidebar)
        self.theme_btn.setProperty("class", "secondaryBtn")
        self.theme_btn.clicked.connect(self._toggle_theme)
        sidebar_layout.addWidget(self.theme_btn)

        # Privacy Badge Card
        info_card = QFrame(sidebar)
        info_card.setObjectName("sidebarInfoCard")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(4)
        status_dot = QLabel("🟢 Offline Guaranteed", info_card)
        status_dot.setObjectName("privacyTitle")
        info_sub = QLabel("Files are processed strictly in local RAM and temporary storage.", info_card)
        info_sub.setObjectName("privacyDesc")
        info_sub.setWordWrap(True)
        info_layout.addWidget(status_dot)
        info_layout.addWidget(info_sub)
        sidebar_layout.addWidget(info_card)

        root_layout.addWidget(sidebar)

        # 2. Right Stacked Workspaces
        self.stack = QStackedWidget(self)

        self.home_view = HomeView(self)
        self.home_view.action_requested.connect(self._handle_home_action)
        self.stack.addWidget(self.home_view)

        self.pdf_workspace = PDFWorkspace(self)
        self.pdf_workspace.document_loaded.connect(self._update_menu_state)
        self.stack.addWidget(self.pdf_workspace)

        self.image_workspace = ImageWorkspace(self)
        self.stack.addWidget(self.image_workspace)

        self.image_editor = ImageEditorWorkspace(self)
        self.stack.addWidget(self.image_editor)

        root_layout.addWidget(self.stack, stretch=1)

        # Connect Navigation
        self.btn_group.idClicked.connect(self.stack.setCurrentIndex)

        # Status Bar
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.privacy_lbl = QLabel("🟢 Offline — Files processed locally", self)
        self.privacy_lbl.setObjectName("privacyBadge")
        self.status_bar.addPermanentWidget(self.privacy_lbl)
        self.status_bar.showMessage("Ready")

        # Top Application Menu Bar (File, Edit, View, Tools, Help)
        self._create_menu_bar()

    def _create_menu_bar(self):
        menubar = self.menuBar()

        # ── 1. File Menu ──
        file_menu = menubar.addMenu("&File")

        open_pdf_act = QAction("📂 Open PDF…", self)
        open_pdf_act.setShortcut(QKeySequence("Ctrl+O"))
        open_pdf_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._on_open_pdf()))
        file_menu.addAction(open_pdf_act)

        open_img_act = QAction("🖼️ Open Images (Batch)…", self)
        open_img_act.triggered.connect(lambda: (self.img_btn.setChecked(True), self.stack.setCurrentWidget(self.image_workspace), self.image_workspace._on_add_images()))
        file_menu.addAction(open_img_act)

        open_editor_act = QAction("🎨 Edit Image (Crop / 4R / 2x2)…", self)
        open_editor_act.triggered.connect(lambda: (self.editor_btn.setChecked(True), self.stack.setCurrentWidget(self.image_editor), self.image_editor._on_open_image()))
        file_menu.addAction(open_editor_act)

        file_menu.addSeparator()

        self.menu_save_act = QAction("💾 Save", self)
        self.menu_save_act.setShortcut(QKeySequence("Ctrl+S"))
        self.menu_save_act.triggered.connect(lambda: self.pdf_workspace._on_save())
        file_menu.addAction(self.menu_save_act)

        self.menu_save_as_act = QAction("💾 Save As…", self)
        self.menu_save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self.menu_save_as_act.triggered.connect(lambda: self.pdf_workspace._on_save_as())
        file_menu.addAction(self.menu_save_as_act)

        file_menu.addSeparator()

        self.menu_print_act = QAction("🖨️ Print…", self)
        self.menu_print_act.setShortcut(QKeySequence("Ctrl+P"))
        self.menu_print_act.triggered.connect(lambda: self.pdf_workspace._on_print())
        file_menu.addAction(self.menu_print_act)

        file_menu.addSeparator()

        exit_act = QAction("Exit", self)
        exit_act.setShortcut(QKeySequence("Ctrl+Q"))
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # ── 2. Edit Menu ──
        edit_menu = menubar.addMenu("&Edit")

        self.menu_add_text_act = QAction("✏️ Add Text Box", self)
        self.menu_add_text_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._on_add_text_clicked()))
        edit_menu.addAction(self.menu_add_text_act)

        self.menu_font_act = QAction("🔤 Font & Style (System OS Fonts)…", self)
        self.menu_font_act.triggered.connect(lambda: self.pdf_workspace._on_format_font_clicked())
        edit_menu.addAction(self.menu_font_act)

        self.menu_color_act = QAction("🎨 Text Color…", self)
        self.menu_color_act.triggered.connect(lambda: self.pdf_workspace._on_format_color_clicked())
        edit_menu.addAction(self.menu_color_act)

        self.menu_add_img_act = QAction("🖼️ Overlap / Add Image (Stamp/Logo)…", self)
        self.menu_add_img_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._on_add_image_clicked()))
        edit_menu.addAction(self.menu_add_img_act)

        self.menu_clean_sig_act = QAction("🖋️ Clean Signature / Remove Paper Background (Curves Ctrl+M)…", self)
        self.menu_clean_sig_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._on_clean_signature_clicked()))
        edit_menu.addAction(self.menu_clean_sig_act)

        edit_menu.addSeparator()

        self.menu_delete_act = QAction("🗑️ Delete Selected Item", self)
        self.menu_delete_act.setShortcut(QKeySequence("Delete"))
        self.menu_delete_act.triggered.connect(lambda: self.pdf_workspace._on_delete_selected_clicked())
        edit_menu.addAction(self.menu_delete_act)

        self.menu_embed_act = QAction("💾 Embed Edits Into PDF", self)
        self.menu_embed_act.triggered.connect(lambda: self.pdf_workspace._on_embed_edits_clicked())
        edit_menu.addAction(self.menu_embed_act)

        # ── 3. View Menu ──
        view_menu = menubar.addMenu("&View")

        self.menu_zin_act = QAction("Zoom In", self)
        self.menu_zin_act.setShortcut(QKeySequence("Ctrl++"))
        self.menu_zin_act.triggered.connect(lambda: self.pdf_workspace._on_zoom_in())
        view_menu.addAction(self.menu_zin_act)

        self.menu_zout_act = QAction("Zoom Out", self)
        self.menu_zout_act.setShortcut(QKeySequence("Ctrl+-"))
        self.menu_zout_act.triggered.connect(lambda: self.pdf_workspace._on_zoom_out())
        view_menu.addAction(self.menu_zout_act)

        self.menu_fwidth_act = QAction("Fit Width", self)
        self.menu_fwidth_act.setShortcut(QKeySequence("Ctrl+1"))
        self.menu_fwidth_act.triggered.connect(lambda: self.pdf_workspace._on_fit_width())
        view_menu.addAction(self.menu_fwidth_act)

        self.menu_fpage_act = QAction("Fit Page", self)
        self.menu_fpage_act.setShortcut(QKeySequence("Ctrl+0"))
        self.menu_fpage_act.triggered.connect(lambda: self.pdf_workspace._on_fit_page())
        view_menu.addAction(self.menu_fpage_act)

        view_menu.addSeparator()

        self.menu_search_act = QAction("🔍 Find in Document", self)
        self.menu_search_act.setShortcut(QKeySequence("Ctrl+F"))
        self.menu_search_act.triggered.connect(lambda: self.pdf_workspace._show_search_bar())
        view_menu.addAction(self.menu_search_act)

        view_menu.addSeparator()

        fs_act = QAction("Toggle Fullscreen", self)
        fs_act.setShortcut(QKeySequence("F11"))
        fs_act.triggered.connect(self._toggle_fullscreen)
        view_menu.addAction(fs_act)

        theme_act = QAction("Toggle Theme (Dark / Light)", self)
        theme_act.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_act)

        # ── 4. Tools Menu ──
        tools_menu = menubar.addMenu("&Tools")

        self.menu_word_act = QAction("Convert PDF to Word (.docx)…", self)
        self.menu_word_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._convert_to_word()))
        tools_menu.addAction(self.menu_word_act)

        self.menu_compress_act = QAction("Compress PDF…", self)
        self.menu_compress_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._compress_current()))
        tools_menu.addAction(self.menu_compress_act)

        self.menu_rotate_act = QAction("Rotate Pages Dialog…", self)
        self.menu_rotate_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._open_rotate_dialog()))
        tools_menu.addAction(self.menu_rotate_act)

        self.menu_reorder_act = QAction("Rearrange / Move Pages…", self)
        self.menu_reorder_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._open_reorder_dialog()))
        tools_menu.addAction(self.menu_reorder_act)

        self.menu_delete_pages_act = QAction("Delete Pages…", self)
        self.menu_delete_pages_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._open_delete_dialog()))
        tools_menu.addAction(self.menu_delete_pages_act)

        self.menu_export_img_act = QAction("Export PDF Pages as JPEG/PNG…", self)
        self.menu_export_img_act.triggered.connect(lambda: (self.pdf_btn.setChecked(True), self.stack.setCurrentWidget(self.pdf_workspace), self.pdf_workspace._open_export_images_dialog()))
        tools_menu.addAction(self.menu_export_img_act)

        tools_menu.addSeparator()

        merge_act = QAction("Merge Multiple PDFs…", self)
        merge_act.triggered.connect(lambda: self._handle_home_action("merge_pdf", []))
        tools_menu.addAction(merge_act)

        split_act = QAction("Split PDF Pages…", self)
        split_act.triggered.connect(lambda: self._handle_home_action("split_pdf", []))
        tools_menu.addAction(split_act)

        img_pdf_act = QAction("Combine Images to PDF…", self)
        img_pdf_act.triggered.connect(lambda: (self.img_btn.setChecked(True), self.stack.setCurrentWidget(self.image_workspace), self.image_workspace._on_combine_to_pdf()))
        tools_menu.addAction(img_pdf_act)

        # ── 5. Help Menu ──
        help_menu = menubar.addMenu("&Help")

        about_act = QAction("About Offline Toolbox", self)
        about_act.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_act)

        # Update initial menu enablement
        self._update_menu_state(False)

    def _update_menu_state(self, has_doc: bool):
        """Grey out or enable menu items based on document availability."""
        if hasattr(self, "menu_save_act"):
            self.menu_save_act.setEnabled(has_doc)
            self.menu_save_as_act.setEnabled(has_doc)
            self.menu_print_act.setEnabled(has_doc)

            self.menu_add_text_act.setEnabled(has_doc)
            self.menu_font_act.setEnabled(has_doc)
            self.menu_color_act.setEnabled(has_doc)
            self.menu_add_img_act.setEnabled(has_doc)
            self.menu_clean_sig_act.setEnabled(has_doc)
            self.menu_delete_act.setEnabled(has_doc)
            self.menu_embed_act.setEnabled(has_doc)

            self.menu_zin_act.setEnabled(has_doc)
            self.menu_zout_act.setEnabled(has_doc)
            self.menu_fwidth_act.setEnabled(has_doc)
            self.menu_fpage_act.setEnabled(has_doc)
            self.menu_search_act.setEnabled(has_doc)

            self.menu_word_act.setEnabled(has_doc)
            self.menu_compress_act.setEnabled(has_doc)
            self.menu_rotate_act.setEnabled(has_doc)
            self.menu_reorder_act.setEnabled(has_doc)
            self.menu_delete_pages_act.setEnabled(has_doc)
            self.menu_export_img_act.setEnabled(has_doc)

    def _show_about_dialog(self):
        QMessageBox.about(
            self,
            "About Offline Toolbox",
            "<h3>Offline Toolbox v0.1.0</h3>"
            "<p>A private, native desktop application for high-fidelity document and image processing.</p>"
            "<p><b>100% Local:</b> No internet required. Zero data leaves your machine.</p>"
            "<p>Features native Adobe Acrobat-style PDF viewing, text annotation, image stamping, OCR fallback, and multi-format conversion.</p>",
        )

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        files = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if files:
            self._route_files(files)

    def _route_files(self, files: List[Path]):
        first_ext = files[0].suffix.lower()
        if first_ext == ".pdf":
            self.pdf_btn.setChecked(True)
            self.stack.setCurrentWidget(self.pdf_workspace)
            self.pdf_workspace.load_pdf(files[0])
        else:
            self.img_btn.setChecked(True)
            self.stack.setCurrentWidget(self.image_workspace)
            self.image_workspace.add_files(files)

    def _handle_home_action(self, action_id: str, files: List[Path]):
        if action_id == "auto_route" and files:
            self._route_files(files)
            return

        if action_id == "merge_pdf":
            chosen, _ = QFileDialog.getOpenFileNames(
                self, "Select 2 or more PDFs to merge", "", "PDF Files (*.pdf)"
            )
            if chosen and len(chosen) >= 2:
                save_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Merged PDF", "merged_document.pdf", "PDF Files (*.pdf)"
                )
                if save_path:
                    res = PDFService.merge([Path(f) for f in chosen], output_path=Path(save_path))
                    if res.is_ok():
                        QMessageBox.information(self, "Merged", f"Saved to {res.value.name}")
                        self.pdf_btn.setChecked(True)
                        self.stack.setCurrentWidget(self.pdf_workspace)
                        self.pdf_workspace.load_pdf(res.value)
                    else:
                        QMessageBox.critical(self, "Merge Failed", res.error.message)

        elif action_id == "split_pdf":
            chosen, _ = QFileDialog.getOpenFileName(self, "Select PDF to split", "", "PDF Files (*.pdf)")
            if chosen:
                self.pdf_btn.setChecked(True)
                self.stack.setCurrentWidget(self.pdf_workspace)
                self.pdf_workspace.load_pdf(Path(chosen))

        elif action_id == "pdf_to_word":
            chosen, _ = QFileDialog.getOpenFileName(self, "Select PDF to convert to Word", "", "PDF Files (*.pdf)")
            if chosen:
                self.pdf_btn.setChecked(True)
                self.stack.setCurrentWidget(self.pdf_workspace)
                self.pdf_workspace.load_pdf(Path(chosen))
                self.pdf_workspace._convert_to_word()

        elif action_id == "edit_img":
            self.editor_btn.setChecked(True)
            self.stack.setCurrentWidget(self.image_editor)
            self.image_editor._on_open_image()

        elif action_id == "img_to_pdf":
            self.img_btn.setChecked(True)
            self.stack.setCurrentWidget(self.image_workspace)
            self.image_workspace._on_add_images()

        elif action_id == "convert_img":
            self.img_btn.setChecked(True)
            self.stack.setCurrentWidget(self.image_workspace)

        elif action_id == "compress_pdf":
            chosen, _ = QFileDialog.getOpenFileName(self, "Select PDF to compress", "", "PDF Files (*.pdf)")
            if chosen:
                self.pdf_btn.setChecked(True)
                self.stack.setCurrentWidget(self.pdf_workspace)
                self.pdf_workspace.load_pdf(Path(chosen))
                self.pdf_workspace._compress_current()

        elif action_id == "organize_pdf":
            chosen, _ = QFileDialog.getOpenFileName(self, "Select PDF to organize", "", "PDF Files (*.pdf)")
            if chosen:
                self.pdf_btn.setChecked(True)
                self.stack.setCurrentWidget(self.pdf_workspace)
                self.pdf_workspace.load_pdf(Path(chosen))
