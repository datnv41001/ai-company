# Danh mục Marketing cho nhân sự nội bộ

Increment này dùng C1 core v22 và `amc_business` v2. Base tích hợp là PR #27 ở `222ac7e2565d18285e23bafbf59fee9505c113b9`. Nhân sự chọn khách hàng và thương hiệu tại Hồ sơ doanh nghiệp, rồi mở **Danh mục, điều khoản và mục tiêu**. Tài khoản chỉ xem được tìm kiếm và xem chi tiết. Editor có thể lập nháp. Admin/owner ghi các sự kiện duyệt, tranh chấp, thay thế và thu hồi kèm lý do. Server kiểm quyền trong từng giao dịch.

## Từ SKU đến giá đã duyệt

1. Lập sản phẩm hoặc dịch vụ với tên và SKU chuẩn. Lập biến thể bằng cách chọn sản phẩm theo tên rồi cấp SKU riêng. Tạo thị trường với mã kinh doanh xác định và các locale phục vụ.
2. Lưu điều khoản theo đúng biến thể, thị trường, vùng, locale và kênh. Các chiều bán lẻ/bán buôn, trả trước/tín dụng, tiêu chuẩn/mở rộng, selling unit và khoảng số lượng có thể cùng tồn tại. Tồn kho ghi thời điểm quan sát và thời điểm hết hạn. Khi có nhiều nguồn mâu thuẫn, ghi tranh chấp hoặc thay thế, chọn bản ưu tiên và nhập lý do. API C1 đối chiếu lại đúng placement, phạm vi và hiệu lực của nguồn.
3. Lập giá bằng đơn vị tiền tệ quen dùng. Ví dụ `12.34 USD` trên 1 m² thành đúng 1234 minor units. Với VND/JPY, chỉ giá trị biểu diễn chính xác bằng đơn vị nguyên mới có thể lưu. Chọn MOQ, bậc, thuế, điều kiện, hiệu lực và nguồn điều khoản theo tên. Giá theo hộp và giá theo kg có cơ sở khác nhau. Cần cung cấp cơ sở đúng ngay khi lập offer. Luồng này chưa có hệ số chuyển đổi bao gói được duyệt.
4. Tìm theo tên/SKU, mở chi tiết và xem trạng thái trước khi duyệt. Bản ghi chưa có mã danh mục được gắn nhãn cần đối soát. Dữ liệu ban đầu, SHA và revision cũ của C1 vẫn truy xuất được qua lịch sử kỹ thuật.

Mã SKU được cấp riêng trong phạm vi tenant/client/brand cho cả sản phẩm, dịch vụ và biến thể. Mã thị trường dùng namespace khác trong cùng phạm vi. Lệnh so trùng mã và tên thị trường trùng chính xác với bản ghi cũ, kể cả khi editor thiếu quyền xem đối thủ. API chỉ báo cần đối soát. Tên gần giống, mã kinh doanh khác nhau và các địa bàn ngoài danh mục Hà Nội, TP.HCM, Đà Nẵng cần người nghiệp vụ xác nhận. Địa bàn dùng mã C1, điều kiện thương mại dùng ID có nhãn tiếng Việt/Anh. Bản gốc vẫn giữ nguyên nhãn đã ký. [Hợp đồng phạm vi](../../app/commercial_scope.py) · [Ràng buộc master](../../app/catalog_identity.py)

## Brand, audience và KPI

Hướng dẫn thương hiệu có giọng điệu. ICP và segment có mô tả, thị trường, nhu cầu, phân biệt giả thuyết và thông tin được khai báo có nguồn. Chỉ định source theo tên khi đã có quyền xem. Thiếu chứng cứ được hiển thị trên màn hình. Người thiếu quyền đọc một quan hệ chỉ thấy trạng thái hạn chế ở chi tiết. C2 chưa kiểm chứng tính đúng đắn hoặc độ liên quan của chứng cứ ngoài đời.

Mục tiêu theo cây C1 có các cấp công ty, thương hiệu và chiến dịch. Mục tiêu cấp công ty trong increment này vẫn nằm trong kho dữ liệu của brand đang chọn. Việc chia sẻ cây mục tiêu thực sự giữa các brand khác với kế thừa bốn trường hồ sơ chung đã triển khai ở PR #27. KPI ghi người phụ trách, cách đo, đơn vị, kỳ và nguồn. Mốc gốc, chỉ tiêu và thực tế để trống được hiển thị riêng. Giá trị 0 được giữ nguyên. KPI thiếu nguồn có thể lưu nháp và cần bổ sung nguồn trước duyệt. Bước ghim các mục catalog cụ thể vào brief nội bộ và C3 có hợp đồng riêng.

## Chạy, đối chiếu và phục hồi

Chạy publisher và API theo [runbook của hồ sơ chung](C2-WORKSPACE-RUNBOOK.md). Với Docker dùng `docker compose up --build -d`. `GET .../brands/{brand}/catalog/items?kind=product&q=...&limit=20` trả các bản hiện tại, cursor theo stable subject và nhãn nghiệp vụ. `POST .../catalog/items` dùng key, CAS, actor và chính sách C1. Mất phản hồi sau khi lưu có thể tìm lại từ `GET .../catalog/commands/{key}`. Lệnh duyệt tiếp tục dùng endpoint sự kiện theo revision C1.

Chạy `python -m pytest -q tests/test_marketing_catalog.py tests/test_knowledge_scope_aliases.py tests/test_knowledge_commercial.py` trên DB thử. Bộ tập trung ban đầu đạt 26/26 trên SQLite và PostgreSQL native 16.16. Chạy `python tests/browser_catalog.py` khi API local dùng PostgreSQL và có biến thử nghiệm browser như [CI](../../.github/workflows/ci.yml). Bộ browser đi qua form ở 1280×850 và 390×844, lập giá, đối chiếu giá thật ở API, xác nhận nhãn giả thuyết sau đăng nhập lại, chụp màn hình và đo số run/ledger trước sau. [Fixture và kiểm thử UI](../../tests/browser_catalog.py)

Migration module v2 tạo hàm kiểm trùng dùng signed actor/transaction và cập nhật quy tắc so điều kiện. Core 023 vẫn dành cho Identity A1. Sao lưu đầy đủ DB trước khi đổi binary. Binary v1 từ chối marker v2. Nếu cần quay lại v1, dừng ghi danh mục, lưu archive hiện tại, phục hồi bản sao v1 sang DB mới rồi đối chiếu các thay đổi thực hiện sau backup trước khi chuyển kết nối. Commercial GA **NO-GO**. Các phép đo usability với người dùng độc lập, chuyển đổi đơn vị tùy biến và kết nối AI theo nguồn có thẩm quyền còn mở.
