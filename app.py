from pathlib import Path

import pandas as pd
import streamlit as st

from hrc_reconcile.comparison import compare_matches, load_tolerances
from hrc_reconcile.io import load_company_table
from hrc_reconcile.matching import match_rows
from hrc_reconcile.normalize import normalize_company_table
from hrc_reconcile.ocr import RapidOcrEngine, ocr_certificate
from hrc_reconcile.preprocess import deskew_document, load_document_pages, orient_document
from hrc_reconcile.reporting import build_report_workbook
from hrc_reconcile.review import confirm_review
from hrc_reconcile.templates import load_template
from hrc_reconcile.ui import apply_editor_values, can_compare, ocr_workload_message, review_dataframe


ROOT = Path(__file__).parent
TEMPLATE_PATH = ROOT / "config" / "templates" / "certificate_v1.json"
TOLERANCE_PATH = ROOT / "config" / "tolerances.json"


def main() -> None:
    st.set_page_config(page_title="Đối chiếu dữ liệu HRC", layout="wide")
    st.title("Tool đối chiếu dữ liệu HRC")
    st.caption("Xử lý cục bộ: dữ liệu không được gửi ra dịch vụ bên ngoài.")
    company_file = st.file_uploader("1. Tải Excel/CSV dữ liệu công ty", type=["csv", "xlsx", "xls"])
    if company_file is not None:
        try:
            st.session_state.company_df = normalize_company_table(load_company_table(company_file))
            st.success(f"Đã đọc {len(st.session_state.company_df)} dòng và {len(st.session_state.company_df.columns)} cột.")
            st.dataframe(st.session_state.company_df.head(10), use_container_width=True)
        except Exception as exc:
            st.error(f"Không đọc được dữ liệu công ty: {exc}")

    document_file = st.file_uploader("2. Tải ảnh/PDF chứng từ", type=["jpg", "jpeg", "png", "pdf"])
    row_count = st.number_input("Số dòng Coil cần OCR", min_value=1, max_value=200, value=15, step=1)
    st.caption(ocr_workload_message(int(row_count)))
    if row_count > 25:
        st.warning("Số dòng cao sẽ mất thời gian. Với ảnh mẫu hiện tại, hãy nhập 19 dòng Coil.")
    if document_file is not None and st.button("Chạy OCR cục bộ"):
        try:
            with st.spinner(f"Đang OCR {int(row_count) * 9} ô, vui lòng chờ…"):
                template = load_template(TEMPLATE_PATH)
                page = deskew_document(orient_document(load_document_pages(document_file, document_file.name)[0], template))
                st.session_state.review = ocr_certificate(page, template, RapidOcrEngine(), int(row_count))
                st.session_state.review.source_name = document_file.name
            st.success("OCR hoàn tất. Hãy kiểm tra và sửa bảng trước khi xác nhận.")
        except Exception as exc:
            st.error(f"OCR thất bại: {exc}")

    review = st.session_state.get("review")
    if review is not None:
        st.subheader("3. Kiểm tra và xác nhận OCR")
        edited = st.data_editor(review_dataframe(review), hide_index=True, use_container_width=True, disabled=["row_key", "field", "confidence", "manually_edited"])
        review = apply_editor_values(review, edited)
        if st.button("Xác nhận dữ liệu OCR"):
            review = confirm_review(review)
            st.session_state.review = review
            st.success("Đã xác nhận dữ liệu OCR.")

    review = st.session_state.get("review")
    company_df = st.session_state.get("company_df")
    if review is not None and company_df is not None and can_compare(review) and st.button("4. Chạy đối chiếu"):
        try:
            matches = match_rows(company_df, review)
            tolerances = load_tolerances(TOLERANCE_PATH)
            comparison_rows = compare_matches(matches, tolerances)
            st.session_state.comparison_rows = comparison_rows
            st.session_state.report = build_report_workbook(comparison_rows, review, tolerances).getvalue()
        except Exception as exc:
            st.error(f"Đối chiếu thất bại: {exc}")

    rows = st.session_state.get("comparison_rows")
    if rows:
        st.subheader("5. Kết quả")
        st.dataframe(pd.DataFrame([{"row_key": row.row_key, "status": row.status.value, "note": row.note} for row in rows]), use_container_width=True)
        st.download_button("Tải báo cáo Excel", st.session_state.report, file_name="hrc_reconciliation_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    main()
