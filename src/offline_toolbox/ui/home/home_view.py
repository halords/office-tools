"""Home dashboard with prominent drag-and-drop zone and quick actions."""

from pathlib import Path
from typing import Callable, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DropZoneFrame(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        icon_lbl = QLabel("📥", self)
        icon_lbl.setStyleSheet("font-size: 40px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_lbl = QLabel("Drag & Drop your PDFs or Images here", self)
        main_lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #F1F5F9;")
        main_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub_lbl = QLabel("or click below to browse files from your computer", self)
        sub_lbl.setStyleSheet("font-size: 13px; color: #94A3B8;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("Browse Files", self)
        browse_btn.setProperty("class", "secondaryBtn")
        browse_btn.clicked.connect(self._on_browse)

        layout.addWidget(icon_lbl)
        layout.addWidget(main_lbl)
        layout.addWidget(sub_lbl)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        file_paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        if file_paths:
            self.files_dropped.emit(file_paths)

    def _on_browse(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents or Images",
            "",
            "Documents & Images (*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tiff *.ico);;All Files (*)",
        )
        if files:
            self.files_dropped.emit([Path(f) for f in files])


class HomeView(QWidget):
    """Home view dashboard with quick actions."""

    action_requested = Signal(str, list)  # action_name, file_paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(24)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title = QLabel("Welcome to Offline Toolbox", self)
        title.setObjectName("welcomeTitle")
        subtitle = QLabel(
            "100% offline document and image processing. Your files never leave this computer.", self
        )
        subtitle.setObjectName("welcomeSubtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # Drop Zone
        self.drop_zone = DropZoneFrame(self)
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        main_layout.addWidget(self.drop_zone)

        # Quick Actions Grid
        actions_title = QLabel("Popular Tools", self)
        actions_title.setStyleSheet("font-size: 16px; font-weight: 600; color: #F1F5F9; margin-top: 10px;")
        main_layout.addWidget(actions_title)

        grid = QGridLayout()
        grid.setSpacing(16)

        cards = [
            ("Merge PDFs", "Combine multiple PDF files into one clean document", "merge_pdf", 0, 0),
            ("Split PDF", "Extract page ranges or separate into individual documents", "split_pdf", 0, 1),
            ("PDF to Word", "Convert document to editable Word (.docx) with OCR fallback", "pdf_to_word", 0, 2),
            ("Photo & Image Editor", "Crop, fit to width, slide 4R/2x2/Passport & clean signatures", "edit_img", 1, 0),
            ("Images to PDF", "Convert and assemble photos into an organized PDF", "img_to_pdf", 1, 1),
            ("Convert Images", "Fast batch format conversion (JPEG, PNG, WebP, ICO)", "convert_img", 1, 2),
        ]

        for title_text, desc_text, action_id, r, c in cards:
            card = self._create_action_card(title_text, desc_text, action_id)
            grid.addWidget(card, r, c)

        main_layout.addLayout(grid)
        main_layout.addStretch(1)

    def _create_action_card(self, title: str, desc: str, action_id: str) -> QFrame:
        card = QFrame(self)
        card.setProperty("class", "actionCard")
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)

        t_lbl = QLabel(title, card)
        t_lbl.setProperty("class", "cardTitle")

        d_lbl = QLabel(desc, card)
        d_lbl.setProperty("class", "cardDesc")
        d_lbl.setWordWrap(True)

        layout.addWidget(t_lbl)
        layout.addWidget(d_lbl)

        card.mousePressEvent = lambda e: self.action_requested.emit(action_id, [])
        return card

    def _on_files_dropped(self, paths: List[Path]):
        self.action_requested.emit("auto_route", paths)
