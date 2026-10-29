from hrc_reconcile.models import ComparisonCell, FieldStatus


def test_comparison_cell_carries_sources_tolerance_confidence_and_status():
    cell = ComparisonCell(
        field="Heat no",
        company_value="355818",
        document_value="355818",
        normalized_company_value="355818",
        normalized_document_value="355818",
        difference=None,
        tolerance=0.0,
        status=FieldStatus.MATCH,
        ocr_confidence=0.98,
        note="",
    )

    assert cell.field == "Heat no"
    assert cell.company_value == "355818"
    assert cell.tolerance == 0.0
    assert cell.status is FieldStatus.MATCH
    assert cell.ocr_confidence == 0.98
