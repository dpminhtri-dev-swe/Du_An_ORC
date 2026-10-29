from __future__ import annotations

import csv
from io import BytesIO, StringIO
from pathlib import Path
from typing import IO

import pandas as pd

from .normalize import canonicalize_field_name


def _rewind(source: object) -> None:
    if hasattr(source, "seek"):
        source.seek(0)


def _find_header_row(preview: pd.DataFrame) -> int:
    for index, row in preview.iterrows():
        fields = {canonicalize_field_name(value) for value in row if str(value).strip()}
        if {"Heat no", "Coil no"}.issubset(fields):
            return int(index)
    return 0


def _read_bytes(source: str | Path | IO[bytes] | IO[str]) -> bytes:
    if isinstance(source, (str, Path)):
        return Path(source).read_bytes()
    _rewind(source)
    payload = source.read()
    _rewind(source)
    return payload.encode("utf-8") if isinstance(payload, str) else payload


def _decode_csv(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1258"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="replace")


def _find_csv_header_row(text: str, delimiter: str) -> int:
    for index, row in enumerate(csv.reader(StringIO(text), delimiter=delimiter)):
        fields = {canonicalize_field_name(value) for value in row if value.strip()}
        if {"Heat no", "Coil no"}.issubset(fields):
            return index
    return 0


def load_company_table(path_or_file: str | Path | IO[bytes] | IO[str]) -> pd.DataFrame:
    name = getattr(path_or_file, "name", str(path_or_file)).lower()
    if name.endswith(('.xlsx', '.xls')):
        preview = pd.read_excel(path_or_file, header=None, nrows=25, dtype=object)
        header_row = _find_header_row(preview)
        _rewind(path_or_file)
        return pd.read_excel(path_or_file, header=header_row, dtype=object)
    if name.endswith(('.csv', '.tsv')):
        delimiter = "\t" if name.endswith(".tsv") else ","
        text = _decode_csv(_read_bytes(path_or_file))
        header_row = _find_csv_header_row(text, delimiter)
        return pd.read_csv(
            StringIO(text),
            sep=delimiter,
            header=header_row,
            dtype=object,
            keep_default_na=False,
            skip_blank_lines=False,
        )
    raise ValueError("Unsupported company data file. Use CSV, XLSX, or XLS.")
