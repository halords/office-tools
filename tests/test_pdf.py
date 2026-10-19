import pytest
from pathlib import Path
import fitz
from PIL import Image
from offline_toolbox.core.models import CompressionPreset, ImageFormat
from offline_toolbox.pdf.service import PDFService
from offline_toolbox.pdf.validation import verify_pdf_output


def _create_dummy_pdf(path: Path, num_pages: int = 3):
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 72), f"Test Document Page {i + 1}", fontsize=18)
    doc.save(str(path))
    doc.close()


def test_pdf_inspect_and_verify(tmp_path):
    pdf_f = tmp_path / "doc.pdf"
    _create_dummy_pdf(pdf_f, num_pages=2)

    ver = verify_pdf_output(pdf_f, expected_min_pages=2)
    assert ver.is_ok()

    inspect_res = PDFService.inspect(pdf_f)
    assert inspect_res.is_ok()
    assert inspect_res.value.page_count == 2


def test_pdf_rotate_and_merge(tmp_path):
    pdf_1 = tmp_path / "part1.pdf"
    pdf_2 = tmp_path / "part2.pdf"
    _create_dummy_pdf(pdf_1, num_pages=2)
    _create_dummy_pdf(pdf_2, num_pages=1)

    # Rotate
    rot_res = PDFService.rotate(pdf_1, rotation_delta=90, page_indices=[0])
    assert rot_res.is_ok()
    doc_rot = fitz.open(str(rot_res.value))
    assert doc_rot[0].rotation == 90
    assert doc_rot[1].rotation == 0
    doc_rot.close()

    # Merge
    merged_res = PDFService.merge([pdf_1, pdf_2], output_directory=tmp_path)
    assert merged_res.is_ok()
    doc_m = fitz.open(str(merged_res.value))
    assert len(doc_m) == 3
    doc_m.close()


def test_pdf_compression(tmp_path):
    pdf_f = tmp_path / "large.pdf"
    _create_dummy_pdf(pdf_f, num_pages=5)

    comp_res = PDFService.compress(pdf_f, preset=CompressionPreset.BALANCED)
    assert comp_res.is_ok()
    assert comp_res.value.exists()


def test_images_to_pdf_and_back(tmp_path):
    img1 = tmp_path / "img1.png"
    Image.new("RGB", (300, 400), "blue").save(img1)
    img2 = tmp_path / "img2.jpg"
    Image.new("RGB", (400, 300), "green").save(img2)

    pdf_out = tmp_path / "combined.pdf"
    res_pdf = PDFService.from_images([img1, img2], output_path=pdf_out)
    assert res_pdf.is_ok()
    assert res_pdf.value.exists()

    # Export back to images (all pages)
    res_imgs = PDFService.to_images(res_pdf.value, output_directory=tmp_path, target_format=ImageFormat.PNG)
    assert res_imgs.is_ok()
    assert len(res_imgs.value) == 2


def test_pdf_to_jpeg_page_range_selection(tmp_path):
    pdf_f = tmp_path / "multi_page.pdf"
    _create_dummy_pdf(pdf_f, num_pages=6)

    # Export specific pages (e.g., page 2 and page 5, which are 0-indexed 1 and 4) to JPEG
    out_dir = tmp_path / "jpeg_out"
    out_dir.mkdir()
    res = PDFService.to_images(
        pdf_f,
        output_directory=out_dir,
        target_format=ImageFormat.JPEG,
        dpi=150,
        page_indices=[1, 4],
    )
    assert res.is_ok()
    exported = res.value
    assert len(exported) == 2
    for p in exported:
        assert p.exists()
        assert p.suffix.lower() == ".jpg"
        # Validate that image is readable and non-empty
        with Image.open(p) as im:
            assert im.width > 0 and im.height > 0


def test_pdf_page_reordering_and_deletion(tmp_path):
    pdf_f = tmp_path / "original_pages.pdf"
    _create_dummy_pdf(pdf_f, num_pages=5)

    from offline_toolbox.pdf.pages import reorder_and_delete_pages

    # 1. Test moving page 2 to page 5:
    # Original 0-indexed: [0, 1, 2, 3, 4]
    # Moving page 2 (index 1) to position 5 (index 4) -> [0, 2, 3, 4, 1]
    reordered_pdf = tmp_path / "reordered.pdf"
    res_reorder = reorder_and_delete_pages(
        source_path=pdf_f,
        target_path=reordered_pdf,
        ordered_page_indices=[0, 2, 3, 4, 1],
    )
    assert res_reorder.is_ok()
    doc_r = fitz.open(str(reordered_pdf))
    assert len(doc_r) == 5
    # Original page 1 was index 0, original page 3 was index 2 -> text should match
    assert "Page 1" in doc_r[0].get_text()
    assert "Page 3" in doc_r[1].get_text()
    assert "Page 2" in doc_r[4].get_text()
    doc_r.close()

    # 2. Test deleting page 2 and 4 (keeping 0, 2, 4 in 0-indexed)
    deleted_pdf = tmp_path / "deleted.pdf"
    res_delete = reorder_and_delete_pages(
        source_path=pdf_f,
        target_path=deleted_pdf,
        ordered_page_indices=[0, 2, 4],
    )
    assert res_delete.is_ok()
    doc_d = fitz.open(str(deleted_pdf))
    assert len(doc_d) == 3
    assert "Page 1" in doc_d[0].get_text()
    assert "Page 3" in doc_d[1].get_text()
    assert "Page 5" in doc_d[2].get_text()
    doc_d.close()

