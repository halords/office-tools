"""Post-operation PDF validation and structural integrity checks."""

from pathlib import Path
import fitz  # PyMuPDF
from offline_toolbox.core.errors import OutputVerificationError
from offline_toolbox.core.result import Err, Ok, Result


def verify_pdf_output(target_path: Path, expected_min_pages: int = 1) -> Result[Path, OutputVerificationError]:
    """
    Guarantees document integrity before completing an operation:
    1. Output file exists on disk and is non-zero size.
    2. PDF xref structure can be parsed without fatal error.
    3. Document contains at least the expected page count.
    4. First and last pages can be rendered into raster memory without crashing.
    """
    if not target_path.exists():
        return Err(OutputVerificationError(f"Target file was not written to disk: {target_path.name}"))

    if target_path.stat().st_size == 0:
        return Err(OutputVerificationError(f"Target file is 0 bytes (empty output): {target_path.name}"))

    doc = None
    try:
        doc = fitz.open(str(target_path))
        if doc.is_encrypted:
            return Err(OutputVerificationError(f"Generated PDF is unexpectedly encrypted: {target_path.name}"))

        page_count = len(doc)
        if page_count < expected_min_pages:
            return Err(OutputVerificationError(
                f"Generated PDF has {page_count} pages, expected at least {expected_min_pages}"
            ))

        # Test rendering first page
        page_0 = doc.load_page(0)
        pix_0 = page_0.get_pixmap(dpi=72)
        if pix_0.width == 0 or pix_0.height == 0:
            return Err(OutputVerificationError(f"Rendered page 1 dimensions are invalid in {target_path.name}"))

        # Test rendering last page if document has multiple pages
        if page_count > 1:
            page_last = doc.load_page(page_count - 1)
            pix_last = page_last.get_pixmap(dpi=72)
            if pix_last.width == 0 or pix_last.height == 0:
                return Err(OutputVerificationError(f"Rendered last page dimensions are invalid in {target_path.name}"))

        return Ok(target_path)

    except Exception as e:
        return Err(OutputVerificationError(f"Verification parse error for {target_path.name}", str(e)))
    finally:
        if doc is not None:
            doc.close()
