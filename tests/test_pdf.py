import pytest
from PIL import Image

pymupdf = pytest.importorskip("pymupdf")

from app.converters import pdf  # noqa: E402
from app.core.converter_registry import convert_file  # noqa: E402


def _make_pdf(path, pages):
    doc = pymupdf.open()
    for i in range(pages):
        doc.new_page().insert_text((50, 50), f"page {i + 1}")
    doc.save(path)
    doc.close()


def test_pdf_to_image_returns_every_page(tmp_path):
    src = tmp_path / "m.pdf"
    _make_pdf(src, 3)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    outputs = pdf.pdf_to_image(src, out_dir / "m.png")
    assert [p.name for p in outputs] == ["m.png", "m_2.png", "m_3.png"]
    assert all(p.exists() for p in outputs)


def test_convert_file_reports_all_outputs(tmp_path):
    src = tmp_path / "m.pdf"
    _make_pdf(src, 2)
    outputs = convert_file(src, tmp_path / "out" / "m.jpg")
    assert [p.name for p in outputs] == ["m.jpg", "m_2.jpg"]


def test_convert_file_single_output_is_dst(tmp_path):
    src = tmp_path / "a.png"
    Image.new("RGB", (8, 8)).save(src)
    dst = tmp_path / "out" / "a.jpg"
    assert convert_file(src, dst) == [dst]


def test_image_to_pdf_flattens_transparency(tmp_path):
    src, dst = tmp_path / "t.png", tmp_path / "t.pdf"
    Image.new("RGBA", (40, 40), (255, 0, 0, 0)).save(src)
    pdf.convert(src, dst)
    doc = pymupdf.open(dst)
    pix = doc[0].get_pixmap()
    assert min(pix.pixel(5, 5)) > 240
