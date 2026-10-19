"""PDF compression and stream optimization."""

from pathlib import Path
import fitz  # PyMuPDF
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.models import CompressionPreset
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.filesystem.temporary import TempFileManager, atomic_save
from offline_toolbox.pdf.validation import verify_pdf_output


def compress_pdf(
    source_path: Path,
    target_path: Path,
    preset: CompressionPreset = CompressionPreset.BALANCED,
) -> Result[Path, DocumentError]:
    """
    Compresses PDF using stream deflating, dead-object garbage collection,
    and image re-encoding without corrupting text or vector layouts.
    """
    temp_mgr = TempFileManager()
    run_dir = temp_mgr.create_run_directory("compress_")
    temp_out = temp_mgr.create_temp_file(run_dir, ".pdf")

    doc = None
    try:
        doc = fitz.open(str(source_path))
        page_count = len(doc)

        # PyMuPDF save options
        # garbage=4: compact cross reference table, remove unused objects, deduplicate streams
        # deflate=True: compress content streams using zlib
        # clean=True: clean and sanitize content streams
        save_kwargs = {
            "garbage": 4,
            "deflate": True,
            "clean": True,
        }

        if preset == CompressionPreset.SMALL_FILE:
            save_kwargs["deflate_images"] = True
            save_kwargs["deflate_fonts"] = True

        doc.save(str(temp_out), **save_kwargs)
        doc.close()
        doc = None

        verify_res = verify_pdf_output(temp_out, expected_min_pages=page_count)
        if verify_res.is_err():
            return Err(DocumentError(verify_res.error.message))

        atomic_save(temp_out, target_path)
        return Ok(target_path)

    except Exception as e:
        return Err(DocumentError(f"Failed to compress PDF {source_path.name}", str(e)))
    finally:
        if doc is not None:
            doc.close()
        temp_mgr.cleanup_run(run_dir)
