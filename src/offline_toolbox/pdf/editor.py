"""PDF In-Place Overlay and Editing Service.

Bakes text boxes and image overlays directly into the PDF pages using PyMuPDF (fitz).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.result import Err, Ok, Result


@dataclass
class TextOverlay:
    page_index: int
    x: float          # Left in PDF points (72 DPI)
    y: float          # Top in PDF points (72 DPI)
    width: float      # Width in PDF points
    height: float     # Height in PDF points
    text: str
    font_family: str = "Helvetica"
    font_size: float = 12.0
    color: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # RGB (0-1)
    is_bold: bool = False
    is_italic: bool = False
    is_underline: bool = False


@dataclass
class ImageOverlay:
    page_index: int
    x: float          # Left in PDF points (72 DPI)
    y: float          # Top in PDF points (72 DPI)
    width: float      # Width in PDF points
    height: float     # Height in PDF points
    image_path: Path
    opacity: float = 1.0  # 0.0 to 1.0


@dataclass
class AcroformOverlay:
    page_index: int
    x: float
    y: float
    width: float
    height: float
    field_type: int  # fitz.PDF_WIDGET_TYPE_TEXT or fitz.PDF_WIDGET_TYPE_CHECKBOX
    field_name: str
    field_value: str = ""


def apply_overlays_to_pdf(
    source_path: Path,
    target_path: Path,
    text_overlays: List[TextOverlay],
    image_overlays: List[ImageOverlay],
    acroform_overlays: List[AcroformOverlay] = None,
) -> Result[Path, DocumentError]:
    """
    Burn text and image overlays directly into the PDF.
    If target_path == source_path, safely saves to temporary and replaces the original.
    """
    doc = None
    try:
        doc = fitz.open(str(source_path))

        # 1. Apply image overlays
        for img in image_overlays:
            if 0 <= img.page_index < len(doc):
                page = doc[img.page_index]
                rect = fitz.Rect(img.x, img.y, img.x + img.width, img.y + img.height)
                page.insert_image(
                    rect,
                    filename=str(img.image_path),
                    overlay=True,
                    keep_proportion=False,
                )

        # 2. Apply text overlays
        for txt in text_overlays:
            if 0 <= txt.page_index < len(doc):
                page = doc[txt.page_index]
                rect = fitz.Rect(txt.x, txt.y, txt.x + txt.width, txt.y + txt.height)

                # Base font selection
                fam = txt.font_family.lower()
                if "times" in fam or "roman" in fam or "serif" in fam:
                    base = "ti"
                elif "courier" in fam or "mono" in fam or "code" in fam:
                    base = "co"
                else:
                    base = "he"

                if base == "ti":
                    font_name = "tibi" if (txt.is_bold and txt.is_italic) else ("tibo" if txt.is_bold else ("tiit" if txt.is_italic else "tiro"))
                elif base == "co":
                    font_name = "cobi" if (txt.is_bold and txt.is_italic) else ("cobo" if txt.is_bold else ("coit" if txt.is_italic else "cour"))
                else:
                    font_name = "hebi" if (txt.is_bold and txt.is_italic) else ("hebo" if txt.is_bold else ("heit" if txt.is_italic else "helv"))

                page.insert_textbox(
                    rect,
                    txt.text,
                    fontsize=txt.font_size,
                    fontname=font_name,
                    color=txt.color,
                    align=fitz.TEXT_ALIGN_LEFT,
                    overlay=True,
                )

                if txt.is_underline:
                    # Draw subtle underline under the text line
                    line_y = min(rect.y1, rect.y0 + txt.font_size * 1.15)
                    # Approximate text width: len(txt.text) * font_size * 0.55
                    approx_w = min(rect.width, len(txt.text) * txt.font_size * 0.58)
                    page.draw_line(
                        fitz.Point(rect.x0, line_y),
                        fitz.Point(rect.x0 + approx_w, line_y),
                        color=txt.color,
                        width=max(0.75, txt.font_size / 14.0),
                        overlay=True,
                    )

        # 3. Apply acroform overlays
        if acroform_overlays:
            for acro in acroform_overlays:
                if 0 <= acro.page_index < len(doc):
                    page = doc[acro.page_index]
                    rect = fitz.Rect(acro.x, acro.y, acro.x + acro.width, acro.y + acro.height)
                    widget = fitz.Widget()
                    widget.rect = rect
                    widget.field_type = acro.field_type
                    widget.field_name = acro.field_name
                    widget.field_value = acro.field_value
                    if acro.field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                        widget.text_format = fitz.PDF_WIDGET_TX_FORMAT_NONE
                    page.add_widget(widget)

        # Save result (in-place or to target)
        if target_path.resolve() == source_path.resolve():
            temp_save = source_path.with_name(f"{source_path.stem}_tmp_edit.pdf")
            doc.save(str(temp_save), garbage=3, deflate=True)
            doc.close()
            doc = None
            temp_save.replace(source_path)
            return Ok(source_path)
        else:
            doc.save(str(target_path), garbage=3, deflate=True)
            return Ok(target_path)

    except Exception as exc:
        return Err(DocumentError(f"Failed to embed edits into PDF: {exc}"))
    finally:
        if doc:
            doc.close()
