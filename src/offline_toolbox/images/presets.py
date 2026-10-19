"""Standard photo size presets for government IDs, visas, and photo prints (300 DPI standard)."""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class PhotoPreset:
    id: str
    name: str
    category: str
    width_px: int
    height_px: int
    dpi: int = 300
    description: str = ""
    crop_aspect_ratio: Optional[float] = None

    @property
    def aspect_ratio(self) -> float:
        if self.crop_aspect_ratio is not None:
            return self.crop_aspect_ratio
        return self.width_px / float(self.height_px)


# Standard photo presets at 300 DPI (standard print resolution)
PHOTO_PRESETS: Dict[str, PhotoPreset] = {
    "2x2": PhotoPreset(
        id="2x2",
        name="2 x 2 inches (51 x 51 mm)",
        category="Government & ID",
        width_px=600,
        height_px=600,
        description="Philippine Passport, US Visa, PRC, Civil Service, Driver's License, SSS, NBI",
    ),
    "passport_35x45": PhotoPreset(
        id="passport_35x45",
        name="Passport 35 x 45 mm (Full Frame)",
        category="Government & ID",
        width_px=413,
        height_px=531,
        description="International Passport, Schengen Visa, Canada, UK, Australian Visa standard",
    ),
    "passport_2x2_embed": PhotoPreset(
        id="passport_2x2_embed",
        name="Passport 35 x 45 mm (Embed 2x2 crop)",
        category="Government & ID",
        width_px=413,
        height_px=531,
        crop_aspect_ratio=1.0,
        description="Pads a 2x2 square crop into a 35x45mm passport size",
    ),
    "1x1": PhotoPreset(
        id="1x1",
        name="1 x 1 inch (25 x 25 mm)",
        category="Government & ID",
        width_px=300,
        height_px=300,
        description="Student IDs, PhilHealth, Postal ID, Barangay Clearance, Employment records",
    ),
    "passport_ph_old": PhotoPreset(
        id="passport_ph_old",
        name="Philippine ID (35 x 45 mm)",
        category="Government & ID",
        width_px=413,
        height_px=531,
        description="35mm x 45mm standard photo with white background",
    ),
    "4r": PhotoPreset(
        id="4r",
        name="4R (4 x 6 inches / 102 x 152 mm)",
        category="Standard Photo Print",
        width_px=1200,
        height_px=1800,
        description="Standard 4R physical print (portrait 4x6)",
    ),
    "4r_landscape": PhotoPreset(
        id="4r_landscape",
        name="4R Landscape (6 x 4 inches / 152 x 102 mm)",
        category="Standard Photo Print",
        width_px=1800,
        height_px=1200,
        description="Standard 4R physical print (landscape 6x4)",
    ),
    "3r": PhotoPreset(
        id="3r",
        name="3R (3.5 x 5 inches / 89 x 127 mm)",
        category="Standard Photo Print",
        width_px=1050,
        height_px=1500,
        description="Standard 3R photo print",
    ),
    "5r": PhotoPreset(
        id="5r",
        name="5R (5 x 7 inches / 127 x 178 mm)",
        category="Standard Photo Print",
        width_px=1500,
        height_px=2100,
        description="Framed portrait / formal photo print",
    ),
    "wallet": PhotoPreset(
        id="wallet",
        name="Wallet Size (2.5 x 3.5 inches)",
        category="Standard Photo Print",
        width_px=750,
        height_px=1050,
        description="Mini wallet sized photo",
    ),
}


def fit_image_to_preset(
    image: Image.Image,
    target_width: int,
    target_height: int,
    fill_color: Tuple[int, int, int] = (255, 255, 255),
    crop_to_fill: bool = False,
    offset_x: float = 0.5,  # 0.0 = left, 0.5 = center, 1.0 = right
    offset_y: float = 0.5,  # 0.0 = top, 0.5 = center, 1.0 = bottom
    crop_scale: float = 1.0,  # 1.0 = full fit, >1.0 = zoom in (e.g. 1.5x, 2.0x for framing face in 2x2)
    nametag_enabled: bool = False,
    nametag_height_pct: float = 0.18,  # Height percentage dedicated to white space (typically 15% - 22% for 2x2)
    name_text: str = "",
    name_image: Optional[Image.Image] = None,
    name_scale: float = 1.0,  # 0.5x to 2.0x scale
    signature_image: Optional[Image.Image] = None,
    signature_scale: float = 1.0,  # 0.5x to 2.5x scale
    signature_pos_y: float = 0.0,  # -1.0 to 1.0 vertical adjustment within banner
    exact_crop_box: Optional[Tuple[int, int, int, int]] = None,
    align_top: bool = False,  # If True, pin cropped image to top; white space fills below (passport 2x2 embed)
) -> Image.Image:
    """
    Fits an image to the exact preset dimensions.
    
    - If exact_crop_box (left, top, right, bottom) is passed:
        Crops precisely the coordinates framed on the interactive canvas for 100% WYSIWYG accuracy.
    - If nametag_enabled is True:
        Reserves a dedicated crisp white space banner at the bottom of the photo
        (standard requirement for Philippine Civil Service Commission, PRC, and government 2x2 IDs).
        The photo content is framed and cropped strictly inside the upper region,
        leaving the bottom space 100% clean white for the handwritten/typed name and signature.
    - If crop_to_fill is True:
        crop_scale and offsets position and scale the subject.
    - If crop_to_fill is False:
        Pads the remainder with fill_color.
    """
    orig_w, orig_h = image.size

    # Calculate effective photo viewport height
    if nametag_enabled:
        banner_h = max(24, int(round(target_height * max(0.10, min(0.35, nametag_height_pct)))))
        photo_h = target_height - banner_h
    else:
        banner_h = 0
        photo_h = target_height

    photo_w = target_width

    if exact_crop_box is not None:
        # 100% WYSIWYG: Crop exactly what the user saw in the canvas crop box
        c_left, c_top, c_right, c_bottom = exact_crop_box
        box_w = c_right - c_left
        box_h = c_bottom - c_top

        # Create a new padded canvas using fill_color
        canvas_mode = "RGB" if image.mode != "RGBA" else "RGBA"
        bg_color = fill_color if canvas_mode == "RGB" else (fill_color[0], fill_color[1], fill_color[2], 255)
        padded_crop = Image.new(canvas_mode, (box_w, box_h), color=bg_color)

        # Paste the original image onto it. 
        # If crop box is outside image bounds, this perfectly pads it.
        padded_crop.paste(image, (-c_left, -c_top))
        
        c_w, c_h = padded_crop.size
        scale = min(photo_w / float(c_w), photo_h / float(c_h))
        new_w = max(1, int(round(c_w * scale)))
        new_h = max(1, int(round(c_h * scale)))
        
        scaled = padded_crop.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        
        rendered_photo = Image.new(canvas_mode, (photo_w, photo_h), color=bg_color)
        
        paste_x = (photo_w - new_w) // 2
        paste_y = 0 if align_top else (photo_h - new_h) // 2
        rendered_photo.paste(scaled, (paste_x, paste_y))
    elif crop_to_fill:
        target_aspect = photo_w / float(photo_h)
        image_aspect = orig_w / float(orig_h)

        if image_aspect > target_aspect:
            base_box_h = float(orig_h)
            base_box_w = base_box_h * target_aspect
        else:
            base_box_w = float(orig_w)
            base_box_h = base_box_w / target_aspect

        safe_scale = max(0.2, min(5.0, float(crop_scale)))
        box_w = min(float(orig_w), base_box_w / safe_scale)
        box_h = min(float(orig_h), base_box_h / safe_scale)

        max_x = max(0.0, float(orig_w) - box_w)
        max_y = max(0.0, float(orig_h) - box_h)

        clamped_ox = max(0.0, min(1.0, float(offset_x)))
        clamped_oy = max(0.0, min(1.0, float(offset_y)))

        left = int(round(max_x * clamped_ox))
        top = int(round(max_y * clamped_oy))
        right = min(orig_w, int(round(left + box_w)))
        bottom = min(orig_h, int(round(top + box_h)))

        cropped = image.crop((left, top, right, bottom))
        
        # If crop_to_fill is set but the target crop aspect ratio differs from the final canvas aspect ratio,
        # we resize it to fit within the canvas and pad it.
        c_w, c_h = cropped.size
        scale = min(photo_w / float(c_w), photo_h / float(c_h))
        new_w = max(1, int(round(c_w * scale)))
        new_h = max(1, int(round(c_h * scale)))
        
        scaled = cropped.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)
        
        canvas_mode = "RGB" if image.mode != "RGBA" else "RGBA"
        bg_color = fill_color if canvas_mode == "RGB" else (fill_color[0], fill_color[1], fill_color[2], 255)
        rendered_photo = Image.new(canvas_mode, (photo_w, photo_h), color=bg_color)

        paste_x = (photo_w - new_w) // 2
        paste_y = (photo_h - new_h) // 2
        rendered_photo.paste(scaled, (paste_x, paste_y))
    else:
        scale = min(photo_w / float(orig_w), photo_h / float(orig_h))
        new_w = max(1, int(round(orig_w * scale)))
        new_h = max(1, int(round(orig_h * scale)))
        scaled = image.resize((new_w, new_h), resample=Image.Resampling.LANCZOS)

        canvas_mode = "RGB" if image.mode != "RGBA" else "RGBA"
        bg_color = fill_color if canvas_mode == "RGB" else (fill_color[0], fill_color[1], fill_color[2], 255)
        rendered_photo = Image.new(canvas_mode, (photo_w, photo_h), color=bg_color)

        paste_x = (photo_w - new_w) // 2
        paste_y = (photo_h - new_h) // 2
        if scaled.mode == "RGBA":
            rendered_photo.paste(scaled, (paste_x, paste_y), scaled)
        else:
            rendered_photo.paste(scaled, (paste_x, paste_y))

    # If no dedicated white space nametag, return rendered photo directly
    if not nametag_enabled:
        return rendered_photo

    # Assemble composite with dedicated white space banner at the bottom
    canvas_mode = "RGB" if image.mode != "RGBA" else "RGBA"
    final_canvas = Image.new(canvas_mode, (target_width, target_height), color=(255, 255, 255))
    final_canvas.paste(rendered_photo, (0, 0))

    banner_top = photo_h
    banner_rect = (0, banner_top, target_width, target_height)
    draw = ImageDraw.Draw(final_canvas)
    
    # Crisp white background for banner with clean hairline boundary
    draw.rectangle(banner_rect, fill=(255, 255, 255))
    draw.line([(0, banner_top), (target_width, banner_top)], fill=(220, 220, 220), width=1)

    has_name = bool(name_text.strip() or name_image)

    # 1. Composite Name (Typed or Handwritten Image)
    name_rendered_h = 0
    if name_image is not None:
        # Handwritten name image
        n_img = name_image.convert("RGBA")
        nw, nh = n_img.size
        target_nw = int(target_width * 0.85 * max(0.4, min(1.8, name_scale)))
        target_nh = int(banner_h * 0.38 * max(0.4, min(1.8, name_scale)))
        n_ratio = min(target_nw / float(nw), target_nh / float(nh))
        final_nw = max(1, int(round(nw * n_ratio)))
        final_nh = max(1, int(round(nh * n_ratio)))
        n_resized = n_img.resize((final_nw, final_nh), resample=Image.Resampling.LANCZOS)
        
        nx = (target_width - final_nw) // 2
        ny = target_height - final_nh - max(4, int(banner_h * 0.08))
        final_canvas.paste(n_resized, (nx, ny), n_resized)
        name_rendered_h = final_nh
    elif name_text.strip():
        # Typed name text with scalable font size
        font = None
        base_size = int(banner_h * 0.26 * max(0.4, min(2.0, name_scale)))
        font_size = max(10, base_size)
        for font_name in ["arialbd.ttf", "arial.ttf", "calibri.ttf", "segoeui.ttf"]:
            try:
                font = ImageFont.truetype(font_name, font_size)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()

        text_to_draw = name_text.strip().upper()
        bbox = draw.textbbox((0, 0), text_to_draw, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        tx = (target_width - tw) // 2
        ty = target_height - th - max(4, int(banner_h * 0.10))
        draw.text((tx, ty), text_to_draw, fill=(0, 0, 0), font=font)
        name_rendered_h = th

    # 2. Composite Signature (scalable and positionable)
    if signature_image:
        sig = signature_image.convert("RGBA")
        sig_w, sig_h = sig.size
        
        # Available area for signature
        avail_w = int(target_width * 0.85 * max(0.3, min(2.5, signature_scale)))
        base_avail_h = (banner_h - name_rendered_h - 6) if has_name else int(banner_h * 0.85)
        avail_h = int(max(10, base_avail_h) * max(0.3, min(2.5, signature_scale)))
        
        sig_ratio = min(avail_w / float(sig_w), avail_h / float(sig_h))
        new_sw = max(1, int(round(sig_w * sig_ratio)))
        new_sh = max(1, int(round(sig_h * sig_ratio)))
        sig_resized = sig.resize((new_sw, new_sh), resample=Image.Resampling.LANCZOS)

        sig_x = (target_width - new_sw) // 2
        
        # Base Y position in the upper portion of banner
        base_y = banner_top + 3 if has_name else banner_top + (banner_h - new_sh) // 2
        # signature_pos_y ranges from -1.0 (higher) to +1.0 (lower)
        y_nudge = int(signature_pos_y * (banner_h * 0.25))
        sig_y = max(banner_top - int(new_sh * 0.3), min(target_height - new_sh, base_y + y_nudge))

        final_canvas.paste(sig_resized, (sig_x, sig_y), sig_resized)

    return final_canvas
