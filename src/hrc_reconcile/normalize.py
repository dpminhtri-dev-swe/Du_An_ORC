from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd


_FIELD_ALIASES = {
    "si": "Si",
    "mn": "Mn",
    "nb": "Nb",
    "ti": "Ti",
    "cu": "Cu",
    "ni": "Ni",
    "cr": "Cr",
    "mo": "Mo",
    "sn": "Sn",
    "ceq": "CEQ",
    "pcm": "PCM",
    "yp": "YPT",
    "ys": "YS",
    "ts": "TS",
    "el": "EL",
    "jsp no": "JSP no",
    "heat no": "Heat no",
    "coil no": "Coil no",
}

_IDENTIFIER_FIELDS = {"JSP no", "Heat no", "Coil no", "Sample ID"}


def canonicalize_field_name(name: object) -> str:
    text = str(name).strip()
    return _FIELD_ALIASES.get(text.casefold(), text)


def _unwrap_formula(value: object) -> str:
    text = str(value).strip()
    if len(text) >= 3 and text.startswith('="') and text.endswith('"'):
        return text[2:-1]
    if len(text) >= 2 and text.startswith("='") and text.endswith("'"):
        return text[2:-1]
    return text


def clean_identifier(value: object) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = _unwrap_formula(value).strip()
    return text or None


def clean_numeric(value: object) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = _unwrap_formula(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_company_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [canonicalize_field_name(column) for column in result.columns]
    duplicated = result.columns[result.columns.duplicated()].tolist()
    if duplicated:
        raise ValueError(f"Duplicate columns after normalization: {', '.join(duplicated)}")

    required = {"Heat no", "Coil no"}
    missing = sorted(required - set(result.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    for column in result.columns:
        if column in _IDENTIFIER_FIELDS:
            result[column] = result[column].map(clean_identifier)
        elif column not in {"Size", "Chemical", "Mechanical", "Grade", "Other"}:
            result[column] = result[column].map(clean_numeric)
    return result
