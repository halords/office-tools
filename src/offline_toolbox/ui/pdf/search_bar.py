"""Floating In-Page Search Bar for Acrobat-style text search."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class PDFSearchBar(QFrame):
    """
    Floating search bar docked at the top right of the PDF canvas (Acrobat-style).
    """

    search_requested = Signal(str)    # text to search
    next_match_requested = Signal()
    prev_match_requested = Signal()
    closed = Signal()

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("pdfSearchBar")
        self.setVisible(False)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Find in document…")
        self.input_field.setFixedWidth(160)
        self.input_field.textChanged.connect(self._on_text_changed)
        self.input_field.returnPressed.connect(self.next_match_requested.emit)
        layout.addWidget(self.input_field)

        self.match_count_lbl = QLabel("No matches", self)
        self.match_count_lbl.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 0 4px;")
        layout.addWidget(self.match_count_lbl)

        self.prev_btn = QPushButton("▲", self)
        self.prev_btn.setToolTip("Previous Match (Shift+Enter)")
        self.prev_btn.setProperty("class", "toolIconBtn")
        self.prev_btn.setFixedSize(24, 24)
        self.prev_btn.clicked.connect(self.prev_match_requested.emit)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▼", self)
        self.next_btn.setToolTip("Next Match (Enter)")
        self.next_btn.setProperty("class", "toolIconBtn")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.clicked.connect(self.next_match_requested.emit)
        layout.addWidget(self.next_btn)

        self.close_btn = QPushButton("✕", self)
        self.close_btn.setToolTip("Close Search (Esc)")
        self.close_btn.setProperty("class", "toolIconBtn")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.hide_bar)
        layout.addWidget(self.close_btn)

    def show_bar(self):
        self.setVisible(True)
        self.raise_()
        self.input_field.setFocus()
        self.input_field.selectAll()

    def hide_bar(self):
        self.setVisible(False)
        self.closed.emit()

    def set_match_status(self, current: int, total: int):
        if total == 0:
            self.match_count_lbl.setText("No matches")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
        else:
            self.match_count_lbl.setText(f"{current + 1} of {total}")
            self.prev_btn.setEnabled(True)
            self.next_btn.setEnabled(True)

    def _on_text_changed(self, text: str):
        self.search_requested.emit(text.strip())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_bar()
        else:
            super().keyPressEvent(event)
