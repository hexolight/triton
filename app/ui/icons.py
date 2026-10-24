"""Drawn icons: one 24-unit grid, one stroke weight, round caps and joins.

Drawn at runtime with PIL (supersampled) so any palette colour works and
there is no Unicode glyph standing in for an icon.
"""

from __future__ import annotations

import math
from functools import lru_cache

import customtkinter as ctk
from PIL import Image, ImageDraw

from app.ui import theme

_SS = 4          # supersampling factor
_STROKE = 2.2    # in 24-unit grid space


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _arc(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 10) -> list[tuple[float, float]]:
    return [
        (cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
         cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
        for i in range(n + 1)
    ]


# name -> list of polylines in 24-unit space
_SHAPES: dict[str, list[list[tuple[float, float]]]] = {
    "close": [[(6, 6), (18, 18)], [(18, 6), (6, 18)]],
    "arrow_right": [[(4, 12), (20, 12)], [(14, 6), (20, 12), (14, 18)]],
    "chevron_left": [[(15, 5), (8, 12), (15, 19)]],
    "save": [
        [(12, 3), (12, 14)],
        [(7, 9.5), (12, 14.5), (17, 9.5)],
        [(4, 16), (4, 18)] + _arc(7, 18, 3, 180, 90, 5) + _arc(17, 18, 3, 90, 0, 5) + [(20, 18), (20, 16)],
    ],
    "alert": [_arc(12, 12, 9, 0, 360, 36), [(12, 7.5), (12, 13)], [(12, 16.6), (12, 16.7)]],
    "check": [[(5, 12.5), (10, 17.5), (19, 7)]],
}


def _stroke(draw: ImageDraw.ImageDraw, pts, unit: float, width: float, fill) -> None:
    px = [(x * unit, y * unit) for x, y in pts]
    draw.line(px, fill=fill, width=round(width), joint="curve")
    r = width / 2
    for x, y in (px[0], px[-1]):
        draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _render(name: str, colour: str, px: int) -> Image.Image:
    big = px * _SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    unit = big / 24
    fill = _rgb(colour) + (255,)
    for pts in _SHAPES[name]:
        _stroke(draw, pts, unit, _STROKE * unit, fill)
    return img.resize((px, px), Image.LANCZOS)


@lru_cache(maxsize=None)
def icon(name: str, colour: str, size: int = 16) -> ctk.CTkImage:
    img = _render(name, colour, size * 2)  # 2x for high-DPI
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


@lru_cache(maxsize=None)
def dot(colour: str, size: int = 10) -> ctk.CTkImage:
    px = size * 2
    big = px * _SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([0, 0, big - 1, big - 1], fill=_rgb(colour) + (255,))
    img = img.resize((px, px), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


@lru_cache(maxsize=None)
def drop_hero(size: int = 72) -> ctk.CTkImage:
    """Empty-state icon: a tinted disc with an arrow dropping into a tray."""
    px = size * 2
    big = px * _SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, big - 1, big - 1], fill=_rgb(theme.EMERALD_SOFT) + (255,))
    fill = _rgb(theme.CHAMPAGNE) + (255,)
    # the "save" glyph, scaled to sit inside the disc with room around it
    inner = big * 0.56
    offset = (big - inner) / 2
    unit = inner / 24
    for pts in _SHAPES["save"]:
        shifted = [(x + offset / unit, y + offset / unit) for x, y in pts]
        _stroke(draw, shifted, unit, 2.3 * unit, fill)
    img = img.resize((px, px), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
