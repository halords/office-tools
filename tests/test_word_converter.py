import pytest
from pathlib import Path
import fitz
import docx
from offline_toolbox.pdf.service import PDFService


def test_pdf_to_word_conversion(tmp_path):
    # 1. Create a sample PDF with mixed text
    pdf_path = tmp_path / "sample_doc.pdf"
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), "Annual Financial Report Summary", fontsize=16)
    p1.insert_text((72, 110), "Revenue increased by 24% over the prior period.", fontsize=11)

    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 72), "Chapter 2: Operational Highlights", fontsize=14)
    p2.insert_text((72, 100), "Supply chain efficiency improved significantly.", fontsize=11)

    doc.save(str(pdf_path))
    doc.close()

    # 2. Convert to Word (.docx)
    docx_out = tmp_path / "output.docx"
    res = PDFService.to_word(
        source_path=pdf_path,
        output_path=docx_out,
        enable_ocr_fallback=True,
    )

    assert res.is_ok()
    assert docx_out.exists()

    # 3. Read back using python-docx to verify content integrity
    word_doc = docx.Document(str(docx_out))
    full_text = "\n".join(p.text for p in word_doc.paragraphs)

    assert "Annual Financial Report Summary" in full_text
    assert "Revenue increased by 24%" in full_text
    assert "Chapter 2: Operational Highlights" in full_text
