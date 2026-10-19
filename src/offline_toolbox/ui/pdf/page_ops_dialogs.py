"""Dialogs for PDF Page Operations: Export to Images, Delete Pages, and Reorder Pages."""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.ui.pdf.rotate_dialog import parse_page_ranges


class ExportPdfImagesDialog(QDialog):
    """Dialog allowing users to convert PDF pages into high-resolution JPEG or PNG images."""

    def __init__(
        self,
        total_pages: int,
        current_page_index: int = 0,
        default_output_dir: Optional[Path] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Export PDF Pages as Images")
        self.setFixedWidth(440)
        self.total_pages = total_pages
        self.current_page_index = current_page_index
        self._output_dir = default_output_dir or Path.home()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Scope / Target Pages
        scope_lbl = QLabel("Pages to Export:", self)
        scope_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #F8FAFC;")
        layout.addWidget(scope_lbl)

        scope_box = QVBoxLayout()
        self.scope_group = QButtonGroup(self)

        self.rb_all = QRadioButton(f"All Pages (1 – {self.total_pages})", self)
        self.rb_all.setChecked(True)
        self.scope_group.addButton(self.rb_all, 0)
        scope_box.addWidget(self.rb_all)

        current_label = f"Current Page only (Page {self.current_page_index + 1})"
        self.rb_current = QRadioButton(current_label, self)
        self.scope_group.addButton(self.rb_current, 1)
        scope_box.addWidget(self.rb_current)

        self.rb_range = QRadioButton("Specific Pages or Page Range:", self)
        self.scope_group.addButton(self.rb_range, 2)
        scope_box.addWidget(self.rb_range)

        # Range input
        self.range_input = QLineEdit(self)
        self.range_input.setPlaceholderText("e.g. 1-3, 5, 8")
        self.range_input.setEnabled(False)
        scope_box.addWidget(self.range_input)

        self.rb_range.toggled.connect(self.range_input.setEnabled)
        layout.addLayout(scope_box)

        # Separator line
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334155;")
        layout.addWidget(sep)

        # 2. Output Format & Resolution
        fmt_row = QHBoxLayout()
        fmt_lbl = QLabel("Format:", self)
        fmt_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        fmt_row.addWidget(fmt_lbl)

        self.fmt_combo = QComboBox(self)
        self.fmt_combo.addItem("JPEG (.jpg) - Standard / Compact", ImageFormat.JPEG)
        self.fmt_combo.addItem("PNG (.png) - Lossless Crisp Quality", ImageFormat.PNG)
        fmt_row.addWidget(self.fmt_combo, stretch=1)
        layout.addLayout(fmt_row)

        dpi_row = QHBoxLayout()
        dpi_lbl = QLabel("Resolution (DPI):", self)
        dpi_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        dpi_row.addWidget(dpi_lbl)

        self.dpi_combo = QComboBox(self)
        self.dpi_combo.addItem("150 DPI (Balanced / Standard View)", 150)
        self.dpi_combo.addItem("300 DPI (High Resolution / Print Quality)", 300)
        self.dpi_combo.addItem("72 DPI (Screen Preview / Web Thumbnail)", 72)
        dpi_row.addWidget(self.dpi_combo, stretch=1)
        layout.addLayout(dpi_row)

        # 3. Output Directory Picker
        dir_lbl = QLabel("Destination Folder:", self)
        dir_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0;")
        layout.addWidget(dir_lbl)

        dir_row = QHBoxLayout()
        self.dir_input = QLineEdit(str(self._output_dir), self)
        self.dir_input.setReadOnly(True)
        dir_row.addWidget(self.dir_input, stretch=1)

        browse_btn = QPushButton("Browse…", self)
        browse_btn.clicked.connect(self._on_browse_dir)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        # 4. Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Export Images")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _on_browse_dir(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for Images", str(self._output_dir)
        )
        if folder:
            self._output_dir = Path(folder)
            self.dir_input.setText(str(self._output_dir))

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

    def get_target_format(self) -> ImageFormat:
        return self.fmt_combo.currentData()

    def get_dpi(self) -> int:
        return self.dpi_combo.currentData()

    def get_output_directory(self) -> Path:
        return self._output_dir

    def get_target_page_indices(self) -> Optional[List[int]]:
        """Returns 0-indexed list of pages, or None if all pages."""
        if self.rb_all.isChecked():
            return None
        elif self.rb_current.isChecked():
            return [self.current_page_index]
        elif self.rb_range.isChecked():
            return parse_page_ranges(self.range_input.text(), self.total_pages)
        return None


class DeletePagesDialog(QDialog):
    """Dialog allowing users to remove specific pages or ranges from the active PDF."""

    def __init__(self, total_pages: int, current_page_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Delete PDF Pages")
        self.setFixedWidth(400)
        self.total_pages = total_pages
        self.current_page_index = current_page_index

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(f"Document has {self.total_pages} total page(s).", self)
        header.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(header)

        warn_lbl = QLabel("Select pages to permanently remove from this document:", self)
        warn_lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #F8FAFC;")
        layout.addWidget(warn_lbl)

        box = QVBoxLayout()
        self.group = QButtonGroup(self)

        current_label = f"Current Page (Page {self.current_page_index + 1})"
        self.rb_current = QRadioButton(current_label, self)
        self.rb_current.setChecked(True)
        self.group.addButton(self.rb_current, 0)
        box.addWidget(self.rb_current)

        self.rb_range = QRadioButton("Specific Page Number or Range:", self)
        self.group.addButton(self.rb_range, 1)
        box.addWidget(self.rb_range)

        self.range_input = QLineEdit(self)
        self.range_input.setPlaceholderText("e.g. 2 or 2-4, 6")
        self.range_input.setEnabled(False)
        box.addWidget(self.range_input)

        self.rb_range.toggled.connect(self.range_input.setEnabled)
        layout.addLayout(box)

        # Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("Delete Pages")
        ok_btn.setStyleSheet("background-color: #DC2626; color: white; font-weight: bold;")
        self.button_box.accepted.connect(self._validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _validate_and_accept(self):
        pages_to_delete = self.get_pages_to_delete()
        if not pages_to_delete:
            QMessageBox.warning(
                self,
                "Invalid Selection",
                f"Please enter valid page numbers between 1 and {self.total_pages}.\nExample: 2 or 1-3, 5",
            )
            return

        # Ensure we do not delete every page in the document
        if len(pages_to_delete) >= self.total_pages:
            QMessageBox.critical(
                self,
                "Cannot Delete All Pages",
                "A PDF document must contain at least one page. You cannot delete all pages.",
            )
            return

        del_human = ", ".join(str(p + 1) for p in pages_to_delete)
        remaining = self.total_pages - len(pages_to_delete)
        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete page(s): {del_human}?\n\n{remaining} page(s) will remain in the document.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.accept()

    def get_pages_to_delete(self) -> Optional[List[int]]:
        """Returns 0-indexed list of page indices to delete."""
        if self.rb_current.isChecked():
            return [self.current_page_index]
        elif self.rb_range.isChecked():
            return parse_page_ranges(self.range_input.text(), self.total_pages)
        return None

    def get_remaining_page_indices(self) -> List[int]:
        """Returns ordered 0-indexed list of pages that remain after deletion."""
        to_delete = set(self.get_pages_to_delete() or [])
        return [i for i in range(self.total_pages) if i not in to_delete]


class ReorderPagesDialog(QDialog):
    """Dialog allowing users to move pages (e.g., move page 2 to page 5) or reorder via visual list."""

    def __init__(self, total_pages: int, current_page_index: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Rearrange PDF Pages")
        self.setFixedWidth(460)
        self.setFixedHeight(480)
        self.total_pages = total_pages
        self.current_page_index = current_page_index
        # 0-indexed list of page indices in current working order
        self._page_order: List[int] = list(range(total_pages))

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # 1. Quick Move Card ("Move Page X to Page Y")
        quick_card = QFrame(self)
        quick_card.setStyleSheet("background-color: #0F172A; border: 1px solid #334155; border-radius: 8px; padding: 10px;")
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setSpacing(8)

        quick_title = QLabel("⚡ Quick Move Page:", quick_card)
        quick_title.setStyleSheet("color: #38BDF8; font-weight: bold; font-size: 12px;")
        quick_layout.addWidget(quick_title)

        move_row = QHBoxLayout()
        move_row.setSpacing(6)

        move_row.addWidget(QLabel("Move Page", quick_card))
        self.spin_from = QSpinBox(quick_card)
        self.spin_from.setRange(1, self.total_pages)
        self.spin_from.setValue(self.current_page_index + 1)
        move_row.addWidget(self.spin_from)

        move_row.addWidget(QLabel("→ into Position", quick_card))
        self.spin_to = QSpinBox(quick_card)
        self.spin_to.setRange(1, self.total_pages)
        # Default destination: next position or page 1
        default_to = min(self.total_pages, (self.current_page_index + 2) if self.current_page_index + 1 < self.total_pages else 1)
        self.spin_to.setValue(default_to)
        move_row.addWidget(self.spin_to)

        btn_apply_move = QPushButton("Move", quick_card)
        btn_apply_move.setStyleSheet("background-color: #0284C7; color: white; font-weight: bold; padding: 4px 12px;")
        btn_apply_move.clicked.connect(self._on_quick_move)
        move_row.addWidget(btn_apply_move)
        quick_layout.addLayout(move_row)

        layout.addWidget(quick_card)

        # 2. Page Sequence List with Up/Down Controls
        list_lbl = QLabel("Current Page Order (Drag or use Up / Down to reorder):", self)
        list_lbl.setStyleSheet("font-weight: 600; color: #E2E8F0; font-size: 12px;")
        layout.addWidget(list_lbl)

        list_row = QHBoxLayout()
        self.list_widget = QListWidget(self)
        self.list_widget.setStyleSheet(
            "QListWidget { background-color: #1E293B; border: 1px solid #475569; border-radius: 6px; font-size: 12px; }"
            "QListWidget::item { padding: 5px; color: #F1F5F9; border-bottom: 1px solid #334155; }"
            "QListWidget::item:selected { background-color: #0284C7; color: white; }"
        )
        self._refresh_list()
        list_row.addWidget(self.list_widget, stretch=1)

        # Side buttons for list
        side_btns = QVBoxLayout()
        side_btns.setSpacing(6)

        btn_up = QPushButton("▲ Move Up", self)
        btn_up.clicked.connect(self._on_move_up)
        side_btns.addWidget(btn_up)

        btn_down = QPushButton("▼ Move Down", self)
        btn_down.clicked.connect(self._on_move_down)
        side_btns.addWidget(btn_down)

        btn_top = QPushButton("⤒ To Top", self)
        btn_top.clicked.connect(self._on_move_top)
        side_btns.addWidget(btn_top)

        btn_bottom = QPushButton("⤓ To Bottom", self)
        btn_bottom.clicked.connect(self._on_move_bottom)
        side_btns.addWidget(btn_bottom)

        btn_reset = QPushButton("↺ Reset", self)
        btn_reset.clicked.connect(self._on_reset)
        side_btns.addWidget(btn_reset)

        side_btns.addStretch(1)
        list_row.addLayout(side_btns)
        layout.addLayout(list_row, stretch=1)

        # 3. Dialog Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Apply Reordering")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _refresh_list(self, select_idx: int = 0):
        self.list_widget.clear()
        for pos, original_idx in enumerate(self._page_order):
            item_text = f"Position {pos + 1}:  Original Page {original_idx + 1}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, original_idx)
            self.list_widget.addItem(item)

        if 0 <= select_idx < self.list_widget.count():
            self.list_widget.setCurrentRow(select_idx)

    def _on_quick_move(self):
        from_pos = self.spin_from.value() - 1  # 0-indexed
        to_pos = self.spin_to.value() - 1      # 0-indexed

        if from_pos == to_pos:
            return

        # Pop from position and insert into destination position
        item = self._page_order.pop(from_pos)
        self._page_order.insert(to_pos, item)
        self._refresh_list(select_idx=to_pos)

    def _on_move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            self._page_order[row], self._page_order[row - 1] = self._page_order[row - 1], self._page_order[row]
            self._refresh_list(select_idx=row - 1)

    def _on_move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._page_order) - 1:
            self._page_order[row], self._page_order[row + 1] = self._page_order[row + 1], self._page_order[row]
            self._refresh_list(select_idx=row + 1)

    def _on_move_top(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self._page_order.pop(row)
            self._page_order.insert(0, item)
            self._refresh_list(select_idx=0)

    def _on_move_bottom(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._page_order) - 1:
            item = self._page_order.pop(row)
            self._page_order.append(item)
            self._refresh_list(select_idx=len(self._page_order) - 1)

    def _on_reset(self):
        self._page_order = list(range(self.total_pages))
        self._refresh_list(select_idx=0)

    def get_ordered_page_indices(self) -> List[int]:
        """Returns 0-indexed list of page indices in new desired order."""
        return list(self._page_order)
