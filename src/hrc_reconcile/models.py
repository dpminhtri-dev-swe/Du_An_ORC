from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    MISSING_ON_DOCUMENT = "missing_on_document"
    MISSING_IN_COMPANY_DATA = "missing_in_company_data"
    OCR_UNREADABLE = "ocr_unreadable"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True)
class SourceValue:
    value: Any = None
    normalized_value: Any = None
    source: str = ""


@dataclass(frozen=True)
class OcrCell:
    row_key: str | None
    field: str
    raw_text: str = ""
    value: Any = None
    normalized_value: Any = None
    confidence: float | None = None
    bounding_box: tuple[int, int, int, int] | None = None
    manually_edited: bool = False


@dataclass(frozen=True)
class ComparisonCell:
    field: str
    company_value: Any = None
    document_value: Any = None
    normalized_company_value: Any = None
    normalized_document_value: Any = None
    difference: float | None = None
    tolerance: float | None = None
    status: FieldStatus = FieldStatus.MANUAL_REVIEW
    ocr_confidence: float | None = None
    note: str = ""


@dataclass(frozen=True)
class ComparisonRow:
    row_key: str
    cells: tuple[ComparisonCell, ...] = ()
    status: FieldStatus = FieldStatus.MANUAL_REVIEW
    note: str = ""


@dataclass(frozen=True)
class ToleranceConfig:
    values: dict[str, float] = field(default_factory=dict)
    manual_review_confidence_threshold: float = 0.75


@dataclass
class ReviewSession:
    cells: list[OcrCell] = field(default_factory=list)
    confirmed: bool = False
    template_name: str = ""
    source_name: str = ""


@dataclass(frozen=True)
class MatchResult:
    matched: dict[str, tuple[Any, OcrCell | None]] = field(default_factory=dict)
    company_only: tuple[Any, ...] = ()
    document_only: tuple[tuple[OcrCell, ...], ...] = ()
    duplicate_keys: tuple[str, ...] = ()
    incomplete_keys: tuple[str, ...] = ()
    ambiguous_document: dict[str, tuple[OcrCell, ...]] = field(default_factory=dict)
