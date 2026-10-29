from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from .models import MatchResult, OcrCell, ReviewSession
from .normalize import clean_identifier


def build_match_key(row: Any) -> str | None:
    if isinstance(row, dict):
        heat = row.get("Heat no")
        coil = row.get("Coil no")
    else:
        heat = row.get("Heat no")
        coil = row.get("Coil no")
    heat_value = clean_identifier(heat)
    coil_value = clean_identifier(coil)
    if not heat_value or not coil_value:
        return None
    return f"{heat_value}|{coil_value}"


def _document_rows(session: ReviewSession) -> tuple[dict[str, list[OcrCell]], list[str]]:
    grouped: dict[str, list[OcrCell]] = defaultdict(list)
    for cell in session.cells:
        if cell.row_key:
            grouped[cell.row_key].append(cell)
    keys: dict[str, str | None] = {}
    incomplete: list[str] = []
    for row_key, cells in grouped.items():
        values = {cell.field: cell.value for cell in cells}
        key = build_match_key(values)
        keys[row_key] = key
        if key is None:
            incomplete.append(row_key)
    return {keys[row_key] or row_key: cells for row_key, cells in grouped.items()}, incomplete


def match_rows(company_df: pd.DataFrame, review_session: ReviewSession) -> MatchResult:
    if not review_session.confirmed:
        raise ValueError("OCR review must be confirmed before matching")
    company_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    company_incomplete: list[str] = []
    for row in company_df.to_dict(orient="records"):
        key = build_match_key(row)
        if key is None:
            company_incomplete.append(str(row.get("JSP no") or "company-row"))
        else:
            company_by_key[key].append(row)

    document_by_key, document_incomplete = _document_rows(review_session)
    duplicate_keys = tuple(sorted(key for key, rows in company_by_key.items() if len(rows) > 1))
    matched: dict[str, tuple[Any, tuple[OcrCell, ...]]] = {}
    company_only: list[Any] = []
    for key, rows in company_by_key.items():
        if key in duplicate_keys:
            continue
        if key in document_by_key:
            matched[key] = (rows[0], tuple(document_by_key[key]))
        else:
            company_only.append(rows[0])
    document_only = tuple(cells[0] for key, cells in document_by_key.items() if key not in company_by_key)
    return MatchResult(
        matched=matched,
        company_only=tuple(company_only),
        document_only=document_only,
        duplicate_keys=duplicate_keys,
        incomplete_keys=tuple(company_incomplete + document_incomplete),
    )
