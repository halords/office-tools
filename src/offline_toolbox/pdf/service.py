"""Facade service orchestrating PDF operations."""

from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, Union
from offline_toolbox.core.errors import DocumentError
from offline_toolbox.core.models import CompressionPreset, ImageFormat, PageInfo, PDFMetadata
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.core.validators import validate_pdf_file
from offline_toolbox.filesystem.naming import generate_safe_output_path
from offline_toolbox.pdf.compression import compress_pdf
from offline_toolbox.pdf.conversion import images_to_pdf, pdf_to_images
from offline_toolbox.pdf.editor import ImageOverlay, TextOverlay, AcroformOverlay, apply_overlays_to_pdf
from offline_toolbox.pdf.merger_splitter import merge_pdfs, split_pdf_by_ranges
from offline_toolbox.pdf.pages import reorder_and_delete_pages, rotate_pages
from offline_toolbox.pdf.renderer import PDFRenderer


class PDFService:
    """Service layer exposing high-level, validated PDF manipulation commands."""

    @staticmethod
    def inspect(doc_path: Path) -> Result[PDFMetadata, DocumentError]:
        val = validate_pdf_file(doc_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        return PDFRenderer.inspect_document(doc_path)

    @staticmethod
    def merge(
        source_paths: List[Path],
        output_path: Optional[Path] = None,
        output_directory: Optional[Path] = None,
    ) -> Result[Path, DocumentError]:
        if not output_path:
            output_path = generate_safe_output_path(
                source_path=source_paths[0],
                action_suffix="merged",
                target_ext=".pdf",
                output_directory=output_directory,
            )
        return merge_pdfs(source_paths, output_path)

    @staticmethod
    def split(
        source_path: Path,
        ranges: List[Tuple[int, int]],
        output_directory: Optional[Path] = None,
    ) -> Result[List[Path], DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        out_dir = output_directory or source_path.parent
        return split_pdf_by_ranges(source_path, ranges, out_dir)

    @staticmethod
    def rotate(
        source_path: Path,
        rotation_delta: int,
        page_indices: Union[Sequence[int], None] = None,
        output_directory: Optional[Path] = None,
    ) -> Result[Path, DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        target_path = generate_safe_output_path(
            source_path=source_path,
            action_suffix="rotated",
            target_ext=".pdf",
            output_directory=output_directory,
        )
        return rotate_pages(source_path, target_path, rotation_delta, page_indices)

    @staticmethod
    def compress(
        source_path: Path,
        preset: CompressionPreset = CompressionPreset.BALANCED,
        output_directory: Optional[Path] = None,
    ) -> Result[Path, DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        target_path = generate_safe_output_path(
            source_path=source_path,
            action_suffix="compressed",
            target_ext=".pdf",
            output_directory=output_directory,
        )
        return compress_pdf(source_path, target_path, preset)

    @staticmethod
    def from_images(
        image_paths: List[Path],
        output_path: Optional[Path] = None,
        page_size_name: str = "A4",
        fit_to_page: bool = True,
    ) -> Result[Path, DocumentError]:
        if not output_path:
            output_path = generate_safe_output_path(
                source_path=image_paths[0],
                action_suffix="from_images",
                target_ext=".pdf",
            )
        return images_to_pdf(image_paths, output_path, page_size_name, fit_to_page)

    @staticmethod
    def to_images(
        source_path: Path,
        output_directory: Optional[Path] = None,
        target_format: ImageFormat = ImageFormat.PNG,
        dpi: int = 150,
        page_indices: Optional[Sequence[int]] = None,
    ) -> Result[List[Path], DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        out_dir = output_directory or source_path.parent
        return pdf_to_images(source_path, out_dir, target_format, dpi, page_indices)

    @staticmethod
    def to_word(
        source_path: Path,
        output_path: Optional[Path] = None,
        output_directory: Optional[Path] = None,
        enable_ocr_fallback: bool = True,
        language: str = "eng",
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Result[Path, DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))

        from offline_toolbox.pdf.word_converter import convert_pdf_to_docx

        target_path = output_path or generate_safe_output_path(
            source_path=source_path,
            action_suffix="converted",
            target_ext=".docx",
            output_directory=output_directory,
        )

        return convert_pdf_to_docx(
            source_path=source_path,
            target_path=target_path,
            enable_ocr_fallback=enable_ocr_fallback,
            language=language,
            progress_callback=progress_callback,
        )

    @staticmethod
    def apply_overlays(
        source_path: Path,
        text_overlays: List[TextOverlay],
        image_overlays: List[ImageOverlay],
        acroform_overlays: Optional[List[AcroformOverlay]] = None,
        target_path: Optional[Path] = None,
    ) -> Result[Path, DocumentError]:
        val = validate_pdf_file(source_path)
        if val.is_err():
            return Err(DocumentError(val.error.message))
        dest = target_path or source_path
        return apply_overlays_to_pdf(source_path, dest, text_overlays, image_overlays, acroform_overlays=acroform_overlays)
