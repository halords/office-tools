"""PyMuPDF high-performance rendering to QImage / QPixmap."""

from pathlib import Path
from typing import Optional, Tuple
import fitz  # PyMuPDF
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.models import PageInfo, PDFMetadata
from offline_toolbox.core.result import Err, Ok, Result


class PDFRenderer:
    """Provides high-performance page and thumbnail rendering."""

    @staticmethod
    def inspect_document(doc_path: Path) -> Result[PDFMetadata, DocumentError]:
        doc = None
        try:
            doc = fitz.open(str(doc_path))
            meta = doc.metadata or {}
            pdf_meta = PDFMetadata(
                title=meta.get("title") or None,
                author=meta.get("author") or None,
                subject=meta.get("subject") or None,
                keywords=meta.get("keywords") or None,
                creator=meta.get("creator") or None,
                producer=meta.get("producer") or None,
                creation_date=meta.get("creationDate") or None,
                modification_date=meta.get("modDate") or None,
                page_count=len(doc),
                is_encrypted=doc.is_encrypted,
                file_size_bytes=doc_path.stat().st_size if doc_path.exists() else 0,
            )
            return Ok(pdf_meta)
        except Exception as e:
            return Err(DocumentError(f"Failed to inspect PDF: {doc_path.name}", str(e)))
        finally:
            if doc is not None:
                doc.close()

    @staticmethod
    def get_page_info(doc_path: Path, page_index: int) -> Result[PageInfo, DocumentError]:
        doc = None
        try:
            doc = fitz.open(str(doc_path))
            if page_index < 0 or page_index >= len(doc):
                return Err(DocumentError(f"Page index {page_index} out of range (total {len(doc)})"))
            page = doc.load_page(page_index)
            rect = page.rect
            return Ok(PageInfo(
                page_number=page_index + 1,
                width=rect.width,
                height=rect.height,
                rotation=page.rotation,
            ))
        except Exception as e:
            return Err(DocumentError(f"Failed to read page {page_index}", str(e)))
        finally:
            if doc is not None:
                doc.close()

    @staticmethod
    def render_page_to_qimage(doc_path: Path, page_index: int, dpi: int = 150) -> Result[QImage, DocumentError]:
        doc = None
        try:
            doc = fitz.open(str(doc_path))
            if page_index < 0 or page_index >= len(doc):
                return Err(DocumentError(f"Page index {page_index} out of range"))
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            
            # Convert PyMuPDF pixmap buffer to QImage without intermediate disk write
            img = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888,
            )
            return Ok(img.copy())  # Detach copy from buffer
        except Exception as e:
            return Err(DocumentError(f"Failed to render page {page_index}", str(e)))
        finally:
            if doc is not None:
                doc.close()

    @staticmethod
    def render_thumbnail_to_pixmap(doc_path: Path, page_index: int, max_size: int = 180) -> Result[QPixmap, DocumentError]:
        render_res = PDFRenderer.render_page_to_qimage(doc_path, page_index, dpi=72)
        if render_res.is_err():
            return render_res
        
        qimg = render_res.value
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            max_size,
            max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return Ok(scaled)
