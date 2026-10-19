"""Photoshop-style signature and ink background extraction engine.

Removes white paper backgrounds using Curves / Levels (Ctrl+M in Photoshop) and converts
uneven shadows to pure white while pushing ink contrast to dark, crisp lines with full alpha transparency.
"""

from typing import Optional, Tuple
from PIL import Image, ImageOps
import numpy as np


def clean_signature_and_remove_white(
    image: Image.Image,
    white_cutoff: int = 215,     # Pixels >= white_cutoff become 100% transparent paper
    black_cutoff: int = 80,      # Pixels <= black_cutoff become 100% solid dark ink
    ink_color: Optional[Tuple[int, int, int]] = None,  # If None, retains original ink hue/saturation
    deepen_ink: bool = True,     # Push dark pixels to deep solid ink
) -> Image.Image:
    """
    Simulates Photoshop's Curves (Ctrl+M) + Multiply transparency.
    
    1. Grayscale luminance calculation.
    2. Levels / Curves expansion:
       - Bright paper and ambient shadows (>= white_cutoff) are clipped to 255 (white).
       - Dark ink (<= black_cutoff) is clipped to 0 (black).
       - Intermediate pixels are smoothed with a high-contrast curve.
    3. Alpha channel calculation:
       - Pure white becomes 100% transparent (alpha = 0).
       - Dark ink becomes opaque (alpha = 255).
       - Anti-aliased edges retain smooth alpha blending so text doesn't look pixelated.
    4. Color handling:
       - If ink_color is provided (e.g. (0, 0, 0) for deep black, or (0, 35, 120) for royal blue),
         fills ink lines cleanly with that color.
       - If None, retains the original photo colors while applying the alpha mask.
    """
    # Ensure source has RGB
    if image.mode != "RGB" and image.mode != "RGBA":
        rgb_img = image.convert("RGB")
    else:
        rgb_img = image.convert("RGBA") if image.mode == "RGBA" else image

    # 1. Grayscale luminance analysis
    gray = image.convert("L")
    gray_arr = np.array(gray, dtype=np.float32)

    # 2. Levels / Curves remap (Ctrl+M equivalent)
    # Clamp bounds
    w_cut = max(50.0, min(255.0, float(white_cutoff)))
    b_cut = max(0.0, min(w_cut - 5.0, float(black_cutoff)))

    # Rescale luminance: b_cut -> 0.0, w_cut -> 1.0
    normalized = np.clip((gray_arr - b_cut) / (w_cut - b_cut), 0.0, 1.0)
    
    # Apply S-curve contrast to deepen ink strokes and clean paper
    # normalized ** 1.3 pushes mid-tones closer to dark while keeping paper pure white
    curved = np.power(normalized, 1.4)

    # Alpha mask: 1.0 - curved (so 1.0 = opaque ink, 0.0 = transparent paper)
    alpha_arr = (1.0 - curved) * 255.0
    alpha_arr = np.clip(alpha_arr, 0.0, 255.0).astype(np.uint8)
    alpha_mask = Image.fromarray(alpha_arr, mode="L")

    # 3. Assemble resulting RGBA image
    if ink_color is not None:
        # Uniform solid ink color with smooth alpha mask
        r_c, g_c, b_c = ink_color
        solid_r = Image.new("L", image.size, r_c)
        solid_g = Image.new("L", image.size, g_c)
        solid_b = Image.new("L", image.size, b_c)
        return Image.merge("RGBA", (solid_r, solid_g, solid_b, alpha_mask))
    else:
        # Retain original ink color, but optionally darken ink strokes for high fidelity
        if rgb_img.mode == "RGBA":
            orig_r, orig_g, orig_b, orig_a = rgb_img.split()
            # Combined alpha: min of original alpha and newly extracted paper alpha
            final_alpha = ImageOps.invert(Image.fromarray(
                np.maximum(255 - np.array(orig_a), 255 - alpha_arr).astype(np.uint8), mode="L"
            ))
        else:
            orig_r, orig_g, orig_b = rgb_img.split()
            final_alpha = alpha_mask

        if deepen_ink:
            # Contrast boost on RGB channels to eliminate faded scanner haze
            r_arr = np.array(orig_r, dtype=np.float32)
            g_arr = np.array(orig_g, dtype=np.float32)
            b_arr = np.array(orig_b, dtype=np.float32)

            # Darken darker pixels toward rich ink
            factor = np.clip(gray_arr / w_cut, 0.0, 1.0)
            r_dark = np.clip(r_arr * factor, 0.0, 255.0).astype(np.uint8)
            g_dark = np.clip(g_arr * factor, 0.0, 255.0).astype(np.uint8)
            b_dark = np.clip(b_arr * factor, 0.0, 255.0).astype(np.uint8)

            return Image.merge("RGBA", (
                Image.fromarray(r_dark, mode="L"),
                Image.fromarray(g_dark, mode="L"),
                Image.fromarray(b_dark, mode="L"),
                final_alpha,
            ))
        else:
            return Image.merge("RGBA", (orig_r, orig_g, orig_b, final_alpha))
