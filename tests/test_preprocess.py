from io import BytesIO
from pathlib import Path

from PIL import Image
import numpy as np

from hrc_reconcile.preprocess import deskew_document, load_document_pages, orient_document
from hrc_reconcile.templates import load_template


TEMPLATE = Path(__file__).parents[1] / "config" / "templates" / "certificate_v1.json"


def test_template_loads_normalized_table_and_column_metadata():
    template = load_template(TEMPLATE)
    assert template.name == "certificate_v1"
    assert template.orientation_degrees == 90
    assert template.columns[2].name == "Heat no"


def test_orientation_rotates_image_using_template():
    source = Image.new("RGB", (20, 10), "white")
    rotated = orient_document(source, load_template(TEMPLATE))
    assert rotated.size == (10, 20)


def test_pdf_page_extraction_returns_images():
    pdf_bytes = BytesIO()
    import fitz

    document = fitz.open()
    page = document.new_page(width=100, height=100)
    page.insert_text((10, 20), "HRC")
    pdf_bytes.write(document.tobytes())
    pdf_bytes.seek(0)

    pages = load_document_pages(pdf_bytes, filename="certificate.pdf")
    assert len(pages) == 1
    assert pages[0].width > 0 and pages[0].height > 0


def test_deskew_preserves_image_dimensions():
    source = Image.new("RGB", (20, 10), "white")
    result = deskew_document(source)
    assert result.size == source.size


def test_deskew_accepts_opencv_hough_lines_shape(monkeypatch):
    monkeypatch.setattr("hrc_reconcile.preprocess.cv2.HoughLinesP", lambda *args, **kwargs: np.array([[1, 1, 18, 1]], dtype=np.int32))
    source = Image.new("RGB", (20, 10), "white")
    result = deskew_document(source)
    assert result.size == source.size
