# Tool đối chiếu dữ liệu HRC

Ứng dụng Streamlit chạy cục bộ để so sánh dữ liệu HRC trong Excel/CSV với chứng từ ảnh/PDF.

## Chạy trên Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
python -m pytest -q
streamlit run app.py
```

Trong ứng dụng:

1. Tải CSV/XLSX dữ liệu công ty.
2. Tải ảnh hoặc PDF chứng từ.
3. Chạy OCR, kiểm tra/sửa bảng OCR rồi bấm xác nhận.
4. Chạy đối chiếu và tải báo cáo Excel.

Xử lý OCR dùng engine cục bộ. Mẫu đầu tiên nằm ở `config/templates/certificate_v1.json`; sai số nằm ở `config/tolerances.json`. Giá trị sai số cần được bộ phận kỹ thuật xác nhận trước khi dùng kết quả làm hồ sơ chính thức.
