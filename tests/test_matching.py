import pandas as pd

from hrc_reconcile.matching import build_match_key, match_rows
from hrc_reconcile.models import OcrCell, ReviewSession


def _cell(row_key, field, value):
    return OcrCell(row_key=row_key, field=field, raw_text=str(value), value=value, normalized_value=value, confidence=0.99)


def test_build_match_key_requires_both_identifiers_and_preserves_strings():
    assert build_match_key({"Heat no": '="00355818"', "Coil no": '="000123"'}) == "00355818|000123"
    assert build_match_key({"Heat no": "355818", "Coil no": ""}) is None


def test_matching_separates_matched_missing_duplicate_and_incomplete_rows():
    company = pd.DataFrame([
        {"Heat no": "355818", "Coil no": "3180730000", "JSP no": "26-672"},
        {"Heat no": "355818", "Coil no": "3180730000", "JSP no": "26-duplicate"},
        {"Heat no": "355819", "Coil no": "3180722000", "JSP no": "26-684"},
    ])
    review = ReviewSession(cells=[
        _cell("355818|3180730000", "Heat no", "355818"),
        _cell("355818|3180730000", "Coil no", "3180730000"),
        _cell("355820|3180000000", "Heat no", "355820"),
        _cell("355820|3180000000", "Coil no", "3180000000"),
        _cell("incomplete", "Heat no", "355821"),
    ], confirmed=True)

    result = match_rows(company, review)

    assert "355818|3180730000" in result.duplicate_keys
    assert "355819|3180722000" in {build_match_key(row) for row in result.company_only}
    assert "355820|3180000000" in {cells[0].row_key for cells in result.document_only}
    assert "incomplete" in result.incomplete_keys


def test_duplicate_document_keys_are_not_silently_collapsed():
    company = pd.DataFrame([{"Heat no": "355818", "Coil no": "3180730000"}])
    review = ReviewSession(cells=[
        _cell("first", "Heat no", "355818"), _cell("first", "Coil no", "3180730000"),
        _cell("second", "Heat no", "355818"), _cell("second", "Coil no", "3180730000"),
    ], confirmed=True)
    result = match_rows(company, review)
    assert "355818|3180730000" in result.duplicate_keys
    assert not result.matched
