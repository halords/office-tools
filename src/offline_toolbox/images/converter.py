"""Pillow-based high-performance image transformations."""

from pathlib import Path
from typing import List, Optional, Tuple, Union
from PIL import Image, ImageOps
from offline_toolbox.core.errors import ImageProcessingError
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.core.result import Err, Ok, Result
from offline_toolbox.images.color import flatten_alpha, normalize_color_space


def load_image(image_path: Path) -> Result[Image.Image, ImageProcessingError]:
    try:
        img = Image.open(image_path)
        img.load()  # Force reading into memory
        return Ok(img)
    except Exception as e:
        return Err(ImageProcessingError(f"Failed to load image: {image_path.name}", str(e)))


def resize_image(
    image: Image.Image,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    preserve_aspect: bool = True,
    resample_filter=Image.Resampling.LANCZOS,
) -> Image.Image:
    orig_w, orig_h = image.size
    if not target_width and not target_height:
        return image

    if preserve_aspect:
        if target_width and target_height:
            scale = min(target_width / orig_w, target_height / orig_h)
        elif target_width:
            scale = target_width / orig_w
        else:
            scale = target_height / orig_h
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))
    else:
        new_w = target_width if target_width else orig_w
        new_h = target_height if target_height else orig_h

    return image.resize((new_w, new_h), resample=resample_filter)


def rotate_image(image: Image.Image, degrees: int, expand: bool = True) -> Image.Image:
    """Rotates image by specified degrees (e.g. 90, 180, 270)."""
    return image.rotate(degrees, expand=expand)


def flip_image(image: Image.Image, horizontal: bool = False, vertical: bool = False) -> Image.Image:
    res = image
    if horizontal:
        res = ImageOps.mirror(res)
    if vertical:
        res = ImageOps.flip(res)
    return res


def crop_image(image: Image.Image, box: Tuple[int, int, int, int]) -> Image.Image:
    """Crop bounding box: (left, top, right, bottom)."""
    return image.crop(box)


from offline_toolbox.images.presets import PHOTO_PRESETS, fit_image_to_preset


def convert_image(
    source_path: Path,
    target_path: Path,
    target_format: ImageFormat,
    quality: int = 90,
    resize_width: Optional[int] = None,
    resize_height: Optional[int] = None,
    preserve_aspect: bool = True,
    strip_metadata: bool = False,
    ico_sizes: Optional[List[Tuple[int, int]]] = None,
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
    """Converts image with robust format translation, photo presets, and error handling."""
    load_res = load_image(source_path)
    if load_res.is_err():
        return load_res

    image = load_res.value

    # Apply background removal if requested (default white, or custom background color)
    if remove_bg:
        from offline_toolbox.images.bg_remover import remove_background
        image = remove_background(image, bg_color=bg_color)

    # Load handwritten name overlay if provided
    name_img = None
    if name_path and name_path.exists():
        name_load = load_image(name_path)
        if name_load.is_ok():
            name_img = name_load.value

    # Load signature overlay if provided
    sig_img = None
    if signature_path and signature_path.exists():
        sig_load = load_image(signature_path)
        if sig_load.is_ok():
            sig_img = sig_load.value

    try:
        # Standardize color space
        image = normalize_color_space(image)

        # Apply photo preset sizing if requested (e.g. 2x2, Passport, 4R)
        if preset_id and preset_id in PHOTO_PRESETS:
            preset = PHOTO_PRESETS[preset_id]
            image = fit_image_to_preset(
                image,
                target_width=preset.width_px,
                target_height=preset.height_px,
                fill_color=bg_color,
                crop_to_fill=crop_to_fill,
                offset_x=offset_x,
                offset_y=offset_y,
                crop_scale=crop_scale,
                nametag_enabled=nametag_enabled,
                nametag_height_pct=nametag_height_pct,
                name_text=name_text,
                name_image=name_img,
                name_scale=name_scale,
                signature_image=sig_img,
                signature_scale=signature_scale,
                signature_pos_y=signature_pos_y,
            )
        # Apply manual resizing if requested
        elif resize_width or resize_height:
            image = resize_image(image, resize_width, resize_height, preserve_aspect)

        target_path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs = {}

        if target_format == ImageFormat.JPEG:
            # Flatten alpha before JPEG export
            image = flatten_alpha(image)
            save_kwargs["format"] = "JPEG"
            save_kwargs["quality"] = max(1, min(quality, 100))
            save_kwargs["optimize"] = True

        elif target_format == ImageFormat.PNG:
            save_kwargs["format"] = "PNG"
            save_kwargs["optimize"] = True

        elif target_format == ImageFormat.WEBP:
            save_kwargs["format"] = "WEBP"
            save_kwargs["quality"] = max(1, min(quality, 100))

        elif target_format == ImageFormat.BMP:
            if image.mode == "RGBA":
                image = flatten_alpha(image)
            save_kwargs["format"] = "BMP"

        elif target_format == ImageFormat.TIFF:
            save_kwargs["format"] = "TIFF"
            save_kwargs["compression"] = "tiff_lzw"

        elif target_format == ImageFormat.ICO:
            # Multi-resolution ICO generation
            sizes = ico_sizes or [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            save_kwargs["format"] = "ICO"
            save_kwargs["sizes"] = sizes

        if strip_metadata:
            # Strip EXIF / ICC chunks by creating fresh image object
            clean_img = Image.new(image.mode, image.size)
            clean_img.putdata(list(image.getdata()))
            image = clean_img

        image.save(target_path, **save_kwargs)
        return Ok(target_path)

    except Exception as e:
        return Err(ImageProcessingError(f"Failed to convert image {source_path.name}", str(e)))
