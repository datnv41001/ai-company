# R70-01 · Ai quyết định hình thức của Product Guide?

**Finding còn mở về giá trị model.** Bản phát hành WF-06/1 chỉ cho Content chọn một trong hai kiểu tiêu đề và một trong hai kiểu trình bày. Ở hai tình huống đã dựng, tổ hợp mặc định đáp ứng cả hai quy tắc định dạng được kiểm. Một lựa chọn hợp lệ theo schema vẫn vi phạm yêu cầu đánh số của brief tiếng Việt. Hai ca này chưa cho biết người đọc hiểu nhanh hơn với cách nào. [Contract và composer](../../../../app/product_guide_runtime.py) · [Các trang đã render và dấu vết từng trường](results.json)

## Thiết kế đối chứng

Mỗi ca có đúng một bản chiếu dữ liệu tổng hợp, một brief và một nguồn P1. Hàm `brief_release` tạo CTA theo locale. Hàm `compose` và `preview` thực của WF-06/1 tạo cả sáu bản, không qua model server. Đầu vào theo hình dạng dữ liệu mà người nhận được phép thấy. Phép so sánh cục bộ này không phát hành receipt cấp quyền. Ngữ cảnh chung là bàn giao ca tại quầy mẫu. Hai case cố ý khác loại thao tác. Vì ngôn ngữ và loại thao tác cùng thay đổi, chỉ so sánh các nhánh *trong cùng một case*. [Fixture đầy đủ](cases.json) · [Mã tái hiện](../../../../tests/evaluation/compare_guide_selections.py)

| Nhánh | Lựa chọn trước khi render | Câu hỏi có thể trả lời |
| --- | --- | --- |
| D · mặc định nghiên cứu | Luôn dùng tiêu đề sản phẩm và danh sách được đánh số | Phương án đơn giản này đáp ứng những nghĩa vụ quan sát được nào? |
| E · đại diện lựa chọn biên tập | Tác giả fixture đặt tiêu đề theo tình huống; chọn đánh số với thao tác tuần tự và checkbox với hai phép đối chiếu độc lập | Khi lựa chọn đó được đưa vào composer, phần nào trên trang thay đổi? |
| M · câu trả lời có kiểm soát | Đưa JSON hai trường qua chính hàm validate của Content. Cả hai câu trả lời chọn tiêu đề theo tình huống và checkbox | Câu trả lời hợp đồng có thể làm hỏng nghĩa vụ nào? Hai cách chọn giống hệt có sinh ra cùng trang? |

Ba nhánh cùng dùng bốn tổ hợp có sẵn. Studio còn cho biên tập viên chọn một tiêu đề lấy nguyên từ câu hướng dẫn được duyệt. Chức năng đó được loại khỏi phép so sánh này để giữ bằng nhau số lựa chọn. Không có practitioner, người dùng cuối hay model nào tham gia chọn trong sáu bản này.

| Case | D | E | M | Đối chiếu |
| --- | --- | --- | --- | --- |
| VI · Lắp thẻ vào túi | 3 số thứ tự | 3 số thứ tự | 3 checkbox | Brief yêu cầu thấy số khi mở nắp, đưa thẻ vào rồi gập nắp. M giữ đúng thứ tự câu và điều kiện thẻ khô nhưng thiếu dấu hiệu đánh số bắt buộc. |
| EN · Đối chiếu bộ mẫu huấn luyện | 2 số thứ tự | 2 checkbox | 2 checkbox | Hai đối chiếu trên hai thẻ khác nhau đều đứng riêng dòng. Brief cho phép bắt đầu ở thẻ nào cũng được. E và M cho cùng title/body và SHA-256. Chưa đo người đọc có suy diễn nhầm rằng số thứ tự là bắt buộc. |

**Phần giá trị đã quan sát.** Cả sáu bản có cùng các bước nguyên văn, giới hạn, audience và CTA theo brief trong từng ca. Composer quyết định nội dung xuất hiện và nguồn cho từng trường. Selector chỉ thay tiêu đề và ký hiệu đầu dòng. Quy tắc định dạng trong bài thử xác minh yêu cầu được viết riêng cho hai case; các điều kiện kinh doanh, sự dễ hiểu và phù hợp với đối tượng vẫn cần người kiểm. Editor quyết định trình bày và sửa bản nháp. Người QA độc lập đối chiếu Work Order, P1 và chính revision được nộp. Khi hai vai trò chọn sai như nhau, SHA giống nhau chỉ chứng minh nội dung giống nhau.

**Chi phí và độ trễ.** Việc chạy script chỉ gọi các hàm Python cục bộ. Không có invocation, token, latency hay hóa đơn inference để suy ra chi phí một guide. Một lượt qua model server trong tương lai sẽ thêm thời gian chờ worker, xử lý request và thời gian retry nếu có. Thời gian biên tập và QA có thể tăng hoặc giảm. Chỉ so sau khi có phép chạy được duyệt và receipt thật theo từng arm, gồm model/version, phiên bản release, bytes đầu vào, token, thời gian vào queue, thời gian thực thi, số attempt, ledger settlement và cơ sở tính chi phí. Khi chưa đo, ghi `null`. [Đề xuất pilot](PRACTITIONER.md)

**Quyết định.** Có căn cứ dùng D làm đối chứng rẻ cho nghiên cứu. Chưa có căn cứ thay selector của release /1, quy kết lợi ích cho AI hoặc kết luận mặc định đủ cho mọi brief. Để tiếp tục, cần brief mới ở *cả hai* ngôn ngữ cho *cả hai* loại thao tác, thứ tự nhánh được cân bằng, dữ liệu practitioner độc lập và nếu cần so sánh model thật thì phải có ngân sách/phạm vi đã duyệt.

## Tái hiện từ thư mục repository

```sh
python tests/evaluation/compare_guide_selections.py --output guide-comparison.local.json
python -m pytest -q tests/test_guide_selection_comparison.py
```

So sánh kết quả JSON với `results.json`. Từng case có SHA-256 của đầu vào và bản chiếu, cùng SHA-256 của title/body trên từng nhánh. Digest dùng JSON UTF-8, sắp khóa và bỏ khoảng trắng phân cách. Mọi bản render vẫn ở trạng thái chờ editor nộp. [Kiểm thử tái hiện và kiểm tra hợp đồng](../../../../tests/test_guide_selection_comparison.py)
