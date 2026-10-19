"""Input validation and security sanitization."""

import os
from pathlib import Path
from typing import List, Union
from offline_toolbox.core.errors import ValidationError
from offline_toolbox.core.result import Err, Ok, Result

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".ico"
}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}


def validate_file_exists(file_path: Union[str, Path]) -> Result[Path, ValidationError]:
    path = Path(file_path).resolve()
    if not path.exists():
        return Err(ValidationError(f"File does not exist: {path}"))
    if not path.is_file():
        return Err(ValidationError(f"Path is not a regular file: {path}"))
    if path.stat().st_size == 0:
        return Err(ValidationError(f"File is zero bytes (empty): {path}"))
    return Ok(path)


def validate_files_exist(file_paths: List[Union[str, Path]]) -> Result[List[Path], ValidationError]:
    if not file_paths:
        return Err(ValidationError("No input files provided"))
    resolved: List[Path] = []
    for fp in file_paths:
        res = validate_file_exists(fp)
        if res.is_err():
            return Err(res.error)
        resolved.append(res.value)
    return Ok(resolved)


def validate_pdf_file(file_path: Union[str, Path]) -> Result[Path, ValidationError]:
    check = validate_file_exists(file_path)
    if check.is_err():
        return check
    path = check.value
    if path.suffix.lower() not in SUPPORTED_PDF_EXTENSIONS:
        return Err(ValidationError(f"File is not a PDF: {path.name}"))
    
    # Check PDF magic header
    try:
        with open(path, "rb") as f:
            header = f.read(5)
            if not header.startswith(b"%PDF-"):
                return Err(ValidationError(f"File lacks valid PDF header signature: {path.name}"))
    except OSError as e:
        return Err(ValidationError(f"Cannot read file {path.name}", str(e)))

    return Ok(path)


def validate_image_file(file_path: Union[str, Path]) -> Result[Path, ValidationError]:
    check = validate_file_exists(file_path)
    if check.is_err():
        return check
    path = check.value
    if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return Err(ValidationError(f"Unsupported image extension: {path.suffix}"))
    return Ok(path)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal and illegal Windows/POSIX characters."""
    bad_chars = '<>:"/\\|?*\0'
    cleaned = "".join(c for c in filename if c not in bad_chars).strip()
    return cleaned or "document"
