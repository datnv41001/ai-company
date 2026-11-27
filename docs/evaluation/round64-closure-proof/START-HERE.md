# PR #64 · Đối chiếu phiếu Content /2

Head `a0c43a15dbcec783a859c4c525fec2671206483c`, base `053410d161b15285a1ef264f853d4920a3d559e1`, trial `80fa77de08afbe0b308fd56ddf3738fbf0b2938d` và tree `1c6779ae574d0cd2efd5c8f8798162a7438a0b52`. Bản đối chứng cũ là `d79f7637`. [Phạm vi, versioning, lệnh chạy và rollback](review/README.md).

1. Đọc [hai phiên trên head cũ](review/reviewed-handoff-red.json) và xem [ảnh RED](before/recipient-order.png). Trên trial mới, [lineage](lineage/lineage.json) có hai phần `signed_review` và `delivered`. Tra cùng receipt ID; trong `work_order.brief` đối chiếu buyer action, văn phong, requirements, exclusions và acceptance criteria. Phần `guidance` tách hướng viết khỏi câu sản phẩm.
2. Đọc [nội dung thực tế trong DOM người nhận](screens/recipient-visible-order.txt), [ảnh điện thoại](screens/recipient-requirements-390-dark.png), [ảnh desktop](screens/recipient-requirements-1280-light.png), [ảnh giữ việc khi mâu thuẫn](screens/brief-conflict-hold.png) và [số đo 12 phiên UI](screens/browser-measurements.json). Run của trình duyệt có định danh riêng.
3. Kiểm [Purchasing directors tại quầy](lineage/placement.json), [thu hồi và gửi lại](lineage/authority.json), [giữ thông tin nguồn riêng tư](lineage/private-handoff.json), [xử lý receipt /1](lineage/legacy-handoff.json) và [các ca âm](lineage/negative-cases.json).
4. AMC-R64-02 vẫn OPEN. Xem [JUnit lịch sử đã bỏ dữ liệu máy](sales/reviewed-native-failure.xml), [đối chứng Sales trên hai SHA](review/sales-observations.json), [các lần chạy native](native-runs.json) và [JUnit CI trong từng checkout](ci.json). Phép thử thời gian có kiểm soát phân biệt được hai nhánh lỗi; cả hai lượt gửi tự nhiên trả 200.
5. Xem [telemetry các job model đã cấp phép](model-resources.json), [output thực theo checkout](actual-model.json) và [đề xuất #65](review/NEXT-65.md). Chi phí runner chưa có hóa đơn. Khâu tạo và nhận phiếu dùng worker có kiểm soát.
6. Tính SHA-256 của ZIP so với mô tả PR, kiểm CRC bằng `python -m zipfile -t runtime-handoff.zip`, rồi so từng đường dẫn và digest với [manifest](files.json).

Production và Commercial GA vẫn NO-GO. Dừng ở draft để người review quyết định.

Lượt CI trial đầu tiên đạt 767 test rồi dừng vì timeout ở nút “Xem kết quả và chi phí” trong suite Storyboard cũ. Cùng phép thử đạt trên Windows và trên PR head. Maintainer chạy lại đúng job API integration, cùng tree; hai job model của PR giữ nguyên giờ bắt đầu và kết thúc. Xem [cả hai lượt CI](ci/storyboard-attempts.json) và [JUnit kiểm riêng Storyboard](native/storyboard.xml). Nguyên nhân của timeout đầu chưa xác định.

Để ghi thêm cờ consent `granted` ngay trên inquiry thứ hai, sau khi push đã chạy thêm một probe mỗi checkout. [Lượt #63](sales/sales-consent-base.json) và [lượt #64 đã review](sales/sales-consent-old.json) đều ghi `granted: true`, purpose `quote_request`. Tổng cộng 4 lượt tự nhiên (2 mỗi checkout), cả 4 trả 200; các nhánh đối chứng trả 409. Không có sửa đổi Sales. [Mã probe bổ sung](sales/probe_sales_consent.py)
