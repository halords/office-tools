"""Dialog for choosing page rotation angles and page range targeting."""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
)


def parse_page_ranges(range_str: str, max_pages: int) -> Optional[List[int]]:
    """
    Parses comma and hyphen separated ranges like '1-3, 5, 7-9' into 0-indexed page indices.
    """
    cleaned = range_str.strip()
    if not cleaned:
        return None

    page_indices = set()
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            bounds = part.split("-")
            if len(bounds) != 2:
                return None
            try:
                start_p = int(bounds[0].strip())
                end_p = int(bounds[1].strip())
                if start_p < 1 or end_p > max_pages or start_p > end_p:
                    return None
                for p in range(start_p, end_p + 1):
                    page_indices.add(p - 1)
            except ValueError:
                return None
        else:
            try:
                p = int(part)
                if p < 1 or p > max_pages:
                    return None
                page_indices.add(p - 1)
            except ValueError:
                return None

    return sorted(list(page_indices)) if page_indices else None


class RotatePagesDialog(QDialog):
    """Dialog allowing users to rotate All Pages, Selected Range, or Current Page."""

    def __init__(self, total_pages: int, current_page_index: int = 0, selected_indices: Optional[List[int]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rotate PDF Pages")
        self.setFixedWidth(380)
        self.total_pages = total_pages
        self.current_page_index = current_page_index
        self.selected_indices = selected_indices or []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Rotation Direction
        dir_lbl = QLabel("Rotation Angle:", self)
        dir_lbl.setStyleSheet("font-weight: 600;")
        layout.addWidget(dir_lbl)

        dir_box = QHBoxLayout()
        self.r_90_cw = QRadioButton("90° Right (Clockwise)", self)
        self.r_90_cw.setChecked(True)
        self.r_90_ccw = QRadioButton("90° Left (Counter-Clockwise)", self)
        self.r_180 = QRadioButton("180°", self)

        dir_box.addWidget(self.r_90_cw)
        dir_box.addWidget(self.r_90_ccw)
        dir_box.addWidget(self.r_180)
        layout.addLayout(dir_box)

        # 2. Scope / Target Pages
        scope_lbl = QLabel("Apply Rotation To:", self)
        scope_lbl.setStyleSheet("font-weight: 600; margin-top: 10px;")
        layout.addWidget(scope_lbl)

        scope_box = QVBoxLayout()
        self.scope_group = QButtonGroup(self)

        self.rb_all = QRadioButton(f"All Pages (1 – {self.total_pages})", self)
        self.rb_all.setChecked(True)
        self.scope_group.addButton(self.rb_all, 0)
        scope_box.addWidget(self.rb_all)

        current_label = f"Current Page (Page {self.current_page_index + 1})"
        self.rb_current = QRadioButton(current_label, self)
        self.scope_group.addButton(self.rb_current, 1)
        scope_box.addWidget(self.rb_current)

        self.rb_range = QRadioButton("Custom Page Range:", self)
        self.scope_group.addButton(self.rb_range, 2)
        scope_box.addWidget(self.rb_range)

        # Range input
        self.range_input = QLineEdit(self)
        self.range_input.setPlaceholderText("e.g. 1-3, 5, 8-10")
        self.range_input.setEnabled(False)
        scope_box.addWidget(self.range_input)

        self.rb_range.toggled.connect(self.range_input.setEnabled)

        layout.addLayout(scope_box)

        # 3. Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _validate_and_accept(self):
        if self.rb_range.isChecked():
            parsed = parse_page_ranges(self.range_input.text(), self.total_pages)
            if not parsed:
                QMessageBox.warning(
                    self,
                    "Invalid Range",
                    f"Please enter valid page numbers between 1 and {self.total_pages}.\nExample: 1-3, 5, 7",
                )
                return
        self.accept()

    def get_rotation_delta(self) -> int:
        if self.r_90_cw.isChecked():
            return 90
        elif self.r_90_ccw.isChecked():
            return 270
        elif self.r_180.isChecked():
            return 180
        return 90

    def get_target_page_indices(self) -> Optional[List[int]]:
        """Returns 0-indexed list of pages, or None if all pages."""
        if self.rb_all.isChecked():
            return None
        elif self.rb_current.isChecked():
            return [self.current_page_index]
        elif self.rb_range.isChecked():
            return parse_page_ranges(self.range_input.text(), self.total_pages)
        return None
