from __future__ import annotations

from pathlib import Path
from typing import IO

import pandas as pd


def load_company_table(path_or_file: str | Path | IO[bytes] | IO[str]) -> pd.DataFrame:
    name = getattr(path_or_file, "name", str(path_or_file)).lower()
    if name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(path_or_file, dtype=object)
    if name.endswith(('.csv', '.tsv')):
        return pd.read_csv(path_or_file, dtype=object, keep_default_na=False)
    raise ValueError("Unsupported company data file. Use CSV, XLSX, or XLS.")
