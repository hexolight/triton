"""One-off script: crop the new lightning-bolt logo, round its corners for
in-app display, and build a multi-size .ico. Not part of the shipped app."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

# The source is a two-colour mark (green field, white bolt). Recolour it into
# the app palette (emerald ink / champagne) by interpolating between the two.
SRC_FIELD_R, SRC_BOLT_R = 62, 255
EMERALD = np.array((31, 143, 107), dtype=float)
CHAMPAGNE = np.array((238, 221, 174), dtype=float)


def recolor(img: Image.Image) -> Image.Image:
    a = np.asarray(img.convert("RGBA")).astype(float)
    t = np.clip((a[..., 0] - SRC_FIELD_R) / (SRC_BOLT_R - SRC_FIELD_R), 0, 1)[..., None]
    rgb = EMERALD * (1 - t) + CHAMPAGNE * t
    return Image.fromarray(np.concatenate([rgb, a[..., 3:4]], axis=-1).astype("uint8"), "RGBA")


SRC = Path(__file__).parent / "logo_source.png"
OUT_SQUARE = Path(__file__).parent / "logo_square.png"
OUT_ROUNDED = Path(__file__).parent / "logo.png"
OUT_ICO = Path(__file__).parent / "app.ico"

im = Image.open(SRC).convert("RGBA")
bbox = im.split()[-1].getbbox()
im = im.crop(bbox)

# make sure it's a perfect square (pad the shorter side with the bg green)
w, h = im.size
bg = im.getpixel((2, 2))
side = max(w, h)
square = Image.new("RGBA", (side, side), bg)
square.paste(im, ((side - w) // 2, (side - h) // 2))
square = recolor(square)
square.save(OUT_SQUARE)
print("square saved", square.size)

# rounded-corner version for in-app header/list use
radius = int(side * 0.22)
mask = Image.new("L", (side, side), 0)
draw = ImageDraw.Draw(mask)
draw.rounded_rectangle([0, 0, side - 1, side - 1], radius=radius, fill=255)
rounded = Image.new("RGBA", (side, side), (0, 0, 0, 0))
rounded.paste(square, (0, 0), mask)
rounded.save(OUT_ROUNDED)
print("rounded saved", rounded.size)

icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
rounded.save(OUT_ICO, format="ICO", sizes=icon_sizes)
print("ico saved (rounded)")

print("bg sample:", bg)
