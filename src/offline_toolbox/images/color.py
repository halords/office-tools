"""Image color management, transparency matting, and ICC normalization."""

from typing import Tuple
from PIL import Image, ImageCms


def flatten_alpha(image: Image.Image, matte_color: Tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """
    Flattens RGBA or LA alpha transparency onto a solid color matte background.
    Guarantees compatibility when saving to formats without alpha support (like JPEG).
    """
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        alpha_img = image.convert("RGBA")
        background = Image.new("RGBA", alpha_img.size, matte_color + (255,))
        composite = Image.alpha_composite(background, alpha_img)
        return composite.convert("RGB")
    return image.convert("RGB")


def normalize_color_space(image: Image.Image) -> Image.Image:
    """
    Normalizes CMYK and paletted images to sRGB to avoid inverted or washed out colors.
    """
    if image.mode == "CMYK":
        return image.convert("RGB")
    elif image.mode == "P":
        if "transparency" in image.info:
            return image.convert("RGBA")
        return image.convert("RGB")
    elif image.mode == "1":
        return image.convert("L")
    return image
