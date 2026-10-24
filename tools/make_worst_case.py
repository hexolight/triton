"""Dev tool: writes a folder of realistic worst-case files to drag into Triton.

    .venv\\Scripts\\python tools\\make_worst_case.py

Covers very long / non-ASCII / emoji names, uppercase and doubled extensions,
unsupported types, two files with the same name in different folders, and a
folder of 300 files (more than one page of rows).
"""

import sys
import tempfile
from pathlib import Path

from PIL import Image

root = Path(tempfile.gettempdir()) / "triton_worst_case"
nested = root / ("Müşteri Belgeleri Arşivi 2026 - Nihai Düzeltilmiş Sürüm " * 2).strip()
nested.mkdir(parents=True, exist_ok=True)

names = [
    "Müşteri Sözleşmesi - Nihai Sürüm (düzeltilmiş) 2026-09-28 versiyon 12 FINAL final son.docx",
    "IMG_20260928_142233_1234567890_very_long_whatsapp_export_name_without_spaces.JPG",
    "a.png",
    "🎬 tatil videosu 😀 ığdüşçö.mp4",
    "my.file.name.with.many.dots.v2.final.mp3",
    "Rapor.PDF",
    "no_extension_file",
    "unsupported.xyz",
]
for n in names:
    (nested / n).write_bytes(b"x")

for sub, colour in (("same_name_a", (220, 40, 40)), ("same_name_b", (40, 40, 220))):
    d = root / sub
    d.mkdir(exist_ok=True)
    Image.new("RGB", (64, 64), colour).save(d / "photo.png")

bulk = root / "bulk_300"
bulk.mkdir(exist_ok=True)
for i in range(300):
    p = bulk / f"IMG_{i:04d}.png"
    if not p.exists():
        Image.new("RGB", (16, 16), (i % 255, 120, 120)).save(p)

print(root)
sys.exit(0)
