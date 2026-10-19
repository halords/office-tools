"""Facade service orchestrating image operations and batch conversions."""

from pathlib import Path
from typing import Callable, List, Optional, Tuple
from offline_toolbox.core.errors import ImageProcessingError
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.core.validators import validate_image_file
from offline_toolbox.filesystem.naming import generate_safe_output_path
from offline_toolbox.images.converter import convert_image


class ImageService:
    """Service layer for image conversions and batch transformations."""

    @staticmethod
    def convert_single(
        source_path: Path,
        target_format: ImageFormat,
        output_directory: Optional[Path] = None,
        quality: int = 90,
        resize_width: Optional[int] = None,
        resize_height: Optional[int] = None,
        preserve_aspect: bool = True,
        strip_metadata: bool = False,
        allow_overwrite: bool = False,
        preset_id: Optional[str] = None,
        crop_to_fill: bool = False,
        offset_x: float = 0.5,
        offset_y: float = 0.5,
        crop_scale: float = 1.0,
        nametag_enabled: bool = False,
        nametag_height_pct: float = 0.18,
        name_text: str = "",
        name_path: Optional[Path] = None,
        name_scale: float = 1.0,
        signature_path: Optional[Path] = None,
        signature_scale: float = 1.0,
        signature_pos_y: float = 0.0,
        remove_bg: bool = False,
        bg_color: Tuple[int, int, int] = (255, 255, 255),
    ) -> Result[Path, ImageProcessingError]:
        val = validate_image_file(source_path)
        if val.is_err():
            return Err(ImageProcessingError(val.error.message))

        ext = f".{target_format.value.lower()}"
        if target_format == ImageFormat.JPEG:
            ext = ".jpg"

        target_path = generate_safe_output_path(
            source_path=source_path,
            action_suffix="converted",
            target_ext=ext,
            output_directory=output_directory,
            allow_overwrite=allow_overwrite,
        )

        return convert_image(
            source_path=source_path,
            target_path=target_path,
            target_format=target_format,
            quality=quality,
            resize_width=resize_width,
            resize_height=resize_height,
            preserve_aspect=preserve_aspect,
            strip_metadata=strip_metadata,
            preset_id=preset_id,
            crop_to_fill=crop_to_fill,
            offset_x=offset_x,
            offset_y=offset_y,
            crop_scale=crop_scale,
            nametag_enabled=nametag_enabled,
            nametag_height_pct=nametag_height_pct,
            name_text=name_text,
            name_path=name_path,
            name_scale=name_scale,
            signature_path=signature_path,
            signature_scale=signature_scale,
            signature_pos_y=signature_pos_y,
            remove_bg=remove_bg,
            bg_color=bg_color,
        )

    @staticmethod
    def batch_convert(
        source_paths: List[Path],
        target_format: ImageFormat,
        output_directory: Path,
        quality: int = 90,
        resize_width: Optional[int] = None,
        resize_height: Optional[int] = None,
        preserve_aspect: bool = True,
        strip_metadata: bool = True,
        preset_id: Optional[str] = None,
        crop_to_fill: bool = False,
        offset_x: float = 0.5,
        offset_y: float = 0.5,
        crop_scale: float = 1.0,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> Result[List[Path], ImageProcessingError]:
        converted: List[Path] = []
        total = len(source_paths)

        for idx, src in enumerate(source_paths, start=1):
            if progress_callback:
                progress_callback(idx, total, src.name)

            res = ImageService.convert_single(
                source_path=src,
                target_format=target_format,
                output_directory=output_directory,
                quality=quality,
                resize_width=resize_width,
                resize_height=resize_height,
                preserve_aspect=preserve_aspect,
                strip_metadata=strip_metadata,
                preset_id=preset_id,
                crop_to_fill=crop_to_fill,
                offset_x=offset_x,
                offset_y=offset_y,
                crop_scale=crop_scale,
            )
            if res.is_ok():
                converted.append(res.value)

        return Ok(converted)
