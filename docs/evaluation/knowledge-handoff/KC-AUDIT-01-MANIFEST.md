# Manifest công bố · AMC-KC-AUDIT-01-CLOSURE

**Sau merge #64.** Base hiện tại của audit là `a6fa1976f9a5d4557a4e3b64ac28dec2eb0fc0a4`. Reviewer đã đóng KC-01–07 trong phạm vi tài liệu. Cold Handoff còn NOT_VERIFIABLE (0 phiên độc lập). [Chứng nhận main](../round64/MAIN-64.json) · [Bàn giao hiện hành](../../../HANDOFF.md). Phần sau giữ nguyên số liệu và SHA của vòng công bố đầu tiên.

Mở danh sách file tại SHA của PR. Người phản biện có thể tải từng blob từ GitHub và so với Git trên máy của mình. Hai commit audit local được giữ nguyên trong lịch sử nhánh. Base là `053410d161b15285a1ef264f853d4920a3d559e1`. Audit gốc là `90737b30c1895a0ddfbec9ba1ccdf333b4905b12`, tree `8d5ec4f6e20451a0cec1d78c6f4f3707ed7bc8bc`, cha `fe61923e7f53a28e215a191491e53f80cbfef000`. SHA và tree bàn giao cuối cùng nằm trong mô tả draft PR để tránh tự tham chiếu.

| Mục cần kiểm | Nguồn công khai | Phạm vi và giới hạn |
|---|---|---|
| Baseline và 7 finding | [Báo cáo và bảng AMC-KC-01–07](KC-AUDIT-01.md), [Git/CI/ancestry](KC-AUDIT-01-REFS.json) | Mỗi finding ghi dòng trên base, rủi ro, thay đổi và owner. Việc thu dọn năm PR cần quyết định riêng. |
| Chỉ thị và thẩm quyền | [Nguồn chuyển qua Reviewer](KC-AUDIT-01.md#directive-provenance), [ma trận](../../../AGENTS.md), [verdict](../../../.github/pull_request_template.md) | Đối chiếu phần owner chỉ đạo và phần diễn giải trong repo. |
| Kiểm tra liên kết | [Kết quả audit gốc](KC-AUDIT-01-LINKS.json) | 424 tham chiếu nội bộ tại SHA ghi trong JSON. Bao gồm đường dẫn và anchor. Kết quả recheck của candidate cuối ghi trong draft PR. |
| Checkout sạch | [Biên nhận](KC-AUDIT-01-DRILL.md), [JUnit đã lược hostname](KC-AUDIT-01-JUNIT.xml) | Một test hợp đồng WF-03 trên `fe61923e` và HTTP health qua TestClient. Đây là phép thử của người làm audit. |
| Tiếp quản độc lập | [Phiếu khởi tạo cho AI mới](KC-AUDIT-01-COLD-PROMPT.md) | Chỉ chuyển permalink của phiếu tại candidate SHA cho phiên mới được phép. Số phiên độc lập tại thời điểm công bố bằng 0; kết quả NOT_VERIFIABLE. |
| Danh sách file và diff | Trang **Files changed** và compare bất biến từ base tới head trong mô tả PR | Tái lập bằng `git diff --name-status <base> <head>` và `git diff --check <base> <head>`. |
| Dấu vết ứng viên sản phẩm #64 | [Gói proof theo commit](https://github.com/datnv41001/ai-company/blob/f4f0d990e7841e52173b1f733f2f6649db6ad1c5/docs/evaluation/round64-closure-proof/START-HERE.md) | Quyết định đối với #64 độc lập với audit tài liệu. R64-02 mở; nguyên nhân timeout Storyboard lần đầu còn chưa xác định. |

**Phạm vi công bố.** Chỉ công bố các thay đổi văn bản, JSON và JUnit đã kiểm trong diff. Kho đã có sẵn attribution tác giả của hai commit lịch sử. Git bundle, ZIP local, log máy, bản lưu hội thoại, dữ liệu benchmark kín và credential không nằm trong gói công bố. Các trích dẫn bằng hash trong báo cáo chỉ định danh nguồn. Phạm vi kiểm dữ liệu là nội dung bổ sung và các object mới được đẩy.

**GitHub Actions.** Workflow `ci.yml` chạy cả trên push và pull_request, gồm job `workforce-model`. Commit công bố dùng chỉ thị skip Actions để giữ đúng giới hạn inference. Ghi CI nhánh audit là **không chạy**. Kết quả CI được trích ở REFS thuộc main và PR sản phẩm tại các SHA tương ứng.

**Quyết định chờ.** Product Owner hoặc Independent Reviewer có thể tổ chức một phiên AI mới trong sandbox chỉ đọc và ghi transcript, lỗi, kết quả từng tiêu chí theo protocol hiện hữu. Independent Reviewer quyết định nghiệm thu audit sau khi đọc bằng chứng remote. Production và Commercial GA vẫn NO-GO.
