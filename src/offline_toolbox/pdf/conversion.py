"""Cross-conversion between Images and PDFs."""

from pathlib import Path
from typing import List, Optional, Sequence
import fitz  # PyMuPDF
from PIL import Image
from offline_toolbox.core.errors import DocumentError, ImageProcessingError
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.filesystem.naming import generate_safe_output_path
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save
from offline_toolbox.images.color import flatten_alpha, normalize_color_space
from offline_toolbox.pdf.validation import verify_pdf_output

PAGE_SIZES = {
    "A4": (595.28, 841.89),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
    "A3": (841.89, 1190.55),
    "A5": (419.53, 595.28),
}


def images_to_pdf(
    image_paths: List[Path],
    target_path: Path,
    page_size_name: str = "Original",
    fit_to_page: bool = True,
    margin_points: float = 0.0,  # Zero margins: image IS the PDF page
) -> Result[Path, DocumentError]:
    """
    Converts one or multiple images directly into a borderless, full-bleed PDF document.
    Each image forms the exact dimensions of its PDF page (no white padding or borders).
    """
    if not image_paths:
        return Err(DocumentError("No input images provided"))

    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("img2pdf_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

    pdf_doc = None
    try:
        pdf_doc = fitz.open()

        for img_path in image_paths:
            # Create a page matching the image dimensions 1:1 with zero borders/margins
            pix = fitz.Pixmap(str(img_path))
            try:
                page = pdf_doc.new_page(width=pix.width, height=pix.height)
                page.insert_image(fitz.Rect(0, 0, pix.width, pix.height), filename=str(img_path))
            finally:
                pix = None

        pdf_doc.save(str(temp_out), garbage=3, deflate=True)
        pdf_doc.close()
        pdf_doc = None

        verify_res = verify_pdf_output(temp_out, expected_min_pages=len(image_paths))
        if verify_res.is_err():
            return Err(DocumentError(verify_res.error.message))

        atomic_save(temp_out, target_path)
        return Ok(target_path)

    except Exception as e:
        return Err(DocumentError("Failed to convert images to PDF", str(e)))
    finally:
        if pdf_doc is not None:
            pdf_doc.close()
        temp_mgr.cleanup_run(run_dir)


def pdf_to_images(
    source_path: Path,
    output_directory: Path,
    target_format: ImageFormat = ImageFormat.PNG,
    dpi: int = 150,
    page_indices: Optional[Sequence[int]] = None,
) -> Result[List[Path], DocumentError]:
    """Exports specified pages (or all pages if page_indices is None) of a PDF document as high-resolution images."""
    doc = None
    output_files: List[Path] = []
    ext = f".{target_format.value.lower()}"
    if target_format == ImageFormat.JPEG:
        ext = ".jpg"

    try:
        doc = fitz.open(str(source_path))
        total = len(doc)
        indices_to_export = range(total) if page_indices is None else [p for p in page_indices if 0 <= p < total]

        if not indices_to_export:
            return Err(DocumentError("No valid pages selected for image export"))

        for idx in indices_to_export:
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=dpi)

            target_file = generate_safe_output_path(
                source_path=source_path,
                action_suffix=f"page_{idx + 1:03d}",
                target_ext=ext,
                output_directory=output_directory,
            )
            pix.save(str(target_file))
            output_files.append(target_file)

        return Ok(output_files)

    except Exception as e:
        return Err(DocumentError(f"Failed to export PDF {source_path.name} to images", str(e)))
    finally:
        if doc is not None:
            doc.close()

