# Dùng Hồ sơ doanh nghiệp

Đăng nhập vào workspace và mở **Hồ sơ doanh nghiệp**. Trên điện thoại, mục này nằm ở đầu workspace, ngay sau bộ chọn không gian làm việc. Tên workspace xuất hiện bên trên tên hồ sơ. Chọn khách hàng rồi chọn thương hiệu. Khi chỉ có một lựa chọn, hệ thống chọn sẵn. Với workspace mới, dùng **Thêm khách hàng**, sau đó **Thêm thương hiệu** để thiết lập phạm vi đầu tiên.

## Lưu bốn thông tin cơ bản

Trong **Hồ sơ chung**, nhập tên doanh nghiệp, sản phẩm hoặc dịch vụ, khách hàng mục tiêu và mục tiêu Marketing. Có thể lưu hai trường hôm nay và quay lại bổ sung sau. Nhấn **Lưu thay đổi** rồi chờ dòng **Đã lưu thay đổi**. Bộ đếm cho biết số trường đã lưu có giá trị đối với thương hiệu hiện tại. Các trường chưa điền sẽ xuất hiện thành câu hỏi trong brief.

Các thương hiệu thuộc cùng khách hàng dùng chung hồ sơ doanh nghiệp. Trong **Theo thương hiệu**, mỗi trường có ba lựa chọn.

| Lựa chọn | Kết quả khi lưu |
| --- | --- |
| Từ hồ sơ doanh nghiệp | Hiển thị giá trị hiện tại của doanh nghiệp. |
| Điều chỉnh cho thương hiệu | Dùng giá trị riêng vừa nhập cho thương hiệu đã chọn. |
| Chủ động để trống | Giữ trường trống ở thương hiệu này dù doanh nghiệp đã điền. |

Dòng dưới mỗi trường ghi giá trị đã lưu, nơi cung cấp giá trị và số bản lưu. Để dùng lại dữ liệu chung, chọn **Từ hồ sơ doanh nghiệp** rồi lưu. Chỉ số hoàn thiện thay đổi theo thương hiệu đang mở.

## Chuẩn bị brief nghiên cứu

Mở **Brief nháp**, nhập tên và chọn **Tạo brief nháp**. Bạn có thể tạo brief riêng trong khi chưa có giá hoặc người nhận. Brief ghi lại thông tin tại thời điểm tạo, câu hỏi còn trống, tình trạng xác nhận nguồn và các chỉ số KPI còn thiếu. Dùng danh sách brief của bạn để mở lại. Các lần sửa hồ sơ sau đó có hiệu lực với brief mới.

Đây là bước chuẩn bị nội bộ. Để gửi cho khách hoặc chạy một quy trình AI, cần thực hiện các bước nghiệp vụ tương ứng ở luồng khác.

## Khi kết nối gián đoạn hoặc hai người cùng sửa

- Nếu trình duyệt chưa nhận được xác nhận, chọn **Kiểm tra kết quả**. Khi máy chủ đã ghi, hệ thống mở lại đúng kết quả của lần lưu đó. Sau khi tải lại trang, đăng nhập lại đúng tài khoản và mở đúng workspace, khách hàng, thương hiệu. Tab chỉ giữ các mã cần để tìm lại lần lưu. Nếu máy chủ vẫn chưa nhận và bạn đã tải lại, chọn **Nhập lại thao tác** để gửi theo cùng mã.
- Nếu người khác đã lưu trước, màn hình **Đối chiếu thay đổi** hiển thị bản trên máy chủ cạnh bản bạn đang sửa. Chọn từng trường cần giữ rồi bấm **Áp dụng các trường đã chọn**, hoặc chọn **Dùng bản máy chủ**. Khi vừa tạo brief thì so sánh lại thông tin sẽ ghim trước khi xác nhận.
- Khi quyền xem bị thu hẹp, giao diện xóa phần hồ sơ khỏi màn hình sau lần kiểm tra quyền. Liên hệ quản trị viên của workspace nếu cần cấp lại quyền. Người nhận tại cổng khách hàng chỉ dùng giao diện bàn giao theo quyền được cấp.

## Kiểm thử giao diện bằng dữ liệu mẫu

Bộ kiểm thử trong `tests/browser_knowledge.py` thao tác trên Chromium thật tại 1280 × 850 và 390 × 844. Tạo mới cơ sở dữ liệu PostgreSQL dùng cho kiểm thử và khởi động API theo hướng dẫn chạy của repo. Với Compose đã chạy ở cổng 8000, dùng PowerShell từ thư mục gốc.

```powershell
$env:AMC_BROWSER_TEST_URL = 'http://127.0.0.1:8000'
$env:AMC_BROWSER_MAILBOX_PROJECT = 'amc-acceptance'
$env:AMC_KNOWLEDGE_EVIDENCE = Join-Path $env:TEMP 'amc-knowledge-evidence'
python -m pip install -r requirements-browser.txt -r requirements-dev.txt
python -m playwright install chromium
python tests/browser_knowledge.py
```

Tên project phải trùng với lệnh khởi động Compose. Với PostgreSQL và API chạy trực tiếp, dùng `AMC_DEV_MAILBOX_DIR` trỏ tới hộp thư dev của API và `AMC_MIGRATION_DSN` tới database dev thay cho `AMC_BROWSER_MAILBOX_PROJECT`. Có thể trỏ `AMC_BROWSER_EXECUTABLE` đến Chromium cài sẵn. Script tạo tài khoản, khách hàng và thương hiệu tổng hợp mới cho từng kích thước.

Thư mục bằng chứng chứa ảnh PNG và `metrics.json` với kích thước, phiên bản trình duyệt, phiên bản schema, SHA, số brief, số run và số dòng ledger. Thời gian lưu bốn trường là tổng thời gian tự động điền và lưu hai nửa của hồ sơ. Thời gian đến brief đầu tiên tính từ lúc đã mở đúng khách hàng đến lúc thấy nháp sau khi lưu, bao gồm tải lại và đăng nhập lại trong bài thử. Các số này đo thao tác tự động trên fixture. Việc xác nhận mục tiêu ba phút cho thiết lập và năm phút cho brief cần đo với người dùng.

Phạm vi năm persona ở đây là hồ sơ và brief đầu tiên. Các ca bậc giá, tranh chấp thương mại, duyệt claim theo qualification và nội dung công khai từ nguồn hạn chế cần được nghiệm thu ở màn hình tương ứng sau khi có các chức năng đó.
