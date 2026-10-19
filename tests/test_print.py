"""Unit tests for PDF printing pipeline."""

from pathlib import Path
import fitz
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication
from PySide6.QtPrintSupport import QPrinter


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_pdf_printing_to_pdf_target(tmp_path: Path, qapp):
    """Verify that PyMuPDF pages render into QPrinter target at high resolution."""
    # Create sample 2-page PDF
    pdf_path = tmp_path / "printable_sample.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((50, 100), "Hello Page 1", fontsize=20)
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 100), "Hello Page 2", fontsize=20)
    doc.save(str(pdf_path))
    doc.close()

    # Configure printer to output PDF file
    out_print_file = tmp_path / "printed_result.pdf"
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(str(out_print_file))

    # Render pages onto printer
    doc = fitz.open(str(pdf_path))
    painter = QPainter(printer)
    page_rect = printer.pageLayout().paintRectPixels(printer.resolution())

    for i in range(len(doc)):
        if i > 0:
            printer.newPage()
        page = doc[i]
        pix = page.get_pixmap(dpi=150, alpha=False)
        qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        scaled = qimg.scaled(
            page_rect.width(),
            page_rect.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x_off = page_rect.x() + (page_rect.width() - scaled.width()) / 2
        y_off = page_rect.y() + (page_rect.height() - scaled.height()) / 2
        painter.drawImage(int(x_off), int(y_off), scaled)

    painter.end()
    doc.close()

    assert out_print_file.exists()
    assert out_print_file.stat().st_size > 500

    # Verify printed PDF has 2 pages
    verify_doc = fitz.open(str(out_print_file))
    assert len(verify_doc) == 2
    verify_doc.close()
