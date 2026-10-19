"""Non-destructive file naming with collision protection."""

from pathlib import Path


def generate_safe_output_path(
    source_path: Path,
    action_suffix: str = "converted",
    target_ext: str = None,
    output_directory: Path = None,
    allow_overwrite: bool = False,
) -> Path:
    """
    Generates a non-destructive output path.
    Example: report.pdf with action 'compressed' -> report_compressed.pdf
    If collision exists and allow_overwrite is False -> report_compressed (1).pdf
    """
    dir_path = output_directory or source_path.parent
    stem = source_path.stem
    ext = target_ext if target_ext is not None else source_path.suffix
    if not ext.startswith("."):
        ext = f".{ext}"

    base_name = f"{stem}_{action_suffix}" if action_suffix else stem
    candidate = dir_path / f"{base_name}{ext}"

    if allow_overwrite or not candidate.exists():
        return candidate

    counter = 1
    while True:
        candidate = dir_path / f"{base_name} ({counter}){ext}"
        if not candidate.exists():
            return candidate
        counter += 1
