"""Image Workspace for batch format conversion, resizing, and ICO generation."""

from pathlib import Path
from typing import List
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.images.service import ImageService
from offline_toolbox.pdf.service import PDFService


class ImageWorkspace(QWidget):
    """Batch Image processing and conversion workspace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_images: List[Path] = []
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Left: File list and add/remove buttons
        left_box = QVBoxLayout()
        left_box.setSpacing(10)

        list_lbl = QLabel("Selected Images", self)
        list_lbl.setObjectName("sectionHeader")
        left_box.addWidget(list_lbl)

        self.file_list = QListWidget(self)
        left_box.addWidget(self.file_list)

        btn_row = QHBoxLayout()
        self.add_btn = QPushButton("+ Add Images", self)
        self.add_btn.setProperty("class", "secondaryBtn")
        self.add_btn.clicked.connect(self._on_add_images)
        btn_row.addWidget(self.add_btn)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.setProperty("class", "secondaryBtn")
        self.clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self.clear_btn)
        left_box.addLayout(btn_row)

        layout.addLayout(left_box, stretch=2)

        # Right: Distinct Cards for Image Conversion vs Image to PDF
        right_box = QVBoxLayout()
        right_box.setSpacing(16)

        # Card 1: Batch Image Format Conversion
        convert_card = QFrame(self)
        convert_card.setProperty("class", "actionCard")
        cc_layout = QVBoxLayout(convert_card)
        cc_layout.setSpacing(12)

        cc_title = QLabel("🔄  Batch Image Format Converter", convert_card)
        cc_title.setProperty("class", "cardTitle")
        cc_layout.addWidget(cc_title)

        cc_desc = QLabel(
            "Batch convert images to another image format (JPEG, PNG, WebP, ICO), resize, or strip camera metadata.",
            convert_card,
        )
        cc_desc.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 4px;")
        cc_desc.setWordWrap(True)
        cc_layout.addWidget(cc_desc)

        form = QFormLayout()
        form.setSpacing(10)

        # Target Format
        self.format_combo = QComboBox(convert_card)
        for fmt in ImageFormat:
            self.format_combo.addItem(fmt.name, fmt)
        form.addRow("Format:", self.format_combo)

        # Quality slider
        self.quality_slider = QSlider(Qt.Orientation.Horizontal, convert_card)
        self.quality_slider.setRange(10, 100)
        self.quality_slider.setValue(90)
        self.quality_val_lbl = QLabel("90%", convert_card)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_val_lbl.setText(f"{v}%"))
        q_row = QHBoxLayout()
        q_row.addWidget(self.quality_slider)
        q_row.addWidget(self.quality_val_lbl)
        form.addRow("Quality:", q_row)

        # Photo Size Presets (2x2, 4R, Passport, Government ID)
        self.preset_combo = QComboBox(convert_card)
        self.preset_combo.addItem("None (Custom / Original size)", None)
        from offline_toolbox.images.presets import PHOTO_PRESETS
        for pid, preset in PHOTO_PRESETS.items():
            self.preset_combo.addItem(f"📐 {preset.name} — {preset.width_px}x{preset.height_px} px", pid)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        form.addRow("Photo Preset:", self.preset_combo)

        # Preset fit mode
        self.crop_fill_chk = QCheckBox("Crop to fill (borderless) instead of padding with white", convert_card)
        self.crop_fill_chk.setChecked(True)
        form.addRow("", self.crop_fill_chk)

        # Resize width
        self.width_spin = QSpinBox(convert_card)
        self.width_spin.setRange(0, 10000)
        self.width_spin.setSpecialValueText("Original width")
        form.addRow("Max Width (px):", self.width_spin)

        # Metadata stripping
        self.strip_meta_chk = QCheckBox("Remove EXIF / camera metadata (Privacy)", convert_card)
        self.strip_meta_chk.setChecked(True)
        form.addRow("", self.strip_meta_chk)

        cc_layout.addLayout(form)

        self.convert_btn = QPushButton("Convert Images Now", convert_card)
        self.convert_btn.setProperty("class", "primaryBtn")
        self.convert_btn.clicked.connect(self._on_convert)
        cc_layout.addWidget(self.convert_btn)

        right_box.addWidget(convert_card)

        # Card 2: Separate Images to PDF Card
        pdf_card = QFrame(self)
        pdf_card.setProperty("class", "actionCard")
        pc_layout = QVBoxLayout(pdf_card)
        pc_layout.setSpacing(12)

        pc_title = QLabel("📄  Images to PDF", pdf_card)
        pc_title.setProperty("class", "cardTitle")
        pc_layout.addWidget(pc_title)

        pc_desc = QLabel(
            "Combine selected images into a single PDF. Each page directly matches the image dimensions 1:1 with zero borders or margins.",
            pdf_card,
        )
        pc_desc.setStyleSheet("color: #94A3B8; font-size: 12px; margin-bottom: 4px;")
        pc_desc.setWordWrap(True)
        pc_layout.addWidget(pc_desc)

        self.to_pdf_btn = QPushButton("Create PDF from Images (1:1 Full Bleed)", pdf_card)
        self.to_pdf_btn.setProperty("class", "secondaryBtn")
        self.to_pdf_btn.clicked.connect(self._on_combine_to_pdf)
        pc_layout.addWidget(self.to_pdf_btn)

        right_box.addWidget(pdf_card)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        right_box.addWidget(self.progress_bar)

        right_box.addStretch(1)
        layout.addLayout(right_box, stretch=3)

        self._update_action_state()

    def _update_action_state(self):
        has_imgs = len(self._selected_images) > 0
        self.clear_btn.setEnabled(has_imgs)
        self.convert_btn.setEnabled(has_imgs)
        self.to_pdf_btn.setEnabled(has_imgs)

    def add_files(self, paths: List[Path]):
        for p in paths:
            if p not in self._selected_images and p.is_file():
                self._selected_images.append(p)
                self.file_list.addItem(f"{p.name} ({p.stat().st_size // 1024} KB)")
        self._update_action_state()

    def _on_add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tiff *.ico)",
        )
        if files:
            self.add_files([Path(f) for f in files])

    def _on_clear(self):
        self._selected_images.clear()
        self.file_list.clear()
        self._update_action_state()

    def _on_preset_changed(self):
        preset_id = self.preset_combo.currentData()
        if preset_id:
            from offline_toolbox.images.presets import PHOTO_PRESETS
            preset = PHOTO_PRESETS.get(preset_id)
            if preset:
                self.width_spin.setValue(preset.width_px)
                self.width_spin.setEnabled(False)
        else:
            self.width_spin.setEnabled(True)

    def _on_convert(self):
        if not self._selected_images:
            QMessageBox.warning(self, "No Images", "Please add images to convert.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not out_dir:
            return

        fmt = self.format_combo.currentData()
        quality = self.quality_slider.value()
        w = self.width_spin.value() or None
        strip_meta = self.strip_meta_chk.isChecked()
        preset_id = self.preset_combo.currentData()
        crop_to_fill = self.crop_fill_chk.isChecked()

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(self._selected_images))
        self.progress_bar.setValue(0)

        def progress_cb(idx, total, name):
            self.progress_bar.setValue(idx)

        res = ImageService.batch_convert(
            source_paths=self._selected_images,
            target_format=fmt,
            output_directory=Path(out_dir),
            quality=quality,
            resize_width=w,
            strip_metadata=strip_meta,
            preset_id=preset_id,
            crop_to_fill=crop_to_fill,
            progress_callback=progress_cb,
        )

        self.progress_bar.setVisible(False)
        if res.is_ok():
            QMessageBox.information(
                self,
                "Batch Conversion Done",
                f"Successfully converted {len(res.value)} images to {fmt.name}.",
            )
        else:
            QMessageBox.critical(self, "Conversion Error", res.error.message)

    def _on_combine_to_pdf(self):
        if not self._selected_images:
            QMessageBox.warning(self, "No Images", "Please add images to combine.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Save Combined PDF", "images_combined.pdf", "PDF Files (*.pdf)"
        )
        if not save_path:
            return

        res = PDFService.from_images(self._selected_images, output_path=Path(save_path))
        if res.is_ok():
            QMessageBox.information(
                self, "PDF Created", f"Successfully created PDF with {len(self._selected_images)} pages:\n{res.value.name}"
            )
        else:
            QMessageBox.critical(self, "Creation Failed", res.error.message)
