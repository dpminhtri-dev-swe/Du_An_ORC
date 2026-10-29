from PIL import Image
import numpy as np

from hrc_reconcile.models import FieldStatus
from hrc_reconcile.ocr import OcrDetection, RapidOcrEngine, ocr_certificate
from hrc_reconcile.review import apply_review_edit, confirm_review
from hrc_reconcile.templates import load_template


TEMPLATE = load_template("config/templates/certificate_v1.json")


class FakeEngine:
    def __init__(self):
        self.values = ["26-672", "355818", "3180730000", "19.00 X 1499 X C", "SM490A", "7", "21", "135"]
        self.calls = 0
        self.heights = []

    def read(self, image):
        self.heights.append(image.height)
        value = self.values[self.calls] if self.calls < len(self.values) else ""
        self.calls += 1
        return [OcrDetection(value, 0.98, (0, 0, image.width, image.height))] if value else []


def test_ocr_certificate_retains_confidence_and_marks_unreadable_cells():
    engine = FakeEngine()
    session = ocr_certificate(Image.new("RGB", (100, 100)), TEMPLATE, engine, row_count=1)
    heat = next(cell for cell in session.cells if cell.field == "Heat no")
    ceq = next(cell for cell in session.cells if cell.field == "CEQ")

    assert heat.value == "355818"
    assert heat.confidence == 0.98
    assert ceq.value is None
    assert ceq.confidence is None
    assert engine.calls == 9


def test_ocr_excludes_configured_header_rows_from_data_crops():
    engine = FakeEngine()
    ocr_certificate(Image.new("RGB", (100, 100)), TEMPLATE, engine, row_count=2)
    assert set(engine.heights) == {35}


def test_rapidocr_adapter_converts_pil_image_to_numpy_array():
    captured = {}

    class UnderlyingEngine:
        def __call__(self, image):
            captured["image"] = image
            return [], None

    engine = RapidOcrEngine.__new__(RapidOcrEngine)
    engine._engine = UnderlyingEngine()
    assert engine.read(Image.new("RGB", (20, 20), "white")) == []
    assert isinstance(captured["image"], np.ndarray)


def test_review_edit_replaces_ocr_value_and_confirmation_unlocks_session():
    session = ocr_certificate(Image.new("RGB", (100, 100)), TEMPLATE, FakeEngine(), row_count=1)
    edited = apply_review_edit(session, "355818|3180730000", "Heat no", "355819")
    confirmed = confirm_review(edited)
    heat = next(cell for cell in confirmed.cells if cell.field == "Heat no")

    assert heat.value == "355819"
    assert heat.manually_edited is True
    assert heat.confidence is None
    assert confirmed.confirmed is True
