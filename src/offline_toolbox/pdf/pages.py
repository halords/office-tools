"""PDF page operations: rotation, reordering, deletion, duplication, extraction."""

from pathlib import Path
from typing import Dict, List, Sequence, Union
import fitz  # PyMuPDF
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save
from offline_toolbox.pdf.validation import verify_pdf_output


def rotate_pages(
    source_path: Path,
    target_path: Path,
    rotation_delta: int,  # e.g. 90, 180, 270
    page_indices: Union[Sequence[int], None] = None,  # None means all pages
) -> Result[Path, DocumentError]:
    """Rotates PDF pages structurally without rasterization."""
    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("rot_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

    doc = None
    try:
        doc = fitz.open(str(source_path))
        total_pages = len(doc)
        pages_to_rotate = range(total_pages) if page_indices is None else page_indices

        for p_idx in pages_to_rotate:
            if 0 <= p_idx < total_pages:
                page = doc.load_page(p_idx)
                current_rot = page.rotation
                new_rot = (current_rot + rotation_delta) % 360
                page.set_rotation(new_rot)

        doc.save(str(temp_out), garbage=3, deflate=True)
        doc.close()
        doc = None

        verify_res = verify_pdf_output(temp_out, expected_min_pages=total_pages)
        if verify_res.is_err():
            return Err(DocumentError(verify_res.error.message))

        atomic_save(temp_out, target_path)
        return Ok(target_path)

    except Exception as e:
        return Err(DocumentError(f"Failed to rotate PDF {source_path.name}", str(e)))
    finally:
        if doc is not None:
            doc.close()
        temp_mgr.cleanup_run(run_dir)


def reorder_and_delete_pages(
    source_path: Path,
    target_path: Path,
    ordered_page_indices: List[int],  # 0-indexed order of pages to keep
) -> Result[Path, DocumentError]:
    """Reorders, duplicates, or deletes pages according to ordered_page_indices."""
    if not ordered_page_indices:
        return Err(DocumentError("Page selection cannot be empty"))

    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("reorder_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

    src_doc = None
    new_doc = None
    try:
        src_doc = fitz.open(str(source_path))
        new_doc = fitz.open()

        for idx in ordered_page_indices:
            if 0 <= idx < len(src_doc):
                new_doc.insert_pdf(src_doc, from_page=idx, to_page=idx)

        new_doc.save(str(temp_out), garbage=3, deflate=True)
        new_doc.close()
        src_doc.close()
        new_doc = None
        src_doc = None

        verify_res = verify_pdf_output(temp_out, expected_min_pages=len(ordered_page_indices))
        if verify_res.is_err():
            return Err(DocumentError(verify_res.error.message))

        atomic_save(temp_out, target_path)
        return Ok(target_path)

    except Exception as e:
        return Err(DocumentError(f"Failed to reorder PDF {source_path.name}", str(e)))
    finally:
        if src_doc is not None:
            src_doc.close()
        if new_doc is not None:
            new_doc.close()
        temp_mgr.cleanup_run(run_dir)
