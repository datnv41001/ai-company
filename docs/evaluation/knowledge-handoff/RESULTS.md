# Nghiệm thu tiếp quản AMC từ repository · 26/11/2026

**Mục tiêu.** Người kế nhiệm có thể chọn đúng công việc Marketing, tìm căn cứ và chạy thử nội bộ từ checkout. Trước thay đổi, README còn mô tả bootstrap, sổ trạng thái chưa phản ánh Workforce và journal hiện hành, còn mẫu PR thiếu phần ghi bất đồng. Base là [main sau #48](https://github.com/datnv41001/ai-company/commit/380be3eb70a41424c6d45318b0b1890fa950970a).

**Thiết kế phép thử.** Một phiên Codex mới được tạo với chế độ không kế thừa lượt chat. Đầu vào chỉ gồm nhiệm vụ tiếp quản, SHA và giao diện đọc Git. Broker trả danh sách file hoặc đoạn trích từ blob đúng SHA; không có thao tác ghi, gọi mạng hoặc cấp thông tin đăng nhập. Người vận hành chạy lệnh do AI chọn trong bản sao tạm của cùng cây với dữ liệu tổng hợp. Đây là bài đọc và tái lập vận hành có trung gian, với một phiên AI. [Nhật ký đọc](reads.jsonl) · [Kết quả môi trường](run.json)

| Nội dung kiểm | Kết quả quan sát được |
|---|---|
| Sứ mệnh và khách hàng | Tìm đúng công việc Marketing được người có thẩm quyền chấp nhận, mô hình Agency/In-house và trách nhiệm ngân sách. Dẫn đến sứ mệnh và đặc tả. |
| Kiến trúc và nghiệp vụ | Lần từ brief được duyệt qua commission, WF-13, QA theo nhóm, snapshot khách và biên nhận dispatcher. Phân biệt đường tạo bảy task tất định. |
| Trạng thái phát triển | Nêu đúng core v26, Business v3, C3 v5, ops/2 tại mốc main; năm vai trò có binding trong hai tiểu quy trình. Phân biệt số đó với 37 vai trò và 24 workflow mẹ. |
| Khoảng trống | Chỉ ra thiếu nghiệm thu practitioner, số đo chi phí, billing và adapter ghi ngoài; giữ Commercial GA NO-GO. |
| Lý do quyết định | Giải thích tình huống A → B → A: digest có thể trùng lại, QA phải kiểm thêm revision để từ chối quyết định cũ. Dẫn được ADR và ca test. |
| Khởi chạy và kiểm thử | Chọn đúng script tạo môi trường, Uvicorn trên loopback và suite API. Broker xác nhận ứng dụng khởi động, ba trang trả HTTP 200, dừng đúng tiến trình. |
| Công việc tiếp theo | Đúng thứ tự phụ thuộc #49 → #52, ca biên tập câu lặp trên landing dịch vụ và pilot hai brief RFQ/dịch vụ khi có người dùng nghiệp vụ. |

**Phiên bản và lệnh.** Cây ứng viên dùng để kiểm là [82d5b246](https://github.com/datnv41001/ai-company/commit/82d5b246143e893f49467e1ca319dfb9d1551229). Trên Windows, Python 3.12.14 và SQLite, chạy các lệnh dưới đây từ bản sao dev, dùng bộ phụ thuộc phát triển của repository. Thay PORT bằng cổng loopback còn trống.

```text
python scripts/init_env.py
python -m uvicorn app.main:app --no-proxy-headers --host 127.0.0.1 --port PORT
GET /api/health
GET /
GET /docs
python -m pytest -q tests/test_api.py
python -m pytest -q tests/test_revision_evidence.py::test_title_only_revision_rejects_old_approval_and_rejection
```

Suite API đạt 12/12 trong 6,58 giây. Ca QA bổ sung do AI yêu cầu đạt 1, bỏ qua 1 trong 10,99 giây ở môi trường SQLite. Lần bổ sung kết thúc sau khi AI nộp nhận xét; số này do người vận hành đối chiếu. Lần khởi động đầu tiên lỗi `WinError 10106` khi import asyncio vì bộ chạy lọc nhầm biến Windows `SYSTEMROOT`. Sau khi sửa cách lọc tên biến trong harness, cùng checkout chạy được. Lỗi đó không thay đổi mã sản phẩm.

**Phản biện và xử lý.** AI tìm được hai chỉ dẫn khác nhau về onboarding: phần đầu README nói xác minh địa chỉ trước khi chọn workspace, nhưng bước đầu của walkthrough lại nói đăng ký tenant. Đối chiếu [hợp đồng web và API tương thích](../../PR16-ONBOARDING.md) xác nhận nhận xét. README hiện mô tả đúng trình tự web tại cả hai chỗ. Phần giải thích các mức nghiệm thu đã được quy về một từ điển trong [sổ trạng thái](../../IMPLEMENTATION_STATUS.md). Những chỉnh sửa này được đưa vào sau snapshot của phép thử.

**Bàn giao và giới hạn.** [Bản đồ](../../KNOWLEDGE_MAP.md) chỉ đến tài liệu hiện hữu. AGENTS, mẫu PR, README, HANDOFF, sổ trạng thái, hướng dẫn starter lịch sử, tài liệu GA và sổ nguồn đã được điều chỉnh cùng gói. Không đổi schema, model, RLS, runtime hoặc adapter. Khi cần quay lại bộ quy tắc trước, revert commit tài liệu bằng PR và giữ biên bản này trong lịch sử. Mục 5 và 13 của [mẫu bàn giao](../../../.github/pull_request_template.md) trỏ tới nguồn và CI của đúng revision. Các nguồn ngoài được dùng và giới hạn quyền được ghi ở [sổ nguồn](../../research/SOURCE_REGISTRY.md). Chi phí lao động và lợi ích thương mại của quy trình tiếp quản chưa đo.

**Câu hỏi cho reviewer.** Có điểm nào còn cho phép nhầm capability sandbox với một workflow đã nghiệm thu thương mại? Một người mới có thể chỉ đúng ai được quyết định cho phép chi tiền, merge và thay đổi phạm vi V1 không? So câu trả lời với bằng chứng ở revision hiện hành trước khi sửa sổ trạng thái.
