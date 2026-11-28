# Nghiệm thu Studio cho hướng dẫn trên trang sản phẩm

Người nhận Content mở phiếu Strategy đã ký rồi chọn **Bắt đầu soạn hướng dẫn**. Sau khi worker hoàn thành, người nhận mở kết quả từ phiếu, danh sách Workforce hoặc bản làm việc trong mục Phê duyệt. Hai phiên đăng nhập trong ca dương thuộc người nhận Content và người đã ký bàn giao Strategy. Người thứ hai độc lập với tác giả của guide và có thẩm quyền QA trong phạm vi này.

| Công việc | Kết quả quan sát |
|---|---|
| Soạn và xem trước | Hai bước dùng Index Stand, điều kiện dùng thẻ khô và CTA tải catalogue xuất hiện trong thành phần xem trước. Nguồn P1 và nguyên văn công bố nằm trong phần **Đối chiếu nguồn của hướng dẫn**. |
| Biên tập | Editor nhập một câu ngoài nguồn, Studio báo tiêu đề chưa khớp và khóa lưu. Sau đó editor nhập nguyên văn bước đầu làm tiêu đề, chuyển phần hướng dẫn sang checklist và lưu revision 2. Backend cũng từ chối tiêu đề ngoài nguồn. [Ảnh sau khi lưu](screens/editor-saved.png) |
| QA | Người nhận gửi revision đã lưu. Reviewer kiểm tra bước, điều kiện và CTA rồi ký đúng revision và SHA-256. Cùng tài liệu có biên nhận độc lập lưu trong Knowledge. Studio hiển thị quyết định và ID biên nhận. [Ảnh QA](screens/independent-qa.png) · [Run, document, revision, digest và receipt](screens/browser.json) |
| Thu hồi quyền | Sau khi chủ nguồn thu hồi mandate, người duyệt chọn kiểm tra lại phiên bản. Studio thay bản xem trước bằng thông báo cần tải lại và xác minh quyền. |
| Thiếu căn cứ | Ca thứ hai dùng brief tiếng Việt và nguồn chỉ mô tả hai ô của bảng bàn giao. Nút bắt đầu trả hướng dẫn bổ sung nguồn có các bước thao tác; không có guide hoặc worker ở ca này. [Ảnh hold trên điện thoại](screens/source-hold-mobile.png) |

## Kết quả Chromium

Ảnh bên dưới lấy ở kích thước viewport thực. Nút bắt đầu, thao tác lưu và ký QA đã được kích hoạt bằng bàn phím. Trong trình biên tập, Tab từ tiêu đề chuyển đến kiểu danh sách. Ở cả sáu tổ hợp, trang không tràn ngang và phép đo tương phản của repo không ghi nhận phần tử bị lỗi trong Studio. Số liệu độ trễ từ chọn bản làm việc đến khi thấy bản preview là phép đo cục bộ trên fixture tổng hợp. [Số liệu theo kích thước và theme](screens/browser.json)

| Viewport | Sáng | Tối |
|---|---|---|
| Desktop 1280 × 850 | [Desktop sáng](screens/guide-1280-light.png) | [Desktop tối](screens/guide-1280-dark.png) |
| Tablet 820 × 1180 | [Tablet sáng](screens/guide-820-light.png) | [Tablet tối](screens/guide-820-dark.png) |
| Mobile 390 × 844 | [Mobile sáng](screens/guide-390-light.png) | [Mobile tối](screens/guide-390-dark.png) |

Chạy `python -m pytest -q tests/test_product_guide_studio.py tests/browser_product_guide.py --junitxml=browser.xml` với PostgreSQL test đã cấu hình theo workflow của repo. Đặt `AMC_PRODUCT_GUIDE_SCREENS` tới thư mục ảnh. `AMC_BROWSER_EXECUTABLE` có thể trỏ tới Chrome/Chromium đã cài. Ca kiểm thử dùng API HTTP thật, đăng nhập tách biệt và controlled worker replies. [JUnit cục bộ](screens/junit.xml) · [Kịch bản browser](../../../tests/browser_product_guide.py) · [Kiểm thử quyền và revision](../../../tests/test_product_guide_studio.py)

Phạm vi biên tập v1 gồm thay tiêu đề bằng dòng nguồn được phép, chọn cách trình bày và kiểm tra preview. Trình duyệt hiển thị chuỗi bằng text node. Các bước, giới hạn và CTA đi theo nguồn đã ký. Chưa đo thời gian làm việc của người dùng thực, hiệu quả Marketing hoặc doanh thu. Fixture D/A/C vẫn độc lập với vòng nghiệm thu này.
