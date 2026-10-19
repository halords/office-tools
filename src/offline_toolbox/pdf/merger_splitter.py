"""High-fidelity PDF merging and splitting operations."""

from pathlib import Path
from typing import List, Tuple
import fitz  # PyMuPDF
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.filesystem.naming import generate_safe_output_path
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save
from offline_toolbox.pdf.validation import verify_pdf_output


def merge_pdfs(
    source_paths: List[Path],
    target_path: Path,
) -> Result[Path, DocumentError]:
    """Merges multiple PDF documents into a single document, preserving bookmarks and structures."""
    if len(source_paths) < 2:
        return Err(DocumentError("Merging requires at least 2 input PDF files"))

    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("merge_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

    merged_doc = None
    open_docs = []
    total_expected_pages = 0

    try:
        merged_doc = fitz.open()

        for path in source_paths:
            doc = fitz.open(str(path))
            open_docs.append(doc)
            total_expected_pages += len(doc)
            merged_doc.insert_pdf(doc)

        merged_doc.save(str(temp_out), garbage=3, deflate=True)
        merged_doc.close()
        merged_doc = None

        verify_res = verify_pdf_output(temp_out, expected_min_pages=total_expected_pages)
        if verify_res.is_err():
            return Err(DocumentError(verify_res.error.message))

        atomic_save(temp_out, target_path)
        return Ok(target_path)

    except Exception as e:
        return Err(DocumentError("Failed to merge PDF files", str(e)))
    finally:
        for d in open_docs:
            d.close()
        if merged_doc is not None:
            merged_doc.close()
        temp_mgr.cleanup_run(run_dir)


def split_pdf_by_ranges(
    source_path: Path,
    ranges: List[Tuple[int, int]],  # (start_page, end_page) 1-indexed inclusive
    output_directory: Path,
) -> Result[List[Path], DocumentError]:
    """Splits PDF by specified page ranges into separate files."""
    if not ranges:
        return Err(DocumentError("No split ranges specified"))

    doc = None
    generated_files: List[Path] = []
    temp_mgr = TempFileManager()

    try:
        doc = fitz.open(str(source_path))
        total_pages = len(doc)

        for idx, (start_p, end_p) in enumerate(ranges, start=1):
            if start_p < 1 or end_p > total_pages or start_p > end_p:
                return Err(DocumentError(f"Invalid split range: {start_p}-{end_p} (total pages: {total_pages})"))

            run_dir = temp_mgr.create_run_directory(f"split_{idx}_")
            temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

            sub_doc = fitz.open()
            # PyMuPDF uses 0-indexed half-open ranges
            sub_doc.insert_pdf(doc, from_page=start_p - 1, to_page=end_p - 1)
            sub_doc.save(str(temp_out), garbage=3, deflate=True)
            sub_doc.close()

            expected_pages = (end_p - start_p) + 1
            verify_res = verify_pdf_output(temp_out, expected_min_pages=expected_pages)
            if verify_res.is_err():
                return Err(DocumentError(verify_res.error.message))

            target_file = generate_safe_output_path(
                source_path=source_path,
                action_suffix=f"part_{idx:02d}_p{start_p}-{end_p}",
                target_ext=".pdf",
                output_directory=output_directory,
            )
            atomic_save(temp_out, target_file)
            generated_files.append(target_file)
            temp_mgr.cleanup_run(run_dir)

        return Ok(generated_files)

    except Exception as e:
        return Err(DocumentError(f"Failed to split PDF {source_path.name}", str(e)))
    finally:
        if doc is not None:
            doc.close()
