# Hồ sơ chung, ghi đè theo thương hiệu và brief nội bộ

Bản triển khai mở đầu C2.1 và C2.5 dùng core v22 ở `c847f910b88c243932f67617c248bd223617b51b` và migration riêng `amc_business` v1. Phạm vi đã triển khai gồm bốn trường hồ sơ, tiến độ, lưu theo phiên bản, truy nguyên từng trường và lập brief cá nhân khi còn thiếu đầu vào. Objective/KPI có cấu trúc, sản phẩm/SKU, duyệt thương mại, ICP và luồng AI là các increment tiếp theo. Commercial GA **NO-GO**.

## Chạy và kiểm lại trên máy khác

Từ checkout dùng cấu hình môi trường thử trong [HANDOFF](../../HANDOFF.md). Trên Docker chạy `docker compose up --build -d`. Job migrate cần hoàn tất trước khi mở API. Với PostgreSQL native, dùng publisher riêng để chạy `python migrations/apply.py`, sau đó khởi động API với `amc_runtime`. Quyền runtime chỉ đọc row đủ điều kiện qua RLS và gọi hàm append đã ký. PostgreSQL đặt khóa giao dịch theo tenant/client để đồng bộ mọi lưu công ty, ghi đè và ghim brief. SQLite cục bộ giữ một writer mỗi lần.

Chạy `python -m pytest -q tests/test_business_workspace.py` tại gốc repo. Mặc định chạy phần SQLite. Để chạy cả hai engine, dùng các biến và DB loopback tên `amc_test_*` của [job CI](../../.github/workflows/ci.yml). Trên PostgreSQL native 16.16 và SQLite, năm ca của bộ API đầu tiên đạt. Có ca chạy hai phiên ghi cùng revision, kiểm RLS với owner/editor/worker và đối chiếu số run, brief Workforce, task, dòng ledger, số tiền giữ và chi trước/sau. Ca SQLite kiểm khôi phục lệnh, hai thương hiệu của cùng khách và phân cách scope. [Kiểm thử qua API và runtime DB](../../tests/test_business_workspace.py)

## Dữ liệu và cách dùng API

Đăng nhập bằng tài khoản đã xác minh. Với tiền tố `P=/api/tenants/{tenant}/clients/{client}` và `B=P/brands/{brand}/business-workspace`, bốn field là `name`, `sells`, `audience`, `goal`.

| Thao tác | Hợp đồng |
| --- | --- |
| `GET B` | Mở lại trạng thái đã lưu, quyền `can_edit`, tiến độ, provenance và danh sách tối đa 50 brief gần đây của người đang đăng nhập. |
| `POST P/business-profile` | Gửi `key`, `expected_revision` và `fields`. Chỉ những khóa được gửi mới thay đổi. Giá trị null xóa thông tin chung. |
| `POST B/overrides` | Gửi `key`, `expected_revision` của thương hiệu, `expected_company_revision`, `fields`. Mỗi field nhận `{"mode":"override","value":"..."}`, `{"mode":"empty"}` hoặc `{"mode":"inherit"}`. |
| `POST B/briefs` | Gửi key, hai revision đang xem và `title`. Kết quả gồm id, thời điểm, người sở hữu qua quyền truy cập, revision hai cấp, giá trị đã ghim, các field còn thiếu và các bước kiểm chứng còn mở. |
| `GET B/briefs/{id}` | Tải lại brief bất biến thuộc brand và người sở hữu. Các lần sửa công ty sau đó chỉ thay đổi lần đọc hồ sơ hiện tại. |
| `GET P/business-profile/revisions/{n}`, `GET B/overrides/revisions/{n}` | Truy lại revision gốc của một giá trị và lần đổi trạng thái kế thừa ở brand. |
| `GET P/business-profile/commands/{key}`, `GET B/commands/{key}` | Tìm lại kết quả riêng của người gửi khi mất phản hồi. Trả 404 khi chưa tìm thấy lệnh trong scope đó. |

Mỗi lượt sửa tạo một khóa lệnh trước khi gửi. Giữ nguyên khóa và payload khi thử lại. Server đọc lại receipt trước khi so revision, nên cùng lệnh vẫn trả về cùng kết quả khi hồ sơ đã có sửa đổi tiếp theo. Khi nhận 409 do revision thay đổi, tải `GET B`, so từng field, chọn lại giá trị và tạo lệnh mới. Field chưa cung cấp có revision nguồn 0. Khi bỏ ghi đè, provenance ghi cả revision chung hiện tại và revision brand đã bỏ ghi đè.

Owner, admin và editor được ghi. Viewer nội bộ được đọc hồ sơ. Chỉ người tạo brief đang có quyền staff trong đúng workspace mới được đọc brief đó. Portal, người ngoài tenant và worker không có quyền vào phần hồ sơ này. Brief có trạng thái `internal_draft` và không yêu cầu recipient. Cần kiểm riêng nguồn Marketing, KPI, baseline, target và actual trước khi quyết định sử dụng ở nghiệp vụ sau.

## Nâng cấp, phục hồi và rollback

Chạy `python tests/check_workspace_upgrade.py` với DSN publisher và runtime cùng trỏ tới **DB thử trống** trên loopback, tên bắt đầu bằng `amc_test`. Test dựng đúng binary `c847f910`, điền một hồ sơ C1, chạy hai lần publisher mới, đối chiếu row và toàn bộ core marker, rồi kiểm tra phiên bản module lạ bị từ chối. Lần cuối test cố ý để marker 99 ở DB thử để xác minh startup. Job CI khôi phục archive sang DB riêng và so 26 bảng, bao gồm row đã điền đủ ba loại công ty, thương hiệu, brief và marker module. [Route từ v22](../../tests/check_workspace_upgrade.py) · [Đối chiếu bản khôi phục](../../tests/check_postgres_upgrade.py)

Core 023 được dành cho Identity A1. Khi tích hợp A1, giữ nguyên cả hai lịch sử migration, dùng đúng binary tương thích core và chạy lại route từ v22 cùng bộ kiểm phiên/module. Khi cần rollback ở mốc này, dừng ghi hồ sơ, sao lưu cả DB rồi chạy lại binary C1 tương thích core v22. Phần bổ sung ở schema riêng có thể giữ nguyên để đối soát hoặc khởi động lại C2. Không xóa bảng chứa nháp và lịch sử người dùng. [DDL module v1](../../migrations/business_workspace/001_workspace.sql)
