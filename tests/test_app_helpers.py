import pandas as pd
import pytest

from hrc_reconcile.models import OcrCell, ReviewSession
from hrc_reconcile.ui import apply_editor_values, can_compare, ocr_workload_message, review_dataframe


def test_review_helpers_require_confirmation_and_apply_editor_changes():
    session = ReviewSession(cells=[OcrCell("k", "Heat no", "355818", "355818", "355818", 0.99)])
    assert can_compare(session) is False
    edited = pd.DataFrame([{"row_key": "k", "field": "Heat no", "value": "355819"}])
    updated = apply_editor_values(session, edited)
    assert updated.cells[0].value == "355819"
    assert updated.cells[0].manually_edited is True
    assert can_compare(ReviewSession(cells=updated.cells, confirmed=True)) is True


def test_review_dataframe_exposes_confidence_and_edit_flag():
    session = ReviewSession(cells=[OcrCell("k", "Heat no", "355818", "355818", "355818", 0.99)])
    frame = review_dataframe(session)
    assert list(frame.columns) == ["row_key", "field", "value", "confidence", "manually_edited"]
    assert frame.iloc[0]["confidence"] == 0.99


def test_ocr_workload_message_explains_the_number_of_cells():
    assert ocr_workload_message(19) == "OCR sẽ đọc 171 ô (19 dòng × 9 cột)."
