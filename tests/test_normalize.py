from pathlib import Path

import pandas as pd
import pytest

from hrc_reconcile.io import load_company_table
from hrc_reconcile.normalize import (
    canonicalize_field_name,
    clean_identifier,
    clean_numeric,
    normalize_company_table,
)


FIXTURE = Path(__file__).parent / "fixtures" / "hrc_sample.csv"


def test_clean_identifier_unwraps_formula_without_float_conversion():
    assert clean_identifier('="00355818"') == "00355818"
    assert clean_identifier("3180730000") == "3180730000"
    assert clean_identifier(355818.0) == "355818"


def test_field_names_and_numbers_are_normalized():
    assert canonicalize_field_name(" SI ") == "Si"
    assert canonicalize_field_name("MN") == "Mn"
    assert clean_numeric('="18.80"') == pytest.approx(18.8)
    assert clean_numeric("") is None


def test_sample_csv_normalizes_formula_identifiers_and_aliases():
    table = normalize_company_table(load_company_table(FIXTURE))

    assert table.loc[0, "Heat no"] == "355818"
    assert table.loc[0, "Coil no"] == "3180730000"
    assert table.loc[0, "Si"] == 21.0
    assert table.loc[0, "Mn"] == 135.0


def test_required_columns_are_reported_when_missing():
    with pytest.raises(ValueError, match="Heat no"):
        normalize_company_table(pd.DataFrame({"JSP no": ["26-1"]}))


def test_text_certificate_columns_are_not_numeric_coerced():
    table = normalize_company_table(pd.DataFrame({
        "Heat no": [355818.0], "Coil no": [3180730000.0],
        "Material Certificate": ["QZA026900285"], "Visual Inspection": ["Good"], "Result": ["ACC"],
    }))
    assert table.loc[0, "Heat no"] == "355818"
    assert table.loc[0, "Coil no"] == "3180730000"
    assert table.loc[0, "Material Certificate"] == "QZA026900285"
    assert table.loc[0, "Visual Inspection"] == "Good"
    assert table.loc[0, "Result"] == "ACC"
