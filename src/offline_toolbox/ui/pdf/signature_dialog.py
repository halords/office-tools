"""Interactive dialog for Photoshop-style Curves (Ctrl+M) & signature / ink background removal."""

from pathlib import Path
from typing import Optional
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)
from offline_toolbox.images.signature import clean_signature_and_remove_white


class SignatureCleanDialog(QDialog):
    """
    Dialog with real-time preview allowing the user to clean a signature / stamp image:
    - Adjust paper brightness (white threshold) to eliminate paper grain and shadows
    - Adjust ink contrast (black threshold) to solidify thin pen strokes
    - Choose ink color (keep original or force solid dark black/blue ink)
    """

    def __init__(self, original_image_path: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ink & Signature Extraction (Curves & Multiply Blend)")
        self.resize(720, 520)

        self._orig_path = original_image_path
        self._pil_orig = Image.open(original_image_path)
        self._cleaned_pil: Optional[Image.Image] = None
        self._output_path: Optional[Path] = None
        self._solid_ink_color: Optional[tuple] = None  # None = retain original ink color

        self._init_ui()
        self._update_preview()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        header_lbl = QLabel(
            "<b>Photoshop-style Curves & Multiply Blend</b><br>"
            "<span style='color: #94A3B8; font-size: 12px;'>"
            "Eliminate white/gray paper backgrounds and shadows while keeping handwritten names, signatures, and stamps solid and crisp."
            "</span>",
            self,
        )
        header_lbl.setWordWrap(True)
        layout.addWidget(header_lbl)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # ── Left Preview Box ──
        preview_container = QFrame(self)
        preview_container.setObjectName("actionCard")
        preview_container.setStyleSheet(
            "background-color: #0F172A; border: 1px solid #334155; border-radius: 8px;"
        )
        p_layout = QVBoxLayout(preview_container)
        p_layout.setContentsMargins(12, 12, 12, 12)

        # Checkerboard background simulation label
        self.preview_lbl = QLabel(preview_container)
        self.preview_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setMinimumSize(320, 300)
        self.preview_lbl.setStyleSheet(
            "background: repeating-conic-gradient(#1E293B 0% 25%, #0F172A 0% 50%) 50% / 20px 20px;"
            "border-radius: 6px;"
        )
        p_layout.addWidget(self.preview_lbl)
        content_layout.addWidget(preview_container, stretch=3)

        # ── Right Controls ──
        ctrl_card = QFrame(self)
        ctrl_card.setObjectName("actionCard")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(12)

        # 1. Paper Brightness (White Cutoff)
        self.white_slider = QSlider(Qt.Orientation.Horizontal, ctrl_card)
        self.white_slider.setRange(100, 255)
        self.white_slider.setValue(215)
        self.white_val_lbl = QLabel("215", ctrl_card)
        self.white_slider.valueChanged.connect(self._on_slider_changed)
        w_row = QHBoxLayout()
        w_row.addWidget(self.white_slider)
        w_row.addWidget(self.white_val_lbl)
        form.addRow("Paper Brightness (Ctrl+M):", w_row)

        # 2. Ink Contrast (Black Cutoff)
        self.black_slider = QSlider(Qt.Orientation.Horizontal, ctrl_card)
        self.black_slider.setRange(0, 150)
        self.black_slider.setValue(80)
        self.black_val_lbl = QLabel("80", ctrl_card)
        self.black_slider.valueChanged.connect(self._on_slider_changed)
        b_row = QHBoxLayout()
        b_row.addWidget(self.black_slider)
        b_row.addWidget(self.black_val_lbl)
        form.addRow("Ink Darkness & Contrast:", b_row)

        # 3. Solid Deep Black Ink Toggle
        self.solid_black_chk = QCheckBox("Deepen ink strokes to solid black (Signature mode)", ctrl_card)
        self.solid_black_chk.setChecked(True)
        self.solid_black_chk.toggled.connect(self._update_preview)
        form.addRow("", self.solid_black_chk)

        # 4. Custom Ink Color Picker Button
        self.color_btn = QPushButton("🎨 Pick Custom Ink Color…", ctrl_card)
        self.color_btn.setProperty("class", "secondaryBtn")
        self.color_btn.clicked.connect(self._on_pick_ink_color)
        form.addRow("Ink Hue:", self.color_btn)

        c_layout.addLayout(form)
        c_layout.addStretch(1)

        content_layout.addWidget(ctrl_card, stretch=4)
        layout.addLayout(content_layout)

        # Dialog Buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_slider_changed(self):
        self.white_val_lbl.setText(str(self.white_slider.value()))
        self.black_val_lbl.setText(str(self.black_slider.value()))
        self._update_preview()

    def _on_pick_ink_color(self):
        qc = QColorDialog.getColor(parent=self, title="Select Ink Color")
        if qc.isValid():
            self._solid_ink_color = (qc.red(), qc.green(), qc.blue())
            self.color_btn.setText(f"🎨 Ink: #{qc.name()}")
            self.color_btn.setStyleSheet(f"color: {qc.name()}; font-weight: bold;")
            self._update_preview()

    def _update_preview(self):
        w_cut = self.white_slider.value()
        b_cut = self.black_slider.value()
        deepen = self.solid_black_chk.isChecked()

        cleaned = clean_signature_and_remove_white(
            self._pil_orig,
            white_cutoff=w_cut,
            black_cutoff=b_cut,
            ink_color=self._solid_ink_color,
            deepen_ink=deepen,
        )
        self._cleaned_pil = cleaned

        # Convert to QPixmap for preview display
        rgba = cleaned.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimg = QImage(data, rgba.width, rgba.height, QImage.Format.Format_RGBA8888)
        pix = QPixmap.fromImage(qimg)

        scaled_pix = pix.scaled(
            self.preview_lbl.width() - 10,
            self.preview_lbl.height() - 10,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_lbl.setPixmap(scaled_pix)

    def _on_accept(self):
        if self._cleaned_pil:
            # Save into temporary PNG with transparent alpha channel
            from offline_toolbox.filesystem.temporary import TempFileManager
            tm = TempFileManager()
            run_dir = tm.create_run_directory("clean_sig_")
            out_file = tm.create_temp_file(run_dir, ".png")
            self._cleaned_pil.save(out_file, format="PNG")
            self._output_path = out_file
        self.accept()

    def get_cleaned_image_path(self) -> Optional[Path]:
        return self._output_path
