"""High-fidelity PDF to Word (.docx) converter with layout reconstruction and offline OCR.

Features:
1. Tier 1 (pdf2docx): For vector/digital PDFs with native text layers (tables, images, fonts).
2. Tier 2 (Smart Layout Reconstruction & OCR):
   - Auto-orientation normalization (handles rotated/sideways scanned PDFs).
   - Visual header seal & logo banner embedding.
   - Structured table detection and grid reconstruction (columns, rows, cell formatting).
   - Section heading detection (Roman numerals, bold titles, center alignment).
   - Natural paragraph flow & justification (merges wrapped OCR text lines).
   - Bullet point and numbered list reconstruction.
"""

import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import docx
import fitz  # PyMuPDF
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save

log = logging.getLogger(__name__)


# ── Cell Margin Styling Helper ──────────────────────────────────────────

def _set_cell_padding(cell, top: int = 80, bottom: int = 80, left: int = 100, right: int = 100):
    """Set inner padding for Word table cells in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


# ── Public Entry Point ───────────────────────────────────────────────────

def convert_pdf_to_docx(
    source_path: Path,
    target_path: Path,
    enable_ocr_fallback: bool = True,
    language: str = "eng",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Result[Path, DocumentError]:
    """
    Convert a PDF into a high-fidelity Microsoft Word (.docx) document.
    """
    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("pdf2docx_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".docx")

    doc = None
    try:
        doc = fitz.open(str(source_path))
        total_pages = len(doc)
        if total_pages == 0:
            return Err(DocumentError(f"PDF contains no pages: {source_path.name}"))

        # Step 1: Detect if PDF has rich native selectable text
        has_native_text = _has_rich_native_text(doc, total_pages)

        if has_native_text:
            if progress_callback:
                progress_callback(0, total_pages, "Analyzing native document layout…")
            tier1_path = _try_pdf2docx(source_path, temp_out, total_pages, progress_callback)
            if tier1_path is not None:
                atomic_save(tier1_path, target_path)
                return Ok(target_path)
            log.info("Native layout conversion fell through; applying Smart OCR Reconstruction.")

        # Step 2: Smart Layout & OCR Reconstruction Engine
        result_docx = _build_high_fidelity_docx(
            doc=doc,
            total_pages=total_pages,
            temp_out=temp_out,
            temp_mgr=temp_mgr,
            run_dir=run_dir,
            enable_ocr=enable_ocr_fallback,
            progress_callback=progress_callback,
        )

        atomic_save(result_docx, target_path)
        return Ok(target_path)

    except Exception as e:
        log.exception("PDF-to-Word conversion error")
        return Err(DocumentError(f"Conversion failed: {source_path.name}", str(e)))
    finally:
        if doc is not None:
            doc.close()
        temp_mgr.cleanup_run(run_dir)


# ── Native pdf2docx Strategy ────────────────────────────────────────────

def _has_rich_native_text(doc: fitz.Document, total_pages: int) -> bool:
    """True if document contains real digital text (not scanned images)."""
    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text().strip())
    avg = total_chars / max(1, total_pages)
    return avg >= 50


def _try_pdf2docx(
    source_path: Path,
    temp_out: Path,
    total_pages: int,
    progress_callback: Optional[Callable],
) -> Optional[Path]:
    """Execute pdf2docx converter if native text is available."""
    try:
        from pdf2docx import Converter

        if progress_callback:
            progress_callback(1, total_pages, "Reconstructing native layout…")

        cv = Converter(str(source_path))
        cv.convert(str(temp_out), start=0, end=None)
        cv.close()

        if temp_out.exists() and temp_out.stat().st_size > 1024:
            return temp_out
        return None
    except Exception as exc:
        log.warning("pdf2docx encountered issue: %s", exc)
        return None


# ── Smart Layout & OCR Reconstruction ───────────────────────────────────

def _build_high_fidelity_docx(
    doc: fitz.Document,
    total_pages: int,
    temp_out: Path,
    temp_mgr: TempFileManager,
    run_dir: Path,
    enable_ocr: bool,
    progress_callback: Optional[Callable],
) -> Path:
    """
    Reconstruct document layout, tables, headings, logos, and flowing paragraphs.
    """
    ocr_engine = None
    if enable_ocr:
        try:
            from rapidocr_onnxruntime import RapidOCR
            ocr_engine = RapidOCR()
        except ImportError:
            log.warning("RapidOCR not installed; OCR fallback unavailable.")

    word_doc = docx.Document()
    for sec in word_doc.sections:
        sec.top_margin = Inches(0.7)
        sec.bottom_margin = Inches(0.7)
        sec.left_margin = Inches(0.8)
        sec.right_margin = Inches(0.8)

    for p_idx in range(total_pages):
        if progress_callback:
            progress_callback(p_idx + 1, total_pages, f"Reconstructing page {p_idx + 1} of {total_pages}…")

        page = doc.load_page(p_idx)

        # Fix orientation: Normalize sideways rotated pages (e.g. 270° or 90°)
        _normalize_page_orientation(page)

        pix = page.get_pixmap(dpi=150)
        img_w, img_h = pix.width, pix.height

        if p_idx > 0:
            word_doc.add_page_break()

        # Page 1 Visual Header Banner (Emblem / Seal / Logos)
        has_embedded_banner = False
        if p_idx == 0:
            banner_h_ratio = 0.16
            crop_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * banner_h_ratio)
            crop_pix = page.get_pixmap(dpi=150, clip=crop_rect)
            banner_file = temp_mgr.create_temp_file(run_dir, ".png")
            crop_pix.save(str(banner_file))

            p_banner = word_doc.add_paragraph()
            p_banner.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_banner.paragraph_format.space_after = Pt(8)
            run = p_banner.add_run()
            run.add_picture(str(banner_file), width=Inches(6.2))
            has_embedded_banner = True

        # Extract items using OCR
        if not ocr_engine:
            continue

        raw_results, _ = ocr_engine(pix.tobytes("png"))
        if not raw_results:
            continue

        # Parse and sort items
        items = _parse_ocr_boxes(raw_results)

        # Filter out items already in the visual header banner
        if has_embedded_banner:
            items = [it for it in items if it["y0"] > (img_h * 0.15)]

        # Group items into lines
        lines = _group_items_into_lines(items)

        # Render lines, tables, headings, and paragraphs
        _render_structured_page(word_doc, lines, img_w)

    word_doc.save(str(temp_out))
    return temp_out


def _normalize_page_orientation(page: fitz.Page):
    """Ensure page is in its natural portrait orientation."""
    # If rotation is sideways (90 or 270) and original mediabox is portrait
    mb = page.mediabox
    if mb.height > mb.width and page.rotation in (90, 270):
        page.set_rotation(0)
    elif page.rect.width > page.rect.height and page.rotation != 0:
        # Check if setting rotation=0 makes it portrait
        page.set_rotation(0)


def _parse_ocr_boxes(ocr_results: list) -> List[Dict[str, Any]]:
    """Convert raw OCR box lists to structured geometric dictionaries."""
    items = []
    for box, text, score in ocr_results:
        clean = text.strip()
        if not clean:
            continue
        xs = [pt[0] for pt in box]
        ys = [pt[1] for pt in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        items.append({
            "text": clean,
            "x0": x0,
            "x1": x1,
            "y0": y0,
            "y1": y1,
            "w": x1 - x0,
            "h": y1 - y0,
            "cx": (x0 + x1) / 2.0,
            "score": score,
        })
    # Sort primarily top to bottom
    items.sort(key=lambda it: it["y0"])
    return items


def _group_items_into_lines(items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Group OCR items that share the same horizontal band into a single line."""
    grouped = []
    curr_line: List[Dict[str, Any]] = []

    for it in items:
        if not curr_line:
            curr_line.append(it)
            continue
        prev_y = curr_line[0]["y0"]
        if abs(it["y0"] - prev_y) <= 14:
            curr_line.append(it)
        else:
            curr_line.sort(key=lambda x: x["x0"])
            grouped.append(curr_line)
            curr_line = [it]

    if curr_line:
        curr_line.sort(key=lambda x: x["x0"])
        grouped.append(curr_line)

    # Post-process: If a 2-item line is just "I." and "BACKGROUND", merge them into 1 item!
    normalized = []
    for line in grouped:
        if len(line) == 2:
            first_txt = line[0]["text"].strip()
            if re.match(r"^[I|V|X|1-9]+\.?$", first_txt):
                merged = dict(line[0])
                merged["text"] = f"{first_txt} {line[1]['text'].strip()}"
                merged["x1"] = line[1]["x1"]
                merged["w"] = merged["x1"] - merged["x0"]
                normalized.append([merged])
                continue
        normalized.append(line)

    return normalized


def _render_structured_page(word_doc: docx.Document, lines: List[List[Dict[str, Any]]], page_width: float):
    """
    Render structured lines into Word: detecting tables, headings, lists, and paragraphs.
    """
    idx = 0
    while idx < len(lines):
        line = lines[idx]

        # ── 1. Table Detection ──
        is_table_line = len(line) >= 2 and any(it["w"] > 40 for it in line)
        if is_table_line:
            # Collect consecutive table rows
            table_rows = [line]
            idx += 1
            while idx < len(lines) and len(lines[idx]) >= 2:
                table_rows.append(lines[idx])
                idx += 1

            _add_reconstructed_table(word_doc, table_rows)
            continue

        # ── 2. Single Line Elements ──
        item = line[0]
        text = item["text"]
        cx = item["cx"]
        w = item["w"]
        page_center = page_width / 2.0

        is_centered = abs(cx - page_center) < (page_width * 0.12) and w < (page_width * 0.75)
        is_section_header = (
            bool(re.match(r"^[I|V|X]+\.\s+", text)) or
            (text.isupper() and len(text) < 60 and w < (page_width * 0.8)) or
            text.startswith("TERMS OF REFERENCE") or
            text.startswith("General Objective") or
            text.startswith("Specific Objectives")
        )
        is_bullet = bool(re.match(r"^[\u2022\u25cf\-\*]\s*", text)) or bool(re.match(r"^\d+\.\s+", text))

        if is_section_header:
            p = word_doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            if is_centered:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold = True
            run.font.name = "Calibri"
            run.font.size = Pt(11.5)
            idx += 1
            continue

        if is_centered:
            p = word_doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(text)
            if any(k in text.upper() for k in ["REPUBLIC", "PROVINCE", "OFFICE", "ADMINISTRATOR", "TERMS", "YEAR"]):
                run.bold = True
            run.font.name = "Calibri"
            run.font.size = Pt(11)
            idx += 1
            continue

        if is_bullet:
            style = "List Bullet" if not re.match(r"^\d+\.", text) else "List Number"
            p = word_doc.add_paragraph(style=style)
            clean_text = re.sub(r"^[\u2022\u25cf\-\*]\s*", "", text)
            run = p.add_run(clean_text)
            run.font.name = "Calibri"
            run.font.size = Pt(11)
            p.paragraph_format.space_after = Pt(3)
            idx += 1
            continue

        # ── 3. Flowing Paragraph (Merge wrapped lines) ──
        para_items = [text]
        idx += 1
        while idx < len(lines):
            next_line = lines[idx]
            if len(next_line) != 1:
                break
            next_item = next_line[0]
            next_text = next_item["text"]

            # Stop merging if next line is a header, bullet, or centered
            if (
                re.match(r"^[I|V|X]+\.\s+", next_text) or
                re.match(r"^[\u2022\u25cf\-\*]\s*", next_text) or
                (abs(next_item["cx"] - page_center) < (page_width * 0.12) and next_item["w"] < (page_width * 0.75))
            ):
                break

            # Stop if previous line ended with a full stop and there is noticeable vertical gap
            if para_items[-1].endswith((".", ":")) and (next_item["y0"] - line[0]["y0"]) > 35:
                break

            para_items.append(next_text)
            idx += 1

        p = word_doc.add_paragraph()
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        combined_text = " ".join(para_items)
        run = p.add_run(combined_text)
        run.font.name = "Calibri"
        run.font.size = Pt(11)


def _add_reconstructed_table(word_doc: docx.Document, table_rows: List[List[Dict[str, Any]]]):
    """Insert a cleanly formatted Word table from detected rows."""
    max_cols = max(len(r) for r in table_rows)
    if max_cols == 0:
        return

    tbl = word_doc.add_table(rows=len(table_rows), cols=max_cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.style = "Table Grid"

    for r_idx, row_items in enumerate(table_rows):
        row = tbl.rows[r_idx]
        for c_idx, cell_item in enumerate(row_items):
            cell = row.cells[c_idx]
            cell.text = cell_item["text"]
            _set_cell_padding(cell, top=60, bottom=60, left=80, right=80)
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.space_before = Pt(2)
            if r_idx == 0:
                for r in p.runs:
                    r.bold = True
                    r.font.name = "Calibri"
                    r.font.size = Pt(10)
            else:
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(9.5)

    # Spacer after table
    p_spacer = word_doc.add_paragraph()
    p_spacer.paragraph_format.space_after = Pt(4)
