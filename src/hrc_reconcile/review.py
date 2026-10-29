from __future__ import annotations

from dataclasses import replace

from .models import OcrCell, ReviewSession
from .normalize import clean_identifier, clean_numeric


def _normalize(field: str, value: str):
    if field in {"Heat no", "Coil no", "JSP no"}:
        return clean_identifier(value)
    if field in {"C", "Si", "Mn", "CEQ"}:
        return clean_numeric(value)
    return value.strip() or None


def apply_review_edit(session: ReviewSession, row_key: str, field: str, value: str) -> ReviewSession:
    updated: list[OcrCell] = []
    found = False
    for cell in session.cells:
        if cell.row_key == row_key and cell.field == field:
            normalized = _normalize(field, value)
            updated.append(replace(cell, raw_text=value, value=normalized, normalized_value=normalized, manually_edited=True))
            found = True
        else:
            updated.append(cell)
    if not found:
        raise KeyError(f"OCR cell not found: {row_key}/{field}")
    return ReviewSession(cells=updated, confirmed=False, template_name=session.template_name, source_name=session.source_name)


def confirm_review(session: ReviewSession) -> ReviewSession:
    return ReviewSession(cells=list(session.cells), confirmed=True, template_name=session.template_name, source_name=session.source_name)
