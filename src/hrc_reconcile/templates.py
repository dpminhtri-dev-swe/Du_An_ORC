from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TemplateColumn:
    name: str
    x0: float
    x1: float
    kind: str


@dataclass(frozen=True)
class CertificateTemplate:
    name: str
    orientation_degrees: int
    table_region: tuple[float, float, float, float]
    header_rows: int
    row_height_ratio: float
    columns: tuple[TemplateColumn, ...]


def load_template(path: str | Path) -> CertificateTemplate:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    region = tuple(raw["table_region"])
    if len(region) != 4 or any(not 0 <= value <= 1 for value in region):
        raise ValueError("table_region must contain four normalized values")
    columns = tuple(TemplateColumn(**column) for column in raw["columns"])
    for column in columns:
        if not (0 <= column.x0 < column.x1 <= 1):
            raise ValueError(f"Invalid normalized column bounds: {column.name}")
    return CertificateTemplate(
        name=raw["name"],
        orientation_degrees=int(raw.get("orientation_degrees", 0)) % 360,
        table_region=region,
        header_rows=int(raw.get("header_rows", 1)),
        row_height_ratio=float(raw.get("row_height_ratio", 0.05)),
        columns=columns,
    )
