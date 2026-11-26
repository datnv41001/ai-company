# Vận hành một chiến dịch trên sandbox

Người quản lý agency chọn mục tiêu, ICP và sản phẩm trong Business Knowledge, dùng các revision đã duyệt để tạo brief và ghim manifest C3. Ở màn hình **Chiến dịch → Điều hành chiến dịch**, chọn campaign, mở phần lập kế hoạch, chọn một hoặc hai manifest và kiểm tra hạn thực hiện, kênh, ngân sách mô phỏng trước khi lưu. Với hai manifest, workflow, brief và mục đích bàn giao khác nhau nhưng sản phẩm, thị trường, điều kiện thương mại và hành động người mua phải nhất quán.

1. Người được phân quyền duyệt digest của revision đang chờ. Phần lịch hiển thị mốc, người phụ trách và tiêu chí bàn giao. Mỗi gói việc có mã định danh gắn với tenant, client, brand và campaign.
2. Xếp WF-03 hoặc WF-13 từ kế hoạch đã duyệt. Worker nội bộ dùng release đã kích hoạt cho chiến dịch. Biên nhận ghi lại mỗi lần thử, token và lỗi. Chiến lược, đo lường, landing và SEO có thể lấy từ bản Studio đã lưu. Nội dung social, quảng cáo, brief sáng tạo và lịch nằm ở dạng nháp tổng hợp theo quy tắc.
3. Mở **Duyệt nội dung → Soạn và bàn giao cho khách** để đối chiếu nguồn, sửa từng trường, gửi QA độc lập và chụp snapshot. Studio hiển thị nguyên bản, nội dung đề xuất, căn cứ và lựa chọn ngành. Người biên tập có thể nhận, sửa hoặc bỏ qua gợi ý. Khi lưu, QA và chữ ký áp dụng cho revision mới.
4. Lên lịch từ bản đã duyệt. Người thứ hai cấp phép với trần chi phí của chiến dịch. Chạy mô phỏng khi đến hạn. Tải lại trang để thấy biên nhận, lần thử và trạng thái vừa ghi.
5. Ghi phiên, yêu cầu báo giá, mục đích liên hệ, số lượng theo đơn vị, thời điểm và địa bàn giao. Sales có thể yêu cầu bổ sung, ghi lý do nhận hoặc loại, rồi ghi báo giá, đơn, hủy, hoàn tiền hoặc đính chính. Xem lại doanh thu có và thiếu nguồn trước khi đề xuất việc tối ưu. Một người khác duyệt đề xuất dựa trên đúng digest báo cáo. Mọi giá trị của phễu là dữ liệu mô phỏng.

## Chạy trên máy khác

Dùng các bước cài Docker, tạo bí mật local và khởi tạo DB trong HANDOFF. PostgreSQL dùng core v25, Business v3, C3 v4. Bản tăng trưởng này dùng các bảng và quyền hiện có. Dùng môi trường có worker/model loopback và registry đã duyệt để chạy hành trình thực. SQLite hỗ trợ phép thử planner, ledger và API. Quy trình chạy Docker lặp lại được đặt trong job `workforce-model` và lưu điều kiện model cùng kết quả. [Workflow](../../../.github/workflows/ci.yml)

Từ gốc repository với dependencies phát triển đã cài, chạy `python -m pytest -q tests/test_studio_journeys.py tests/test_campaign_planner.py`. Chạy lại hành trình riêng trong DB PostgreSQL dùng một lần tên `amc_test…` đã migrate, với DSN owner/runtime, nguồn model loopback và đường dẫn GGUF đã khớp digest qua `python tests/campaign_planner_journey.py evidence-new`. Tạo thư mục đầu ra mới cho mỗi lần. Đặt `AMC_ENGINE_EVIDENCE=evidence-new/screens` và cài Playwright Chromium để chụp giao diện cả ba viewport và hai theme. Các lệnh, biến và cổng động cụ thể nằm trong job CI. Local không cần thông tin tài khoản khách thật.

Hợp đồng lệnh, mẫu RFQ, phân biệt chi phí mô phỏng và chi phí sản xuất, cách ghi công và điều kiện nghiệm thu bởi người được mời nằm trong [bàn giao vận hành sandbox](../../campaign-engine/SANDBOX-OPERATIONS.md).

## Khôi phục

Trước khi đổi image, dừng nhận công việc, chờ worker đang chạy hoàn tất và tạo backup nhất quán. Với rollback engine trong cùng C3 v4, dừng API/worker engine trước khi chạy lại image nền đã nghiệm thu. Giữ nguyên bảng lệnh, snapshot và quyết định đã ký. Image nền đọc dữ liệu đã hỗ trợ trước đó. Khi muốn tiếp tục campaign engine, đưa lại image có đúng registry, rồi đọc trạng thái theo campaign và gửi lại đúng request ID của lệnh chưa nhận phản hồi. Rollback qua biên C3 v4 cần theo hướng dẫn cutover riêng ở HANDOFF.

## Phạm vi nghiệm thu

Điều kiện, manifest đầu vào và hợp đồng giao tới worker được mô tả trong [bàn giao Planner và Workforce](../../campaign-engine/PLANNER.md). Dùng [sổ đầu ra và chi phí sáu đợt chạy](workforce/RESULTS.md) để đối chiếu câu của model với từng trường đã ký. Đối với artifact CI đã giải nén, chạy `python tests/check_engine_receipts.py campaign-engine-receipts --checkout SHA_DA_TEST --screens campaign-engine-receipts/screens`. Bỏ tùy chọn screens khi kiểm tra job chỉ chạy trên head.

Dùng [kết quả phiên trình duyệt](ui/sessions.json) để nối ảnh với đúng campaign và run ID. Thời gian từ khi chọn campaign đến khi vẽ xong trong phiên local là 188 ms, 250 ms và 234 ms ở ba kích thước dưới đây. Đây là ba lần quan sát trên máy phát triển.

| Màn hình Chromium | Điều hành | Đối soát RFQ | So sánh sửa ở Studio |
| --- | --- | --- | --- |
| Desktop 1280 × 850 | [Sáng](ui/workspace-1280.png) · [Tối](ui/workspace-1280-dark.png) | [Sáng](ui/funnel-1280.png) · [Tối](ui/funnel-1280-dark.png) | [Sáng](ui/editor-1280.png) · [Tối](ui/editor-1280-dark.png) |
| Tablet 820 × 1180 | [Sáng](ui/workspace-820.png) · [Tối](ui/workspace-820-dark.png) | [Sáng](ui/funnel-820.png) · [Tối](ui/funnel-820-dark.png) | [Sáng](ui/editor-820.png) · [Tối](ui/editor-820-dark.png) |
| Mobile 390 × 844 | [Sáng](ui/workspace-390.png) · [Tối](ui/workspace-390-dark.png) | [Sáng](ui/funnel-390.png) · [Tối](ui/funnel-390-dark.png) | [Sáng](ui/editor-390.png) · [Tối](ui/editor-390-dark.png) |

Để phản biện bản tăng trưởng này, hãy đối chiếu digest và nguồn của một bản giao sau khi biên tập, gửi lại một lệnh sau khi mất phản hồi, kiểm tra lại một đơn từ kế hoạch đã thay thế và xác nhận mẫu số chi phí khi chỉ có khách hàng tổng hợp. Các phép thử cho kỹ thuật viên và phiếu chấm nghiệp vụ có tiêu chí khác nhau. [Giao thức pilot](PILOT.md)

19 năng lực Marketing và 24 workflow vẫn là phạm vi V1. Hai workflow có biên nhận model trong hành trình này là WF-03 và WF-13. AIRC-500 có cơ chế kiểm định riêng. Các phép đo của chuyên viên, chi phí trên bản được doanh nghiệp chấp nhận và mức sẵn sàng thương mại còn mở. [Giao thức pilot](PILOT.md) · [Quyết định nghiên cứu và bước sản phẩm kế tiếp](../../research/CAMPAIGN-ENGINE.md)
