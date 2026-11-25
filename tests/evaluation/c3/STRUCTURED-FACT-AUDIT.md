# Đối chiếu dữ kiện thương mại trong bản giao C3

Chạy từ checkout chứa fixture đã niêm phong. Công cụ chỉ đọc JSON cục bộ, dùng thư viện chuẩn Python. Mỗi thư mục series chứa các thư mục con mang ID của brief. Mỗi brief cần tệp `result.json`. Bộ 10 brief mới còn cần `paired-role.json` để đối chiếu projection. Đường dẫn và SHA checkout phải thuộc đúng lượt CI tạo artifact.

```sh
python tests/evaluation/c3/structured_fact_audit.py c3-product-v2 \
  --mode study --fixture tests/evaluation/c3/qualification-v2.json \
  --checkout "$REVIEWED_SHA" --out commercial-study.json
python tests/evaluation/c3/structured_fact_audit.py c3-unit-recovery \
  --mode recovery --fixture tests/evaluation/c3/holdout-v1.json \
  --checkout "$REVIEWED_SHA" --out commercial-recovery.json
python -m pytest -q tests/test_structured_fact_audit.py
```

Mỗi brief đóng góp bốn mẫu đối chiếu riêng, gồm bản xem trước và trường điều kiện thương mại trước và sau lần biên tập theo kịch bản. WF-03 dùng trường bằng chứng của nghiên cứu và WF-13 dùng trường điều kiện thương mại trong nội dung trang đích. Tệp báo cáo ghi mã nguồn Git của lượt chạy, SHA-256 của bộ đề, từng artifact, file chấm, SHA của manifest, digest của bản xem trước và revision. Với bộ phục hồi, nguồn đối chiếu là dữ liệu đã đông cứng cùng receipt về đơn vị đã xác nhận. Hash manifest là định danh do lượt chạy ghi lại. Bản chụp projection đầy đủ chỉ có ở bộ 10 ca.

Đọc `coverage` theo từng trường hiển thị và từng bản lưu. Giá, tiền tệ, mẫu số, đơn vị, thuế phải xuất hiện trong cùng một báo giá. MOQ, hai đầu bậc giá, lượng đặt và điều kiện đi kèm được kiểm tra riêng. Một điều kiện lặp trong cả qualifiers và conditions được đếm một lần. So sánh các phiên bản có cùng mẫu và giữ nguyên mẫu số khi thiếu artifact. Dòng nào chứa báo giá bổ sung cần được đọc lại trong ngữ cảnh của sản phẩm. Các tín hiệu QA của Studio và kết quả đối chiếu từng câu của AMC nằm riêng ở `product_qa`.

| Kết quả | Cách đọc |
| --- | --- |
| `matched` | Giá trị đã đối chiếu khớp với căn cứ trong đúng khai báo |
| `mismatch` | Phân tích được khai báo và phát hiện giá trị khác |
| `unconfirmed` | Chưa tìm được nguyên văn dữ kiện hoặc điều kiện trong cùng khai báo |
| `inconclusive` | Thiếu artifact, nhãn, đơn vị hỗ trợ hoặc liên kết đủ rõ để chấm |

Công cụ nhận các khai báo tiếng Việt/tiếng Anh theo hợp đồng giao diện đã công bố. Các diễn đạt tự do, mệnh đề mới, ngữ nghĩa hàm ẩn và tính đúng ngoài thực tế vẫn cần người đọc đánh giá. Mã thoát 2 báo có bản ghi không đủ căn cứ đầu vào hoặc có thư mục ngoài kế hoạch. Mã thoát 0 cho biết bộ đầu vào đọc được đầy đủ. Xem các trạng thái cấp trường để đánh giá kết quả.
