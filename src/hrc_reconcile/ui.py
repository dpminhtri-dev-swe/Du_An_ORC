from __future__ import annotations

import pandas as pd

from .models import ReviewSession
from .review import apply_review_edit


def review_dataframe(session: ReviewSession) -> pd.DataFrame:
    return pd.DataFrame([
        {"row_key": cell.row_key, "field": cell.field, "value": cell.value, "confidence": cell.confidence, "manually_edited": cell.manually_edited}
        for cell in session.cells
    ], columns=["row_key", "field", "value", "confidence", "manually_edited"])


def apply_editor_values(session: ReviewSession, edited: pd.DataFrame) -> ReviewSession:
    updated = session
    for row in edited.to_dict(orient="records"):
        original = next(cell for cell in updated.cells if cell.row_key == row["row_key"] and cell.field == row["field"])
        if str(row.get("value", "")) != str(original.value if original.value is not None else ""):
            updated = apply_review_edit(updated, row["row_key"], row["field"], str(row.get("value", "")))
    return updated


def can_compare(session: ReviewSession) -> bool:
    return bool(session.confirmed)
