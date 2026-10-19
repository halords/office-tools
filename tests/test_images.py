import pytest
from pathlib import Path
from PIL import Image
from offline_toolbox.core.models import ImageFormat
from offline_toolbox.images.service import ImageService
from offline_toolbox.images.color import flatten_alpha


def test_flatten_alpha():
    rgba_img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    rgb_img = flatten_alpha(rgba_img, matte_color=(255, 255, 255))
    assert rgb_img.mode == "RGB"
    assert rgb_img.size == (100, 100)


def test_image_conversion_formats(tmp_path):
    # Create test PNG with transparency
    src_png = tmp_path / "sample.png"
    img = Image.new("RGBA", (200, 150), (10, 150, 250, 200))
    img.save(src_png)

    # 1. Convert to JPEG (requires alpha flattening)
    res_jpg = ImageService.convert_single(
        source_path=src_png,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
    )
    assert res_jpg.is_ok()
    assert res_jpg.value.exists()
    assert res_jpg.value.suffix == ".jpg"
    with Image.open(res_jpg.value) as check_jpg:
        assert check_jpg.format == "JPEG"

    # 2. Convert to WebP
    res_webp = ImageService.convert_single(
        source_path=src_png,
        target_format=ImageFormat.WEBP,
        output_directory=tmp_path,
    )
    assert res_webp.is_ok()
    assert res_webp.value.exists()
    with Image.open(res_webp.value) as check_webp:
        assert check_webp.format == "WEBP"

    # 3. Multi-resolution ICO
    res_ico = ImageService.convert_single(
        source_path=src_png,
        target_format=ImageFormat.ICO,
        output_directory=tmp_path,
    )
    assert res_ico.is_ok()
    assert res_ico.value.exists()


def test_photo_presets(tmp_path):
    from offline_toolbox.images.presets import PHOTO_PRESETS

    src_img = tmp_path / "portrait.jpg"
    img = Image.new("RGB", (1200, 1600), (200, 180, 160))
    img.save(src_img)

    # Convert to 2x2 inches (600x600 px)
    res_2x2 = ImageService.convert_single(
        source_path=src_img,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
        preset_id="2x2",
        crop_to_fill=True,
    )
    assert res_2x2.is_ok()
    with Image.open(res_2x2.value) as check_2x2:
        assert check_2x2.size == (600, 600)

    # Convert to 2x2 with framing scale / zoom in (1.8x)
    res_2x2_scaled = ImageService.convert_single(
        source_path=src_img,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
        preset_id="2x2",
        crop_to_fill=True,
        crop_scale=1.8,
        offset_y=0.2,
    )
    assert res_2x2_scaled.is_ok()
    with Image.open(res_2x2_scaled.value) as check_scaled:
        assert check_scaled.size == (600, 600)

    # Convert to 4R (1200x1800 px)
    res_4r = ImageService.convert_single(
        source_path=src_img,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
        preset_id="4r",
        crop_to_fill=True,
    )
    assert res_4r.is_ok()
    with Image.open(res_4r.value) as check_4r:
        assert check_4r.size == (1200, 1800)


def test_signature_extraction(tmp_path):
    from offline_toolbox.images.signature import clean_signature_and_remove_white

    # Create synthetic signature on white/cream paper
    paper_img = Image.new("RGB", (300, 150), (240, 240, 235))
    for x in range(50, 250):
        paper_img.putpixel((x, 75), (20, 30, 70))  # Dark ink line

    cleaned = clean_signature_and_remove_white(
        paper_img,
        white_cutoff=210,
        black_cutoff=80,
        ink_color=(0, 0, 0),
    )
    assert cleaned.mode == "RGBA"
    # Paper pixel is transparent
    assert cleaned.getpixel((10, 10))[3] == 0
    # Ink stroke is solid
    assert cleaned.getpixel((100, 75))[3] == 255
    assert cleaned.getpixel((100, 75))[:3] == (0, 0, 0)


def test_photo_preset_with_dedicated_nametag_and_signature(tmp_path):
    src_img = tmp_path / "photo_for_id.jpg"
    img = Image.new("RGB", (1000, 1200), (210, 190, 170))
    img.save(src_img)

    sig_img = tmp_path / "sig.png"
    sig = Image.new("RGBA", (200, 50), (0, 0, 0, 255))
    sig.save(sig_img)

    res = ImageService.convert_single(
        source_path=src_img,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
        preset_id="2x2",
        crop_to_fill=True,
        crop_scale=1.5,
        nametag_enabled=True,
        nametag_height_pct=0.18,
        name_text="JUAN DELA CRUZ",
        signature_path=sig_img,
    )
    assert res.is_ok()
    assert res.value.exists()
    with Image.open(res.value) as check_img:
        # Full 2x2 dimensions (600x600 px) preserved
        assert check_img.size == (600, 600)
        # Check that bottom white space has white background pixels near bottom-left edge
        assert check_img.getpixel((10, 580)) == (255, 255, 255)


def test_bg_removal_and_dual_upload_nametag(tmp_path):
    from offline_toolbox.images.bg_remover import remove_background

    # 1. Test background removal engine with custom blue color
    test_portrait = Image.new("RGB", (200, 200), (120, 120, 120))
    # Fill center with foreground skin tone
    for y in range(40, 160):
        for x in range(40, 160):
            test_portrait.putpixel((x, y), (230, 190, 160))

    blue_bg = (29, 78, 216)
    bg_removed = remove_background(test_portrait, bg_color=blue_bg)
    assert bg_removed.size == (200, 200)
    assert bg_removed.mode == "RGB"

    # 2. Test dual upload: handwritten name image + signature image with scaling
    name_img_path = tmp_path / "handwritten_name.png"
    name_img = Image.new("RGBA", (300, 60), (0, 0, 0, 255))
    name_img.save(name_img_path)

    sig_img_path = tmp_path / "signature.png"
    sig_img = Image.new("RGBA", (250, 70), (10, 20, 150, 255))
    sig_img.save(sig_img_path)

    photo_path = tmp_path / "id_photo.jpg"
    photo = Image.new("RGB", (800, 1000), (220, 220, 220))
    photo.save(photo_path)

    res = ImageService.convert_single(
        source_path=photo_path,
        target_format=ImageFormat.JPEG,
        output_directory=tmp_path,
        preset_id="2x2",
        crop_to_fill=True,
        crop_scale=1.6,
        remove_bg=True,
        bg_color=(255, 255, 255),
        nametag_enabled=True,
        nametag_height_pct=0.18,
        name_path=name_img_path,
        name_scale=1.2,
        signature_path=sig_img_path,
        signature_scale=1.3,
        signature_pos_y=-0.2,
    )
    assert res.is_ok()
    assert res.value.exists()
    with Image.open(res.value) as check_img:
        assert check_img.size == (600, 600)


def test_passport_preset_layering_and_fit_width(tmp_path):
    from offline_toolbox.images.presets import fit_image_to_preset, PHOTO_PRESETS

    # Create a 2x2 square photo (600 x 600)
    square_2x2 = Image.new("RGB", (600, 600), (210, 190, 170))
    preset = PHOTO_PRESETS["passport_35x45"]  # 413 x 531 px

    # Test layering on passport: fit to width with nametag enabled and signature
    sig_img = Image.new("RGBA", (200, 50), (10, 20, 150, 255))

    passport_out = fit_image_to_preset(
        square_2x2,
        target_width=preset.width_px,
        target_height=preset.height_px,
        crop_to_fill=True,
        crop_scale=1.0,
        nametag_enabled=True,
        nametag_height_pct=0.18,
        name_text="JUAN DELA CRUZ",
        name_scale=1.0,
        signature_image=sig_img,
        signature_scale=1.0,
        signature_pos_y=0.0,
    )

    assert passport_out.size == (preset.width_px, preset.height_px)
    assert passport_out.size == (413, 531)
    # Banner area at the bottom should be crisp white (255, 255, 255)
    assert passport_out.getpixel((10, 520)) == (255, 255, 255)




