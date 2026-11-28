# Hướng dẫn sử dụng trên trang sản phẩm · WF-06/1

Người nhận work order trong một workspace in-house có thể tạo bản hướng dẫn nội bộ, xem trước trong Studio, sửa tiêu đề và cách trình bày, rồi chuyển cho người duyệt Content. Reviewer kiểm cùng các bước, điều kiện sử dụng và CTA đã được Strategy cho phép. [Chứng nhận main #69](MAIN-69.md) · [Contract trong catalog](../../../catalog/product-use-guide-v1.json)

## Nguồn nào đủ để bắt đầu

Chủ nguồn dùng quy trình Business Knowledge hiện hữu để tạo và duyệt một revision loại `source`. Trên đúng entry của assertion loại `description`, khai báo `guide_procedure` có version `amc.product-guide-source/1` và 1–8 bước. Mỗi bước là nguyên văn một phần của wording đã duyệt, theo đúng thứ tự. Trường `excerpt` phải chứa trọn wording và các qualifier. Ví dụ một entry có hai bước như sau.

```json
{
  "version": "amc.product-guide-source/1",
  "steps": [
    "Place the batch card in the front slot.",
    "Insert the reference card in the rear slot."
  ]
}
```

Bản thử có qualifier **“Use dry cards only.”** Phần `guide_procedure` chỉ được dùng khi Strategy ký chính wording này cho đúng placement. Thêm một bước vào đề xuất của editor, cấp một source ID từ frontend hay có một quan sát của người mua đều chưa đủ căn cứ. Với brief tiếng Việt chỉ có mô tả hai ô trên bảng bàn giao, Studio yêu cầu bổ sung nguồn. Hệ thống giữ nguyên số task, manifest, run và bút toán. [Receipt hold](hold-vi.json) · [Định nghĩa Source](../../../app/knowledge_contracts.py)

## Vận hành trong môi trường phát triển

1. Dùng cấu hình PostgreSQL dev của repo. Chạy migration bình thường trước khi khởi động API/dispatcher/worker cùng bản build. Vẫn dùng core v26, C3 v5 và các bảng hiện hữu. Publisher cài các kiểm tra dành riêng cho guide; API xác minh chúng khi khởi động. [Migration](../../../migrations/product_guide.sql)
2. Bằng danh tính migration trong môi trường đã cấu hình, chạy `python migrations/apply.py --publish-registry catalog/product-use-guide-v1.json`. Admin kích hoạt release cho đúng campaign in-house qua `PUT /api/tenants/{tenant_id}/workforce/registry/{campaign_id}` với `{"workflow":"WF-06/product-use-guide@1","action":"activate","skills":["director","content"]}`. Pool phải được cấp quyền ở campaign và cấu hình ngân sách qua cơ chế hiện hành. Start guide đặt trần run 0 micro-USD; một cấu hình có phí dương phải tuân trần này.
3. Tạo Strategy commission có placement web hoặc owned product page, thực hiện WF-03, lưu Studio, ký QA và chọn `web_use_guide` trong Strategy Handoff /2. Chỉ người nhận được chỉ định mới thấy hành động bắt đầu. API chỉ nhận `receipt_id` tại `POST /api/tenants/{tenant_id}/deliverables/{did}/studio/content-handoff/product-guide`. Ký Strategy tự nó không tạo task. Một lần nhấn, hai request đồng thời và gửi lại sau khi mất phản hồi cùng trỏ tới một task cho receipt, recipient và version đó.
4. Trong Studio, mở bản guide từ run đã hoàn thành. So các bước và CTA trong preview với nội dung được phép dùng. Lưu revision rồi gửi duyệt. Người ký handoff có quyền hiện tại và độc lập với người soạn guide mới được ký Content QA. Mỗi lần lưu lại yêu cầu đối chiếu revision/digest mới. Đường share/publish vẫn đóng.
5. Khi rollback, dừng admission mới ở campaign, xử lý các lease hiện hữu, dùng thao tác registry `disable` hoặc `revoke` phù hợp và giữ lịch sử trong DB. Một API cũ không có marker phiên bản sẽ bị RLS ẩn bốn loại row của guide. Giữ migration bảo vệ dữ liệu và registry release lịch sử khi hạ phiên bản ứng dụng. [Phép thử rollback](../../../tests/test_product_guide_rollback.py)

## Bằng chứng để đối chiếu

- [Đọc nguyên bản hướng dẫn trước và sau khi sửa](GUIDE.md) · [Work order và raw reply](guide-before-edit.json) · [Strategy binding và Content QA](guide-approved.json). Hai bản văn đã được tính lại digest từ chính title và body. Các ID thuộc cùng phiên chạy API. [Ảnh và nghiệm thu Studio](STUDIO.md) dùng fixture độc lập và có receipt riêng.
- [Ledger theo từng attempt](ledger.json) ghi cả lần Content trả lựa chọn ngoài contract và lần retry thành công. Đầu ra của Director là kế hoạch xác định, không gọi model. [Nguồn bị rút trước dispatch](fence-queued.json) · [Hạ quyền sau khi giao việc](fence-offered.json) · [Rút mandate sau khi worker nhận](fence-sent.json) · [Strategy đổi sau khi worker trả kết quả](fence-reported.json).
- [Quyền quan sát trước và sau khi thu hồi trên Strategy](dispatcher-authority.json) · [Kiểm tra và rollback PostgreSQL](POSTGRESQL.md) · [JUnit nhóm guide](junit.xml). Các lần chạy phát triển đã phát hiện lỗi fixture email, chờ retry và tuần tự hóa số tiền. Ở vòng kiểm giao diện, một select thiếu tên truy cập rõ ràng. Các phép kiểm sau khi sửa giữ nguyên yêu cầu ban đầu.
- Để tái tạo trên database riêng, đặt các biến test PostgreSQL theo `.github/workflows/ci.yml`, `AMC_TEST_PG=1`, `AMC_PRODUCT_GUIDE_EVIDENCE` tới thư mục receipt và `AMC_PRODUCT_GUIDE_SCREENS` tới thư mục ảnh. Chạy `python -m pytest -q -k product_guide --junitxml=guide.xml`, sau đó `python -m pytest -q tests/browser_product_guide.py --junitxml=browser.xml`. Full regression dùng `python -m pytest -q`. Workflow chuẩn đưa receipt và ảnh từng revision vào artifact `product-guide-head` hoặc `product-guide-integration`. Lấy PR, head, trial, tree, CI và manifest theo liên kết cố định trong phần mô tả draft.

## Quyết định kiến trúc và quyền

Trigger nghiệp vụ là Strategy đã được duyệt nên release nằm dưới **WF-06 Campaign Factory**. WF-03 vẫn tạo chiến lược, WF-08 tạo storyboard và WF-13 phục vụ landing/SEO. Số workflow mẹ, vai trò logic và module vẫn là 24, 37 và 49. Phạm vi của WF-06/1 là một guide nội bộ. Agency, terms panel, thẻ tại quầy và Content Factory tổng quát vẫn ở ngoài contract.

- **Admission.** Server đọc lại người nhận, quyền reviewer, original QA, scope, Strategy revision/digest, nguồn, manifest và release. Một transaction ghi brief nội bộ, snapshot, run và audit. API task/manifest/run thông thường từ chối yêu cầu tạo guide trực tiếp. [Mã admission](../../../app/product_guide_admission.py)
- **Nguồn và worker.** Dữ liệu gửi Content thuộc phiên bản dành cho recipient. Handle cục bộ `P1` trỏ tới declaration được phép dùng. Role Content chọn tiêu đề/bố cục trong contract. Graph giữ nút Director để xác lập assignment có phiên bản; nút này chạy bằng adapter xác định, ghi 0 token. Câu trả lời Content trong phép nghiệm thu do fixture cung cấp qua mailbox, với retry thực của runtime. [Adapter và phép ghép bản](../../../app/product_guide_runtime.py)
- **Thu hồi.** Product Owner đã duyệt phép kiểm PostgreSQL nội bộ riêng cho WF-06. Dispatcher và worker giữ nguyên giới hạn đọc Knowledge. Các hàm đang sở hữu quyền cấp lease và chấp nhận kết quả đối chiếu các pin của chính run. Việc thu hồi có thể chặn cấp lease, chặn lấy việc hoặc loại kết quả đã gửi. Số token đã sử dụng vẫn được đối soát. [Bốn thời điểm kiểm thử](../../../tests/test_product_guide_fence.py)
- **Content QA.** Raw reply, checkpoint, edition và preview là các đối tượng khác nhau. QA ký đúng digest và revision của edition được lắp ráp. Tài liệu lịch sử trong run không cấp quyền đọc hoặc tái duyệt khi Strategy mất hiệu lực. [Studio](../../../app/product_guide_studio.py)

## Căn cứ về chất lượng Marketing

Hướng dẫn biên tập của Google khuyến khích viết các thao tác theo trình tự người đọc cần, có ngữ cảnh sử dụng và mỗi bước có một hành động rõ. WF-06/1 cho phép chuyên gia nguồn xác lập thứ tự đó và editor chọn cách trình bày. Việc một người dùng thực hiện đúng thao tác từ guide, thời gian tiết kiệm và tỷ lệ chuyển đổi vẫn chưa được đo. Phép thử tiếp theo cần người thực hành đọc guide, làm hai bước trên đúng sản phẩm, nhận biết qualifier và tìm CTA mà không cần người soạn hướng dẫn. [Google developer documentation style guide, Procedures](https://developers.google.com/style/procedures)

**Câu hỏi cho Independent Reviewer.** Khi quyền bị thu hồi sau khi worker đã tốn token, kết quả có bị loại trong khi usage vẫn còn không? Biên tập có giữ nguyên đúng cả hai thao tác và qualifier khi đọc trên màn hình nhỏ không? Chỉ tài sản nội bộ và quyết định QA đã có bằng chứng. Practitioner acceptance, publication và business outcome chưa đạt. RS-01/02 giữ kết quả gốc. Cohort D/A/C 12 brief/72 lượt vẫn PROPOSED; phải khóa quy tắc chấm hold, incomplete và thiếu QA trước khi chạy. AMC-R68-01 vẫn OPEN P3.
