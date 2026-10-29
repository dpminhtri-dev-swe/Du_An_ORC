from pathlib import Path

from PIL import Image

from hrc_reconcile.comparison import compare_matches, load_tolerances
from hrc_reconcile.io import load_company_table
from hrc_reconcile.matching import match_rows
from hrc_reconcile.models import FieldStatus, ReviewSession
from hrc_reconcile.normalize import normalize_company_table
from hrc_reconcile.ocr import OcrDetection, ocr_certificate
from hrc_reconcile.reporting import build_report_workbook
from hrc_reconcile.review import confirm_review
from hrc_reconcile.templates import load_template


class FixtureOcr:
    def __init__(self):
        self.values = [
            "26-672", "355818", "3180730000", "19.00 X 1499 X C", "SM490A", "7", "21", "135", "32",
            "26-673", "355818", "3180731000", "19.00 X 1499 X C", "SM490A", "7", "21", "135", "32",
        ]
        self.index = 0

    def read(self, image):
        value = self.values[self.index] if self.index < len(self.values) else ""
        self.index += 1
        return [OcrDetection(value, 0.99, (0, 0, image.width, image.height))] if value else []


def test_sample_data_flows_through_matching_comparison_and_export():
    root = Path(__file__).parents[1]
    company = normalize_company_table(load_company_table(root / "tests" / "fixtures" / "hrc_sample.csv"))
    template = load_template(root / "config" / "templates" / "certificate_v1.json")
    review = confirm_review(ocr_certificate(Image.new("RGB", (100, 100)), template, FixtureOcr(), row_count=2))
    matches = match_rows(company, review)
    rows = compare_matches(matches, load_tolerances(root / "config" / "tolerances.json"))
    report = build_report_workbook(rows, review, load_tolerances(root / "config" / "tolerances.json"))

    assert len(matches.matched) == 2
    assert len(rows) == 2
    first_cells = {cell.field: cell for cell in rows[0].cells}
    assert first_cells["YPT"].status is FieldStatus.MISSING_ON_DOCUMENT
    assert report.getvalue()[:2] == b"PK"
