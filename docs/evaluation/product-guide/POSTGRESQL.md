# Quyền thực thi guide và rollback

Release `WF-06/product-use-guide@1` chỉ nhận task `amc.product-use-guide/1` đã gắn với Strategy Handoff /2. PostgreSQL kiểm tra scope, in-house, người nhận, document/revision/digest, QA receipt mới nhất, nguồn của mandate, từng chữ ký QA, target generation, các dependency và thời hạn, profile doanh nghiệp cùng quyền registry của đúng campaign. Manifest con phải trỏ đúng brief con, chứa cùng binding và projection của run. [Phép kiểm PostgreSQL](../../../migrations/product_guide.sql)

Ở bước tạo offer và lúc nhận kết quả, predicate dùng các khóa cùng phạm vi với phía biên tập. Nếu phía người dùng đang giữ khóa để trả lời một thay đổi đồng thời, dispatcher nhường vòng xử lý rồi kiểm lại. Ở lúc worker nhận offer, database kiểm thêm một lần trước khi trả envelope. Quyền đọc trực tiếp kho Knowledge của worker và dispatcher giữ nguyên. [Phép kiểm bằng login dispatcher và người nhận](../../../tests/test_product_guide_authority.py)

| Thu hồi trong fixture | Tín hiệu và xử lý |
|---|---|
| Source sau admission, trước dispatch | Run chuyển `failed / guide_authority_changed`, chưa tạo attempt hoặc ghi giữ ngân sách cho guide. |
| Hạ quyền recipient sau offer | Worker không nhận được nội dung. Dispatcher đóng khoản giữ của offer chưa gửi. |
| Thu hồi mandate sau khi worker đã nhận | Worker có thể báo số token đã dùng. Database bỏ raw reply và giữ riêng metering nếu chủ lease, hạn báo và kiểu dữ liệu còn đúng. |
| Strategy đổi revision sau khi worker đã báo | Dispatcher kiểm lại trước khi chuyển bất kỳ kết quả nào thành checkpoint. Usage có thể đối chiếu theo đúng attempt và rate tại lúc đặt giữ. |

Các ca đã báo hợp lệ ghi nhận 110 token vào, 12 token ra, đóng lease và không tạo Content document. Phí trong fixture bằng 0 theo rate cấu hình. Khi không có số liệu xác nhận cho attempt đã gửi, số giữ tiếp tục chờ receipt đối soát theo cơ chế ledger hiện hành. [Kiểm thử lease và đối soát](../../../tests/test_product_guide_fence.py)

## Vận hành trên máy khác

1. Chạy publisher bình thường bằng `python migrations/apply.py` với DSN migration của môi trường thử nghiệm. Publisher cài predicate và policy trong cùng transaction. Core v26, C3 writer v5 vẫn là version của lớp dùng chung. API guide kiểm các policy đọc theo edition, trigger lease và quyền execute của helper trước khi khởi động. [Kiểm tra cấu hình hiệu lực](../../../migrations/product_guide_contract.py)
2. Khi rollback, quản trị campaign dùng thao tác `revoke` cho hai skill `director` và `content` của đúng release guide tại endpoint registry campaign hiện hữu. Giữ worker/dispatcher tương thích để đóng các lease đang xử lý và đối soát usage, kể cả khoản giữ chưa có receipt. Sau đó mới chuyển traffic về binary trước nếu cần.
3. Giữ migration và lịch sử trên PostgreSQL. Policy theo marker `guide/1` bảo vệ brief, manifest, run, deliverable và audit event có thể chứa trích đoạn QA của guide. Trigger nhận diện audit event qua document, run hoặc task của chính guide. Phép thử dùng cùng phiên người nhận trên hai edition, đọc lại các dòng Strategy và audit event lịch sử, sau đó khôi phục marker và đối chiếu lịch sử guide. [Phép thử edition đọc](../../../tests/test_product_guide_rollback.py)
4. Để kiểm tra chuyển phiên bản trên database tổng hợp đã cài bản #69, chạy `python tests/check_product_guide_upgrade.py --previous-checkout <checkout-69> --report <report.json>` với môi trường bootstrap PostgreSQL của bộ test. Báo cáo ghi số dòng và SHA-256 của mười bảng trước và sau hai lượt publisher. Thêm `--pg-bin <thư-mục-client-PostgreSQL>` để chạy cả vòng dump và restore bằng công cụ PostgreSQL. Trường `native_archive` phân biệt hai kết quả. [Phép thử cutover và restore](../../../tests/check_product_guide_upgrade.py)

Production và Commercial GA vẫn NO-GO.
The [PostgreSQL 16.16 cutover receipt](CUTOVER.json) identifies the predecessor tree, table digests, repeat publication and legacy-reader rehearsal.
