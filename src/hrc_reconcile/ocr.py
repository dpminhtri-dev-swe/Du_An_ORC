from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from PIL import Image, ImageOps

from .models import OcrCell, ReviewSession
from .normalize import clean_identifier, clean_numeric
from .templates import CertificateTemplate


@dataclass(frozen=True)
class OcrDetection:
    text: str
    confidence: float | None
    bounding_box: tuple[int, int, int, int] | None = None


class OcrEngine(Protocol):
    def read(self, image: Image.Image) -> list[OcrDetection]: ...


class RapidOcrEngine:
    def __init__(self) -> None:
        from rapidocr_onnxruntime import RapidOCR

        self._engine = RapidOCR()

    def read(self, image: Image.Image) -> list[OcrDetection]:
        result, _ = self._engine(image)
        return [OcrDetection(text=item[1], confidence=float(item[2]), bounding_box=tuple(item[0][0] + item[0][2])) for item in result or []]


_OCR_FIELDS = ["JSP no", "Heat no", "Coil no", "Size", "Grade", "C", "Si", "Mn", "CEQ"]


def _normalize_ocr(field: str, value: str | None) -> Any:
    if value is None:
        return None
    if field in {"Heat no", "Coil no", "JSP no"}:
        return clean_identifier(value)
    if field in {"C", "Si", "Mn", "CEQ"}:
        return clean_numeric(value)
    return value.strip() or None


def ocr_certificate(image: Image.Image, template: CertificateTemplate, engine: OcrEngine, row_count: int = 1) -> ReviewSession:
    prepared = ImageOps.grayscale(image)
    width, height = prepared.size
    region_x0, region_y0, region_x1, region_y1 = template.table_region
    table_left, table_top = int(width * region_x0), int(height * region_y0)
    table_right, table_bottom = int(width * region_x1), int(height * region_y1)
    row_height = max(1, (table_bottom - table_top) // max(row_count, 1))
    cells: list[OcrCell] = []
    for row_number in range(row_count):
        values: dict[str, OcrDetection | None] = {}
        row_top = table_top + row_number * row_height
        row_bottom = table_bottom if row_number == row_count - 1 else row_top + row_height
        for column in template.columns:
            if column.name == "No" or column.name not in _OCR_FIELDS:
                continue
            cell_left = table_left + int((table_right - table_left) * column.x0)
            cell_right = table_left + int((table_right - table_left) * column.x1)
            crop = prepared.crop((cell_left, row_top, max(cell_right, cell_left + 1), max(row_bottom, row_top + 1)))
            detections = engine.read(crop)
            values[column.name] = max(detections, key=lambda item: item.confidence or 0.0) if detections else None
        heat = values["Heat no"]
        coil = values["Coil no"]
        row_key = "|".join(
            [
                clean_identifier(heat.text) if heat else "",
                clean_identifier(coil.text) if coil else "",
            ]
        )
        row_key = row_key if row_key != "|" else f"ocr-row-{row_number + 1}"
        for field in _OCR_FIELDS:
            detection = values[field]
            raw = detection.text if detection else ""
            cells.append(
                OcrCell(
                    row_key=row_key,
                    field=field,
                    raw_text=raw,
                    value=_normalize_ocr(field, raw or None),
                    normalized_value=_normalize_ocr(field, raw or None),
                    confidence=detection.confidence if detection else None,
                    bounding_box=detection.bounding_box if detection else None,
                )
            )
    return ReviewSession(cells=cells, confirmed=False, template_name=template.name)
