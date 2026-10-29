# HRC Data Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Streamlit application that imports HRC company data, OCRs a configured certificate layout, lets a reviewer correct OCR values, compares matched Coil rows with configurable tolerances, and exports a color-coded Excel report.

**Architecture:** Keep the UI thin and put normalization, OCR/template handling, matching, comparison, and reporting in separate Python modules. Use a configuration-driven template for the supplied certificate layout, with an adapter boundary around the local OCR engine so it can be replaced later. Persist only local configuration and review data; do not call external services.

**Tech Stack:** Python 3.11+, Streamlit, pandas, OpenCV, Pillow, PyMuPDF, RapidOCR/ONNX Runtime, openpyxl, pytest.

**Spec:** `docs/superpowers/specs/2026-10-29-hrc-data-reconciliation-design.md`

## Global Constraints

- Run all processing locally; do not send HRC images, PDFs, or tabular data to external OCR services.
- Preserve identifiers as strings, including leading zeroes, hyphens, and values originating from formulas such as `="355818"`.
- Use `Heat no. + Coil no.` as the first-version matching key.
- Do not treat company-only fields such as `Dòng` and `Vụ việc` as mismatches when absent from the document.
- Do not auto-merge ambiguous or incomplete keys; expose them for manual review.
- OCR values with low confidence or invalid identifier shape require user confirmation before comparison.
- The first supported document template is the supplied rotated tabular certificate; template data must be configurable for future variants.

## Review Focus

- Formula-wrapped CSV identifiers and leading zeroes must remain exact strings — covered by normalization tests in Task 2.
- Rotated/deskewed images and multi-row certificates must produce stable row/column crops — covered by template/OCR fixture tests in Task 4.
- Missing, duplicate, or incomplete `Heat no. + Coil no.` keys must never silently merge — covered by matching tests in Task 5.
- Missing document-only/company-only fields must receive the correct non-error status — covered by comparison tests in Task 6.
- Low-confidence OCR and user corrections must affect the final comparison/report — covered by review-state tests in Tasks 4 and 7.

### Task 1: Project scaffold and domain model

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `app.py`
- Create: `src/hrc_reconcile/__init__.py`
- Create: `src/hrc_reconcile/models.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Produces `FieldStatus`, `SourceValue`, `OcrCell`, `ComparisonCell`, `ComparisonRow`, `ToleranceConfig`, and `ReviewSession` dataclasses/types used by later tasks.

- [ ] **Step 1: Write the failing domain-model smoke test** in `tests/test_smoke.py` asserting a `ComparisonCell` can represent source values, normalized values, tolerance, OCR confidence, status, and note.
- [ ] **Step 2: Run `pytest tests/test_smoke.py -v` and verify it fails because the package/model is absent.**
- [ ] **Step 3: Implement the package scaffold and typed domain models** in `src/hrc_reconcile/models.py`; define statuses exactly as `MATCH`, `MISMATCH`, `MISSING_ON_DOCUMENT`, `MISSING_IN_COMPANY_DATA`, `OCR_UNREADABLE`, and `MANUAL_REVIEW` with display labels kept separate from machine values.
- [ ] **Step 4: Add minimal `app.py` entrypoint** that imports the package and renders a title plus an explicit “not yet loaded” state.
- [ ] **Step 5: Run `pytest tests/test_smoke.py -v` and verify PASS.**

### Task 2: CSV/Excel ingestion and normalization

**Files:**
- Create: `src/hrc_reconcile/io.py`
- Create: `src/hrc_reconcile/normalize.py`
- Create: `tests/fixtures/hrc_sample.csv`
- Create: `tests/test_normalize.py`

**Interfaces:**
- Produces `load_company_table(path_or_file) -> pandas.DataFrame` and `normalize_company_table(df) -> pandas.DataFrame`.
- Produces `canonicalize_field_name(name: str) -> str`, `clean_identifier(value: object) -> str | None`, and `clean_numeric(value: object) -> float | None`.

- [ ] **Step 1: Add a reduced fixture copied from the supplied CSV** with formula-wrapped `Heat no`, `Coil no`, empty values, and the representative chemical/mechanical fields.
- [ ] **Step 2: Write failing tests** for formula unwrapping, exact string preservation, case/spacing normalization of field names, numeric parsing, and detection of missing required columns.
- [ ] **Step 3: Run `pytest tests/test_normalize.py -v` and verify the new tests fail.**
- [ ] **Step 4: Implement CSV/XLSX loading** using pandas, retaining all raw columns and adding canonical column mappings for `SI`/`Si`, `MN`/`Mn`, `NB`/`Nb`, etc.
- [ ] **Step 5: Implement normalization** so `="355818"` becomes `355818`, identifiers never pass through floating point, blank/formula-empty values become `None`, and numeric fields accept the sample’s decimal formatting.
- [ ] **Step 6: Run the focused tests and then `pytest -q`; verify PASS.**

### Task 3: Template configuration and image/PDF preprocessing

**Files:**
- Create: `src/hrc_reconcile/templates.py`
- Create: `src/hrc_reconcile/preprocess.py`
- Create: `config/templates/ certificate_v1.json` (use a filename without spaces in implementation, e.g. `certificate_v1.json`)
- Create: `tests/fixtures/README.md`
- Create: `tests/test_preprocess.py`

**Interfaces:**
- Produces `CertificateTemplate` and `load_template(path) -> CertificateTemplate`.
- Produces `load_document_pages(file) -> list[PIL.Image.Image]`, `orient_document(image, template) -> PIL.Image.Image`, and `deskew_document(image) -> PIL.Image.Image`.

- [ ] **Step 1: Define the template JSON schema** for orientation, table bounding box, header/column names, row geometry, OCR preprocessing flags, and field aliases; record the supplied certificate as `certificate_v1`.
- [ ] **Step 2: Write failing tests** for template loading, 90-degree orientation correction, PDF page extraction, and preservation of a page’s row/column geometry metadata.
- [ ] **Step 3: Run `pytest tests/test_preprocess.py -v` and verify failure.**
- [ ] **Step 4: Implement template loading and validation** with clear errors for unknown fields, invalid normalized coordinates, and unsupported file types.
- [ ] **Step 5: Implement local image/PDF preprocessing** with Pillow/OpenCV and PyMuPDF; support JPG/PNG and text or scanned PDF pages, rotate using template orientation, and deskew without overwriting the original upload.
- [ ] **Step 6: Run focused tests and `pytest -q`; verify PASS.**

### Task 4: Local OCR adapter and editable OCR session

**Files:**
- Create: `src/hrc_reconcile/ocr.py`
- Create: `src/hrc_reconcile/review.py`
- Create: `tests/test_ocr_review.py`

**Interfaces:**
- Produces `OcrEngine.read(image) -> list[OcrDetection]` and `ocr_certificate(page, template, engine) -> ReviewSession`.
- Produces `apply_review_edit(session, row_key, field, value) -> ReviewSession` and `confirm_review(session) -> ReviewSession`.

- [ ] **Step 1: Write failing tests** with a fake OCR engine for multi-row extraction, confidence propagation, unreadable cells, and replacing an OCR value with a user edit before confirmation.
- [ ] **Step 2: Run `pytest tests/test_ocr_review.py -v` and verify failure.**
- [ ] **Step 3: Implement the OCR adapter** behind a small interface; use RapidOCR locally, crop cells from `certificate_v1`, normalize OCR text per field type, and retain raw text, normalized value, bounding box, and confidence.
- [ ] **Step 4: Implement review state** with immutable or copy-on-write updates, a confirmed flag, and an explicit block preventing comparison until confirmation.
- [ ] **Step 5: Run the focused tests and `pytest -q`; verify PASS.**

### Task 5: Row matching and ambiguity handling

**Files:**
- Create: `src/hrc_reconcile/matching.py`
- Create: `tests/test_matching.py`

**Interfaces:**
- Produces `build_match_key(row) -> str | None` and `match_rows(company_df, review_session) -> MatchResult`.

- [ ] **Step 1: Write failing tests** for exact key matches, company-only rows, document-only rows, duplicate keys, missing Heat/Coil components, and identifier normalization.
- [ ] **Step 2: Run `pytest tests/test_matching.py -v` and verify failure.**
- [ ] **Step 3: Implement exact `Heat no + Coil no` matching** and return explicit collections for matched, company-only, document-only, duplicate, and incomplete-key rows; never choose a row silently when a key is ambiguous.
- [ ] **Step 4: Run focused tests and `pytest -q`; verify PASS.**

### Task 6: Field comparison and tolerance configuration

**Files:**
- Create: `src/hrc_reconcile/comparison.py`
- Create: `config/tolerances.json`
- Create: `tests/test_comparison.py`

**Interfaces:**
- Produces `load_tolerances(path) -> ToleranceConfig` and `compare_matches(match_result, tolerances) -> list[ComparisonRow]`.
- Produces `compare_field(company_value, document_value, field, tolerance, ocr_confidence) -> ComparisonCell`.

- [ ] **Step 1: Write failing tests** for exact identifiers, numeric values within/outside tolerance, text normalization, missing-on-either-side statuses, unreadable OCR, and manual-review precedence.
- [ ] **Step 2: Run `pytest tests/test_comparison.py -v` and verify failure.**
- [ ] **Step 3: Implement field rules** with exact string comparison for identifiers, absolute numeric tolerance per field, normalized text comparison, and status precedence matching the design doc.
- [ ] **Step 4: Add a clearly marked initial tolerance configuration** with values supplied as editable placeholders/defaults rather than hidden technical assumptions; expose validation for non-negative tolerances.
- [ ] **Step 5: Run focused tests and `pytest -q`; verify PASS.**

### Task 7: Excel report generation

**Files:**
- Create: `src/hrc_reconcile/reporting.py`
- Create: `tests/test_reporting.py`

**Interfaces:**
- Produces `build_report_workbook(comparison_rows, review_session, tolerances) -> io.BytesIO`.

- [ ] **Step 1: Write failing tests** asserting the workbook has sheets for summary, row results, cell details, confirmed OCR data, and tolerances; verify status values, notes, source values, and color fills are present.
- [ ] **Step 2: Run `pytest tests/test_reporting.py -v` and verify failure.**
- [ ] **Step 3: Implement XLSX generation** with openpyxl, stable column order, status-based fills, filters, frozen headers, numeric formatting, and a note column explaining missing/ambiguous/OCR cases.
- [ ] **Step 4: Run focused tests and `pytest -q`; verify PASS.**

### Task 8: Streamlit workflow integration

**Files:**
- Modify: `app.py`
- Create: `src/hrc_reconcile/ui.py`
- Create: `tests/test_app_helpers.py`

**Interfaces:**
- Produces UI helpers for loading company data, selecting a template, displaying/editing OCR rows, confirming review, running comparison, and offering the XLSX download.

- [ ] **Step 1: Write failing helper tests** for session state transitions: no comparison before OCR confirmation, edit then confirm, and report generation after comparison.
- [ ] **Step 2: Run `pytest tests/test_app_helpers.py -v` and verify failure.**
- [ ] **Step 3: Implement the Streamlit flow** in the specified seven stages, using `st.data_editor` for OCR corrections, explicit warnings for low confidence and unmatched keys, and a compact summary of status counts plus row/cell detail tables.
- [ ] **Step 4: Wire the report bytes to `st.download_button`** and keep uploads in memory/session state unless the user explicitly exports them.
- [ ] **Step 5: Run `pytest -q` and launch `streamlit run app.py` for a manual smoke test with the supplied CSV and image.**

### Task 9: End-to-end fixture verification and local run documentation

**Files:**
- Create: `tests/test_end_to_end.py`
- Create: `README.md`
- Modify: `config/templates/certificate_v1.json` if fixture calibration requires it

**Interfaces:**
- Verifies the complete path from supplied sample files through normalized data, OCR review fixture, matching, comparison, and workbook export.

- [ ] **Step 1: Write an end-to-end test** using a deterministic fake OCR result derived from the supplied certificate, asserting multiple Coil rows match and that at least one company-only field is not reported as a mismatch.
- [ ] **Step 2: Run the end-to-end test and verify it fails until integration is complete.**
- [ ] **Step 3: Implement fixture wiring and adjust only template calibration/normalization defects revealed by the test.**
- [ ] **Step 4: Run `pytest -q` and the manual Streamlit smoke test; verify all tests pass and the app can export an `.xlsx` report.**
- [ ] **Step 5: Document Windows setup, local execution, supported input formats, template configuration, tolerance editing, and the fact that OCR data remains local.**

## Self-review coverage

The plan covers ingestion/normalization, local OCR and rotation, editable OCR review, exact composite-key matching, all required comparison statuses, per-column tolerances, report export, local-only operation, and the supplied multi-Coil sample. The four unresolved business choices from the builder check are intentionally represented as configuration or manual-review behavior: the first release supports `certificate_v1`; tolerance values remain explicit configuration; ambiguous keys remain unresolved for manual handling; and certificate fields are enabled through the field/template mapping rather than silently inferred.
