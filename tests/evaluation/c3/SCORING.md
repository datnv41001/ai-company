# Quy trình đánh giá hai bản WF-03 và WF-13

Dùng năm ca tổng hợp trong `cases.json`. Mỗi ca có mục tiêu bằng tiếng Việt, hai nguồn, phạm vi thị trường, KPI, CTA mong muốn, giả thuyết, dữ liệu thiếu và một ví dụ về tuyên bố không có căn cứ. Ví dụ tiêu cực chỉ dùng chấm bài. Các điều kiện thương mại có hiệu lực cho phạm vi và số lượng của ca. Bản v2 ghi rõ thuế cho bốn giá có số tiền. Mười lượt ban đầu trên v1 là thử dây chuyền. Chỉ hai nhánh chạy sau khi khóa v2 được đưa vào bảng so sánh.

**Đơn vị chấm.** Một bản giao trong DB cho một mục tiêu và workflow. Tác vụ thiếu bản giao nhận điểm 0. Một lượt cho mỗi ô trong thiết kế 5 × 2 × 2 chưa đo được biến thiên giữa nhiều lần sinh. Giữ cùng weights, engine, seed, ngân sách, mức song song và bộ dữ kiện. Công bố phần dữ liệu mỗi adapter nhìn thấy, các lượt thử lại, token, thời gian và chi phí nhà cung cấp. Nếu điều kiện khác, ghi chênh lệch trước khi diễn giải. Giá điện và công lao động chưa được đo.

**Hai thước đo ban đầu.** Thành công kỹ thuật ở lần đầu nghĩa là tạo được bản giao và mọi lượt thực thi đều có outcome `ok`. Chấp nhận về nghiệp vụ ở lần đầu nghĩa là bản giao chưa biên tập đạt cả sáu tiêu chí dưới đây. Ca thiếu giá, chứng cứ, địa bàn hoặc điều kiện không được gán kết quả thay cho lời xác nhận từ con người.

| Tiêu chí | Điều kiện đạt một điểm |
| --- | --- |
| Dữ kiện sản phẩm | Nhận ra đúng mặt hàng, đặc điểm phân biệt và không thêm đặc điểm trái bộ nguồn. |
| Phạm vi và điều kiện | Nội dung thực tế giữ đúng nhóm khách, địa bàn, đơn vị, thuế, ngưỡng và ngoại lệ nếu nêu giá. Phần thuyết minh đi kèm không cứu một tuyên bố mâu thuẫn ngay ở headline hoặc CTA. |
| Truy được nguồn | Người đọc xác định được căn cứ cho dữ kiện được dùng, phân biệt được giả thuyết và dữ liệu còn thiếu. Kiểm cả nội dung khách nhận lẫn bản tham chiếu đã được phép dùng. |
| Hữu ích với người mua | Có một hành động cụ thể gắn với việc người mua cần làm. Việc chép lại tên thương hiệu, KPI hay toàn bộ bảng dữ kiện chỉ là ngữ cảnh. |
| Chuyên môn Marketing | WF-03 đưa ra lựa chọn có lý do cho nhóm khách và cách đo đúng sự kiện/kỳ đo. WF-13 có thông điệp, CTA và metadata/ý định tìm kiếm nhất quán cho sản phẩm. |
| Tuyên bố có căn cứ | Toàn bộ câu bán hàng tránh kết quả, bảo chứng, mức giá hoặc nghiên cứu bên ngoài chưa được quan sát. Nếu dẫn một con số, đọc cả ngữ cảnh. |

Mỗi quyết định chấm phải có nhận xét cụ thể theo nội dung. Tách trường model tự sinh khỏi phần hệ thống chèn lại từ manifest. Không dùng số lần xuất hiện của SKU như điểm chuyên môn. Ghi rõ người hay AI chấm, việc nhận biết phiên bản có thể xảy ra ngay cả khi ẩn nhãn. Công biên tập của người dùng và tỷ lệ được khách thật chấp thuận để trống cho tới khi có pilot.

**Chạy lại.** Từ thư mục repo đã cài `requirements-dev.txt`, dùng PostgreSQL thử nghiệm độc lập đã chạy publisher, cấu hình DSN migrator và runtime theo HANDOFF, mailbox phát triển riêng và endpoint llama.cpp loopback có weights được ghim. `AMC_EVAL_MODEL_FILE` trỏ bản weights trên máy chấm nếu đường dẫn ở model server khác mount. Mỗi nhánh dùng một DB mới, một thư mục kết quả chung. Trong bước render bằng chứng, chỉ gửi hồ sơ tổng hợp.

```sh
python tests/evaluation/c3/run_comparison.py legacy artifacts/c3
python tests/evaluation/c3/run_comparison.py projected artifacts/c3
python tests/evaluation/c3/review_packet.py artifacts/c3
```

Mỗi người chấm đọc các packet của workflow mình phụ trách và xuất một mảng JSON gồm `id`, `scores` (sáu số 0/1 theo thứ tự bảng) và `observation`. Lưu hai phiếu thành `artifacts/c3/review/ratings-wf03.json` và `ratings-wf13.json` cùng thư mục. Chạy `python tests/evaluation/c3/score_review.py artifacts/c3` để kiểm SHA-256 của packet, digest do API trả về, liên kết run và đủ 20 bản trước khi tính điểm. [Bản giao và kết quả đã đối chiếu ngày 25/11](../../../docs/evaluation/c3-20261125/REPORT.md).

Đối chiếu digest weights và fixture trong hai file conditions trước khi chấm. Các thư mục theo từng ca giữ bản giao nguyên văn, mã run, digest, số token, kết quả từng lượt và SHA request. Đề chấm ở `review/packets`, khóa ánh xạ ở `review/key.json`.
