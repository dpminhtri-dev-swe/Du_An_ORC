import pandas as pd

from hrc_reconcile.comparison import compare_field, compare_matches, load_tolerances
from hrc_reconcile.matching import match_rows
from hrc_reconcile.models import FieldStatus, OcrCell, ReviewSession, ToleranceConfig


def test_compare_field_applies_exact_ids_numeric_tolerance_and_manual_review():
    assert compare_field("355818", "355818", "Heat no", 0, 0.99).status is FieldStatus.MATCH
    assert compare_field("355818", "355819", "Heat no", 0, 0.99).status is FieldStatus.MISMATCH
    assert compare_field(18.80, 18.81, "Thickness (mm)", 0.02, 0.99).status is FieldStatus.MATCH
    assert compare_field(18.80, 18.85, "Thickness (mm)", 0.02, 0.99).status is FieldStatus.MISMATCH
    assert compare_field(1.0, 1.0, "C", 0.01, 0.5).status is FieldStatus.MANUAL_REVIEW


def test_compare_field_distinguishes_missing_and_unreadable_values():
    assert compare_field(1.0, None, "C", 0.01, None).status is FieldStatus.OCR_UNREADABLE
    assert compare_field(1.0, None, "C", 0.01, 0.99).status is FieldStatus.MISSING_ON_DOCUMENT
    assert compare_field(None, 1.0, "C", 0.01, 0.99).status is FieldStatus.MISSING_IN_COMPANY_DATA


def test_compare_matches_returns_cell_level_results():
    company = pd.DataFrame([{"Heat no": "355818", "Coil no": "3180730000", "C": 7.0, "Grade": "SM490A"}])
    cells = [
        OcrCell("355818|3180730000", "Heat no", "355818", "355818", "355818", 0.99),
        OcrCell("355818|3180730000", "Coil no", "3180730000", "3180730000", "3180730000", 0.99),
        OcrCell("355818|3180730000", "C", "7", 7.01, 7.01, 0.99),
        OcrCell("355818|3180730000", "Grade", "SM490A", "SM490A", "SM490A", 0.99),
    ]
    result = match_rows(company, ReviewSession(cells=cells, confirmed=True))
    rows = compare_matches(result, ToleranceConfig({"C": 0.02}))
    statuses = {cell.field: cell.status for cell in rows[0].cells}
    assert statuses["Heat no"] is FieldStatus.MATCH
    assert statuses["C"] is FieldStatus.MATCH


def test_compare_matches_includes_company_and_document_only_rows_for_audit():
    company = pd.DataFrame([{"Heat no": "355818", "Coil no": "3180730000"}])
    review = ReviewSession(cells=[
        OcrCell("355819|3180730001", "Heat no", "355819", "355819", "355819", 0.99),
        OcrCell("355819|3180730001", "Coil no", "3180730001", "3180730001", "3180730001", 0.99),
    ], confirmed=True)
    rows = compare_matches(match_rows(company, review), ToleranceConfig())
    assert {row.status for row in rows} == {FieldStatus.MISSING_ON_DOCUMENT, FieldStatus.MISSING_IN_COMPANY_DATA}
    document_row = next(row for row in rows if row.status is FieldStatus.MISSING_IN_COMPANY_DATA)
    assert {cell.field for cell in document_row.cells} == {"Heat no", "Coil no"}


def test_tolerances_reject_negative_values():
    try:
        load_tolerances({"C": -0.1})
    except ValueError:
        pass
    else:
        raise AssertionError("negative tolerance must fail")
