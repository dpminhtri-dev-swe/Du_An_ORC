from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .models import ComparisonCell, ComparisonRow, FieldStatus, MatchResult, OcrCell, ToleranceConfig
from .normalize import clean_identifier, clean_numeric


_IDENTIFIERS = {"JSP no", "Heat no", "Coil no"}
_TEXT_FIELDS = {"Size", "Grade", "Chemical", "Mechanical", "Visual Inspection", "Material Certificate", "Result", "Other"}
_INTERNAL_FIELDS = {"Dòng", "Vụ việc"}


def load_tolerances(source: str | Path | dict[str, float]) -> ToleranceConfig:
    values = json.loads(Path(source).read_text(encoding="utf-8")) if isinstance(source, (str, Path)) else source
    normalized = {str(key): float(value) for key, value in values.items()}
    if any(value < 0 for value in normalized.values()):
        raise ValueError("Tolerances cannot be negative")
    return ToleranceConfig(normalized)


def _same_text(left: Any, right: Any) -> bool:
    return " ".join(str(left).split()).casefold() == " ".join(str(right).split()).casefold()


def compare_field(company_value: Any, document_value: Any, field: str, tolerance: float, ocr_confidence: float | None, confidence_threshold: float = 0.75) -> ComparisonCell:
    if ocr_confidence is not None and ocr_confidence < confidence_threshold:
        return ComparisonCell(field, company_value, document_value, company_value, document_value, None, tolerance, FieldStatus.MANUAL_REVIEW, ocr_confidence, "OCR confidence is below review threshold")
    if document_value is None:
        status = FieldStatus.OCR_UNREADABLE if ocr_confidence is None else FieldStatus.MISSING_ON_DOCUMENT
        return ComparisonCell(field, company_value, None, company_value, None, None, tolerance, status, ocr_confidence, "Document value unavailable")
    if company_value is None:
        return ComparisonCell(field, None, document_value, None, document_value, None, tolerance, FieldStatus.MISSING_IN_COMPANY_DATA, ocr_confidence, "Company value unavailable")

    if field in _IDENTIFIERS:
        left, right = clean_identifier(company_value), clean_identifier(document_value)
        same = left == right
        difference = None
    elif field in _TEXT_FIELDS:
        left, right = str(company_value).strip(), str(document_value).strip()
        same = _same_text(left, right)
        difference = None
    else:
        left, right = clean_numeric(company_value), clean_numeric(document_value)
        if left is None or right is None:
            same, difference = False, None
        else:
            difference = abs(left - right)
            same = difference <= tolerance
    return ComparisonCell(field, company_value, document_value, left, right, difference, tolerance, FieldStatus.MATCH if same else FieldStatus.MISMATCH, ocr_confidence, "")


def _row_status(cells: list[ComparisonCell]) -> FieldStatus:
    statuses = {cell.status for cell in cells}
    if FieldStatus.MISMATCH in statuses:
        return FieldStatus.MISMATCH
    if FieldStatus.MANUAL_REVIEW in statuses:
        return FieldStatus.MANUAL_REVIEW
    if FieldStatus.OCR_UNREADABLE in statuses:
        return FieldStatus.OCR_UNREADABLE
    if FieldStatus.MISSING_ON_DOCUMENT in statuses:
        return FieldStatus.MISSING_ON_DOCUMENT
    if FieldStatus.MISSING_IN_COMPANY_DATA in statuses:
        return FieldStatus.MISSING_IN_COMPANY_DATA
    return FieldStatus.MATCH


def compare_matches(match_result: MatchResult, tolerances: ToleranceConfig) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []
    for key, (company, document_cells) in match_result.matched.items():
        document_by_field = {cell.field: cell for cell in document_cells}
        fields = [field for field in company if field not in _INTERNAL_FIELDS]
        fields.extend(field for field in document_by_field if field not in fields)
        cells = []
        for field in fields:
            document = document_by_field.get(field)
            cells.append(compare_field(company.get(field), document.value if document else None, field, tolerances.values.get(field, 0.0), document.confidence if document else 1.0, tolerances.manual_review_confidence_threshold))
        rows.append(ComparisonRow(key, tuple(cells), _row_status(cells)))
    return rows
