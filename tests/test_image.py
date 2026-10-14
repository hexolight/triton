from PIL import Image

from app.converters import image


def test_transparent_png_to_jpg_is_flattened_on_white(tmp_path):
    src, dst = tmp_path / "a.png", tmp_path / "a.jpg"
    Image.new("RGBA", (16, 16), (255, 0, 0, 0)).save(src)  # fully transparent red
    image.convert(src, dst)
    r, g, b = Image.open(dst).convert("RGB").getpixel((8, 8))
    assert min(r, g, b) > 240


def test_palette_png_with_transparency_to_jpg_is_flattened_on_white(tmp_path):
    src, dst = tmp_path / "p.png", tmp_path / "p.jpg"
    im = Image.new("P", (16, 16), 0)
    im.putpalette([255, 0, 0] + [0, 0, 0] * 255)
    im.info["transparency"] = 0
    im.save(src, transparency=0)
    image.convert(src, dst)
    assert min(Image.open(dst).convert("RGB").getpixel((8, 8))) > 240


def test_exif_orientation_is_applied(tmp_path):
    src, dst = tmp_path / "r.jpg", tmp_path / "r.png"
    im = Image.new("RGB", (60, 20), (0, 0, 255))
    exif = im.getexif()
    exif[0x0112] = 6  # rotate 90 degrees when displayed
    im.save(src, exif=exif)
    image.convert(src, dst)
    assert Image.open(dst).size == (20, 60)


def test_cmyk_tiff_to_png(tmp_path):
    src, dst = tmp_path / "c.tiff", tmp_path / "c.png"
    Image.new("CMYK", (8, 8)).save(src)
    image.convert(src, dst)
    assert Image.open(dst).mode == "RGB"


def test_cmyk_tiff_to_jpg_becomes_rgb(tmp_path):
    src, dst = tmp_path / "c.tiff", tmp_path / "c.jpg"
    Image.new("CMYK", (8, 8)).save(src)
    image.convert(src, dst)
    assert Image.open(dst).mode == "RGB"
