"""Image <-> image conversion via Pillow."""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageOps

from app.i18n import t

# Pillow needs RGB (no alpha) for these formats
_NO_ALPHA = {"jpg", "jpeg", "bmp"}

# colour models most output formats can't store; converted to RGB first
_NEEDS_RGB = {"CMYK", "YCbCr", "LAB", "HSV"}

_SAVE_FORMAT = {
    "jpg": "JPEG",
    "jpeg": "JPEG",
    "png": "PNG",
    "webp": "WEBP",
    "bmp": "BMP",
    "gif": "GIF",
    "tiff": "TIFF",
    "ico": "ICO",
}


def has_alpha(im: Image.Image) -> bool:
    return im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info


def flatten_to_rgb(im: Image.Image) -> Image.Image:
    """RGB copy of `im`; transparent areas become white (a plain
    convert("RGB") leaves whatever colour is hidden under the alpha)."""
    if has_alpha(im):
        rgba = im.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return im.convert("RGB")


def prepare(im: Image.Image) -> Image.Image:
    """Apply the EXIF orientation so photos don't come out rotated once the
    metadata is dropped on save."""
    return ImageOps.exif_transpose(im)


def convert(src: Path, dst: Path) -> None:
    dst_ext = dst.suffix.lower().lstrip(".")
    fmt = _SAVE_FORMAT.get(dst_ext)
    if not fmt:
        raise RuntimeError(t("err_unsupported_image_format", ext=dst_ext))

    with Image.open(src) as opened:
        im = prepare(opened)

        if dst_ext in _NO_ALPHA:
            if has_alpha(im) or im.mode not in ("RGB", "L"):
                im = flatten_to_rgb(im)
        elif im.mode in _NEEDS_RGB and fmt != "TIFF":
            im = im.convert("RGB")
        elif im.mode == "P" and dst_ext not in ("gif", "ico"):
            im = im.convert("RGBA")

        save_kwargs = {}
        if fmt == "JPEG":
            save_kwargs["quality"] = 95
        if fmt == "ICO":
            save_kwargs["sizes"] = [(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)]

        im.save(dst, fmt, **save_kwargs)
