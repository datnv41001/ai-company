# R70-02 · Đối chiếu phiếu Strategy khi duyệt Content

**Đã tái hiện và sửa trong luồng QA nội bộ của WF-06/1.** Người ký thấy phiếu Strategy đã được phép chuyển tiếp, nguồn P1 và bản hướng dẫn đang chờ duyệt. Mỗi lần quyết định, người ký đối chiếu từng nghĩa vụ và xác định các bước phải làm theo thứ tự, có thể làm độc lập hoặc còn cần làm rõ. Content editor nhận được mục cụ thể cần sửa khi QA trả lại. Kết quả thử đến từ tài khoản và dữ liệu tổng hợp trong PostgreSQL tạm. [Kết quả API](api-junit.xml) · [Kết quả Chromium](browser-junit.xml)

## Bằng chứng trước và sau

| Ca | Kết quả quan sát |
| --- | --- |
| Main sau #70, commit `3d56073fafeb9d5bd5f39843fc74e11bc378fdab`, tree `85a92d483ce84c72b243b1f49b7579f3ea737258` | Phiếu yêu cầu đánh số thứ tự mở túi rồi đưa thẻ vào. Màn hình QA thiếu yêu cầu này. API vẫn nhận checklist với HTTP 200 và tạo receipt `95d0632b-32ab-42f9-bc3c-2593878925e9` ở revision 2. Assertion mong đợi 409 đã đỏ. [Readback](historical-red.json) · [JUnit](historical-red-junit.xml) |
| GQ-VI-01, ba bước phụ thuộc và có yêu cầu đánh số | Khi người duyệt xác định thứ tự bắt buộc, API chặn checklist bằng 409. Người duyệt ghi yêu cầu chưa đáp ứng và tiêu chí cần làm rõ rồi trả về. Editor đổi sang bước đánh số và gửi revision 3. Quyết định cũ nhận 412. QA duyệt đúng revision mới cùng ba bước và điều kiện dùng thẻ giấy khô. [Phiếu trả lại và phiếu duyệt](GQ-VI-01.json) |
| GQ-EN-01, hai thao tác đối chiếu độc lập | Phiếu cho phép kiểm tra nhãn hoặc mẫu vải trước. Checklist giữ hai dòng riêng cùng điều kiện chỉ dùng danh mục huấn luyện. Khi người duyệt xác nhận từng mục và tính độc lập, API nhận quyết định ở revision 2. [Phiếu duyệt](GQ-EN-01.json) |
| Tương thích lịch sử | Test ghi đúng dạng receipt cũ vào PostgreSQL tổng hợp, đọc lại và replay cùng quyết định. ID, digest và toàn bộ payload trước/sau giống nhau. Studio ghi rõ quyết định lịch sử chưa có kết quả cho từng nghĩa vụ. [Kiểm thử replay](../../../../tests/test_product_guide_order_qa.py) |

## Người duyệt đối chiếu những gì

Studio lấy một danh sách trường công khai xác định trong phiếu đã ký. Danh sách gồm mục đích của brief và tài sản, người đọc, vị trí, hành động của người mua, CTA, cách diễn đạt, từng yêu cầu, từng mục loại trừ, từng tiêu chí nghiệm thu, giới hạn nhận định, trạng thái và quyền thực hiện phép đo. Các mục này chỉ hiển thị trong phần đối chiếu nội bộ. Bản preview tiếp tục giữ hợp đồng nội dung WF-06/1. [Chiếu dữ liệu từ nguồn đã ký](../../../../app/product_guide_studio.py) · [Form quyết định](../../../../app/static/product-guide.js)

Mỗi mục nhận một trong ba kết luận của người duyệt: đáp ứng, chưa đáp ứng hoặc cần bổ sung thông tin. Các lựa chọn ban đầu đều trống. API so digest của phiếu, tập ID chính xác, revision, content digest, manifest và quyền hiện tại. Chỉ ký duyệt khi toàn bộ nghĩa vụ đã được người kiểm tra xác nhận và cách trình bày tương thích với tính chất thứ tự đã ghi. Trả lại lưu kết quả từng mục trong receipt gắn với bản đang xét. Chạy lại cùng quyết định dùng receipt đã có. Bản sửa cần được đối chiếu lại.

**Giới hạn của bằng chứng.** Yêu cầu nguồn có thể là văn bản tự do. Người ký vẫn chịu trách nhiệm nếu khai sai rằng các bước độc lập hoặc xác nhận sai một mục. Việc nhận diện mọi quan hệ phụ thuộc bằng máy sẽ cần thiết kế và xét duyệt riêng đối với contract có metadata thứ tự. Kết quả thử xác minh quyết định từ người đúng vai trò, các điều kiện hệ thống kiểm được và receipt đúng phiên bản. Tính dễ hiểu đối với người dùng thực, thời gian tiết kiệm và kết quả kinh doanh chờ pilot.

## Chromium

Chromium 158.0.8127.88 chạy bằng trình duyệt thật và các phiên độc lập cho người biên tập/người ký. Kịch bản dùng bàn phím để di chuyển giữa các nghĩa vụ, trả checklist sai, sửa và ký bản đánh số mới. Mỗi cỡ màn hình kiểm tra chiều rộng, chữ/điều khiển trong vùng đối chiếu và màu hệ thống. Thời gian mở tài sản tới preview ở máy thử là 359–906 ms. Tỷ lệ tương phản nhỏ nhất trong các mẫu đã đo là 6,113:1. Đây là số đo phát triển trên một máy. [Số đo chi tiết và receipt](browser.json) · [Ảnh sau quyết định](numbered-qa-receipt.png) · [Kết quả cả kịch bản Studio cũ và mới](browser-regression-junit.xml)

| Màn hình | Sáng | Tối |
| --- | --- | --- |
| 1280 × 850 | [Desktop](order-1280-light.png) | [Desktop](order-1280-dark.png) |
| 820 × 1180 | [Tablet](order-820-light.png) | [Tablet](order-820-dark.png) |
| 390 × 844 | [Mobile](order-390-light.png) | [Mobile](order-390-dark.png) |

## Chạy lại trên máy khác

Dùng PostgreSQL kiểm thử theo [HANDOFF](../../../../HANDOFF.md) và biến môi trường kiểm thử của job API. `AMC_GUIDE_QUAL_RESULTS` và `AMC_GUIDE_ORDER_SCREENS` nhận đường dẫn thư mục xuất kết quả. Các test tự tạo tenant tổng hợp và đi qua API, quyền của từng người dùng, worker với controlled reply và transaction thật. Đặt `AMC_BROWSER_EXECUTABLE` khi dùng Chromium có sẵn trên máy. Các lệnh bên dưới chỉ chạy các phép kiểm có controlled reply.

```shell
python -m pytest -q tests/test_product_guide_order_qa.py tests/test_product_guide_studio.py tests/test_product_guide_production.py --junitxml=guide-api.xml
python -m pytest -q tests/browser_product_guide_order.py tests/browser_product_guide.py --junitxml=guide-browser.xml
```

Để tái hiện RED trên phiên bản lịch sử, tạo checkout riêng tại đúng commit nêu trên. Đặt [phép thử hồi quy lịch sử](reproduce_r70.py) vào checkout đó, cấu hình PostgreSQL test, đặt `AMC_RED_FILE` thành đường dẫn tệp JSON trong một thư mục đã có rồi chạy `python -m pytest -q reproduce_r70.py`. Một assertion thất bại tại HTTP 200 là kết quả quan sát được ở phiên bản này. Các tệp JUnit bàn giao đã bỏ tên máy. JUnit RED tóm lược lỗi để tránh đường dẫn cá nhân, nguyên nhân và readback nằm trong tệp JSON.

## Chuyển phiên bản và rollback

Trước khi mở lại QA guide trong môi trường nội bộ, tạm ngừng ghi quyết định WF-06, đợi các request đang chạy hoàn tất và thay **tất cả** API writer cùng frontend. Binary #70 vẫn có thể tạo receipt dạng cũ nếu tiếp tục nhận lưu lượng. Binary cũ cũng có thể từ chối đọc receipt dạng mới do đối chiếu toàn bộ payload. Khi rollback, tạm dừng quyết định guide và giữ ứng dụng đọc tương thích để tra cứu receipt mới. Bảo toàn lịch sử dữ liệu, manifest, attempt và ledger. Thử lại một approval và một return trên fixture cô lập trước khi mở lại. Phần này chưa chứng nhận chạy đồng thời hai phiên bản writer.

**Đề nghị Independent Reviewer kiểm tra** trường hợp phiếu tiếng Việt bắt buộc đánh số, trình tự reviewer ghi, receipt từ chối và revision sửa. Sau đó đối chiếu phiếu tiếng Anh cho phép làm theo bất kỳ thứ tự nào và xem kết quả checklist. Hai ca dùng cùng release sản xuất guide và cùng cổng quyết định.
