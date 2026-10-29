# Design: Tool đối chiếu dữ liệu HRC

## 1. Ý định và lý do

Xây dựng một ứng dụng Streamlit chạy nội bộ để nhân viên kiểm tra dữ liệu HRC giữa file Excel/CSV của công ty và giấy tờ chứng nhận dạng ảnh/PDF. Ứng dụng phải giúp người dùng phát hiện sai lệch theo từng dòng và từng ô, nhưng vẫn giữ người dùng trong vòng kiểm soát khi OCR không chắc chắn.

Mẫu thực tế hiện có gồm:

- CSV `Danh sách HRC đã sử dụng.csv` với các trường nhận diện, kích thước, khối lượng, cơ tính, hóa học, chứng nhận và cột nội bộ.
- Ảnh chứng từ dạng bảng bị xoay 90 độ, có nhiều dòng Coil và các nhóm cột `JSP no`, `Heat no`, `Coil no`, `Coil size`, `Grade`, thành phần hóa học và thông tin chứng nhận.

## 2. Mục tiêu

- Đọc Excel/CSV, kể cả giá trị dạng `="355818"`, và chuẩn hóa mã thành chuỗi ổn định.
- Nhận ảnh/PDF, tự xoay và tiền xử lý ảnh để OCR cục bộ.
- OCR theo mẫu chứng từ có cấu hình, không phụ thuộc hoàn toàn vào một bố cục hard-code.
- Hiển thị dữ liệu OCR trong bảng chỉnh sửa được trước khi đối chiếu.
- Ghép dòng bằng `Heat no. + Coil no.`; hỗ trợ nhiều dòng Coil trong một chứng từ.
- So sánh trường chung theo quy tắc từng cột và sai số cấu hình được.
- Phân biệt `Khớp`, `Không khớp`, `Không có trên giấy tờ`, `Không có trong Excel`, `OCR không đọc được` và `Cần kiểm tra thủ công`.
- Xuất báo cáo Excel có màu trạng thái, giá trị hai bên, độ lệch và ghi chú.
- Giữ toàn bộ xử lý dữ liệu trong máy/server nội bộ.

## 3. Không thuộc phạm vi bản đầu

- Đăng nhập, phân quyền nhiều cấp hoặc lịch sử audit nhiều người dùng.
- Tích hợp ERP hoặc đồng bộ dữ liệu ra hệ thống khác.
- Tự động xử lý mọi loại biểu mẫu không theo cấu trúc.
- Tự động kết luận thay người kiểm tra khi OCR không chắc chắn.
- Triển khai cloud hoặc chia sẻ Internet.

## 4. Anti-goals và ràng buộc

- Không coi cột chỉ có trong CSV như `Dòng`, `Vụ việc` là lỗi khi giấy tờ không có.
- Không coi kết quả OCR có độ tin cậy thấp là dữ liệu xác nhận; phải gắn cờ để người dùng kiểm tra.
- Không gửi ảnh, PDF hoặc dữ liệu HRC ra dịch vụ OCR bên ngoài.
- Không làm mất số 0 đầu, dấu gạch nối hoặc độ chính xác của mã Coil/Heat.
- Không tự động ghép mơ hồ khi có nhiều dòng trùng khóa; phải hiển thị để người dùng xử lý.

## 5. Các phương án đã cân nhắc

### Phương án A — OCR theo mẫu cố định

Xoay ảnh, cắt các vùng theo tọa độ cố định và OCR từng ô. Phù hợp nếu chỉ có một mẫu chứng từ, dễ kiểm soát độ chính xác nhưng khó mở rộng khi mẫu thay đổi nhẹ.

### Phương án B — OCR lai có cấu hình mẫu (được chọn)

Dùng cấu hình mẫu cho chứng từ hiện tại: hướng giấy, vùng bảng, hàng tiêu đề, vị trí cột, quy tắc làm sạch và ánh xạ cột. OCR trả về giá trị, độ tin cậy và trạng thái; người dùng sửa trong bảng trước khi xác nhận. Về sau có thể thêm mẫu mới bằng cấu hình thay vì viết lại luồng đối chiếu.

Đây là lựa chọn cân bằng giữa độ chính xác với chứng từ thực tế, khả năng mở rộng và yêu cầu chạy nội bộ.

### Phương án C — OCR bảng tổng quát hoàn toàn

Tự phát hiện mọi bảng, cột và cấu trúc giấy tờ. Linh hoạt nhưng khó ổn định với mã dài, số thập phân và ảnh chụp nghiêng; rủi ro vượt tiêu chí nghiệm thu bản đầu.

## 6. Thiết kế chức năng

### 6.1. Luồng màn hình

1. **Tải dữ liệu công ty**: chọn Excel/CSV, xem trước số dòng/cột, cảnh báo cột thiếu hoặc trùng.
2. **Chuẩn hóa dữ liệu**: loại bỏ lớp công thức dạng `="..."`, chuẩn hóa khoảng trắng, dấu thập phân, mã và tên cột; hiển thị bản xem trước.
3. **Tải giấy tờ**: chọn ảnh hoặc PDF; với PDF scan, chuyển từng trang thành ảnh; với PDF có text, vẫn cho phép dùng OCR ảnh để giữ một luồng nhất quán.
4. **OCR và chọn mẫu**: tự xoay/deskew, nhận diện vùng bảng theo mẫu đã chọn, OCR từng ô; hiển thị ảnh cùng dữ liệu OCR.
5. **Kiểm tra OCR**: bảng chỉnh sửa được; ô độ tin cậy thấp, mã bất thường hoặc không đọc được được tô màu; người dùng xác nhận dữ liệu.
6. **Đối chiếu**: ghép theo `Heat no. + Coil no.`, chạy quy tắc so sánh, hiển thị tổng quan và chi tiết.
7. **Xuất báo cáo**: tải Excel kết quả và tùy chọn tải lại dữ liệu OCR đã xác nhận.

### 6.2. Chuẩn hóa và ánh xạ

Các tên viết hoa/thường tương đương như `SI`/`Si`, `MN`/`Mn`, `Mo`/`MO` được ánh xạ về tên chuẩn nội bộ. `Size` của CSV được ánh xạ với `Coil size` trên giấy tờ nhưng phải giữ cả giá trị gốc để giải thích sai lệch.

Mã `JSP no`, `Heat no`, `Coil no` được lưu dạng chuỗi. Khi làm sạch phải giữ số 0 đầu, dấu gạch nối và không chuyển qua float.

### 6.3. Mô hình trạng thái ô

Mỗi ô đối chiếu lưu: tên trường, khóa dòng, giá trị Excel, giá trị giấy tờ/OCR, giá trị chuẩn hóa, sai số tuyệt đối, sai số cho phép, trạng thái, độ tin cậy OCR và ghi chú.

Trạng thái được xác định theo thứ tự: thiếu hai bên, thiếu một bên, OCR không đọc được, cần kiểm tra thủ công, sau đó mới so sánh. Mã nhận diện phải khớp chính xác; số đo và hóa học dùng sai số theo cấu hình; văn bản chứng nhận dùng chuẩn hóa chuỗi và quy tắc chính xác hoặc kiểm tra thủ công tùy trường.

### 6.4. Ghép dòng

Khóa chính của bản đầu là cặp `Heat no. + Coil no.` sau chuẩn hóa. Kết quả phải xử lý được:

- Dòng có ở cả hai nguồn.
- Dòng chỉ có trong Excel.
- Dòng chỉ có trên giấy tờ.
- Khóa trùng hoặc thiếu một thành phần.

Các trường hợp mơ hồ không tự ghép; hiển thị trong nhóm cần kiểm tra.

### 6.5. Cấu hình sai số

Có cấu hình mặc định theo nhóm và cho phép chỉnh trước khi chạy:

- Mã: khớp tuyệt đối.
- Kích thước, khối lượng, cơ tính, hóa học: sai số tuyệt đối theo cột.
- Văn bản: chuẩn hóa khoảng trắng/chữ hoa thường; không dùng sai số số học.

Giá trị mặc định cụ thể sẽ được tách thành cấu hình để điều chỉnh sau khi có dữ liệu xác nhận từ người dùng; không suy đoán ngưỡng kỹ thuật từ một mẫu duy nhất.

### 6.6. Báo cáo Excel

Báo cáo gồm các sheet: tổng quan, kết quả theo dòng, chi tiết theo ô, dữ liệu OCR đã xác nhận và cấu hình sai số. Màu trạng thái phải nhất quán, có cột giá trị Excel, giá trị trên giấy, độ lệch, sai số cho phép, độ tin cậy OCR và ghi chú.

## 7. Kiến trúc kỹ thuật đề xuất

- Streamlit cho giao diện.
- Python/pandas cho đọc, chuẩn hóa và đối chiếu.
- OpenCV/Pillow cho xoay, deskew, crop và tiền xử lý.
- OCR cục bộ có khả năng xử lý bảng; lớp adapter tách khỏi phần nghiệp vụ để có thể thay engine mà không đổi UI.
- SQLite hoặc file cục bộ cho cấu hình mẫu, cấu hình sai số và phiên làm việc trong bản đầu.
- openpyxl/xlsxwriter cho báo cáo Excel có định dạng.
- Các module dự kiến: `io`, `normalize`, `ocr`, `templates`, `matching`, `comparison`, `reporting`, `ui`.

## 8. Tiêu chí nghiệm thu

- Đọc đúng cấu trúc CSV mẫu và chuẩn hóa được công thức dạng chuỗi.
- Nhận diện/ghép đúng nhiều dòng Coil tương ứng với mẫu chứng từ.
- Đối chiếu được các trường chung và không báo lỗi giả cho cột chỉ có trong Excel.
- Áp dụng sai số theo từng cột.
- Hiển thị được từng điểm lệch, giá trị hai bên và lý do trạng thái.
- Cho sửa dữ liệu OCR rồi mới chạy đối chiếu.
- Xuất được Excel có màu trạng thái và ghi chú.
- Chạy cục bộ, không yêu cầu gửi dữ liệu ra ngoài.

## 9. Các quyết định còn để builder

- Chọn engine OCR cục bộ phù hợp sau khi benchmark trên ảnh mẫu.
- Chọn định dạng lưu cấu hình mẫu và cách quản lý phiên làm việc.
- Chọn bố cục UI cụ thể trong phạm vi luồng màn hình trên.
- Bổ sung kiểm thử đơn vị cho chuẩn hóa, ghép khóa, sai số và trạng thái.

## 10. Câu hỏi cần xác nhận trước khi triển khai

- Có bao nhiêu biến thể layout chứng từ ngoài ảnh mẫu hiện tại?
- Các ngưỡng sai số kỹ thuật chính thức cho từng cột là gì?
- Khi một khóa `Heat no. + Coil no.` xuất hiện trùng, người dùng muốn chọn thủ công hay cho phép ghép theo thứ tự dòng?
- Các trường chứng nhận nào cần đối chiếu bắt buộc trong bản đầu?
