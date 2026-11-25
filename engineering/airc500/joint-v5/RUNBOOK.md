# Đối chiếu năng lực theo reviewer và checkpoint

Bộ ca gồm tám quyết định tổng hợp được ghi trước inference. Hai model đọc cùng dữ liệu. Mỗi nhánh dùng hai lượt đọc mù và một lượt quyết định cho mỗi nhóm bốn ca. Nhánh một người dùng MK-022 cho cả ba lượt. Nhánh hợp tác dùng lượt đọc đầu của MK-022, lượt độc lập của MK-052 rồi MK-052 quyết định sau khi đọc hai ý kiến đã ký. Tiết kiệm hai invocation trên mỗi checkpoint bằng cách dùng lại đúng cùng biên nhận của vòng đầu cho hai nhánh. Mỗi nhánh có cùng sáu lượt logic, cùng context limit, output cap, seed theo giai đoạn và ngân sách. Báo cáo tính tài nguyên thực một lần cho mỗi invocation.

Người xây dựng fixture gán nhãn và đóng dấu trước khi gọi model. Các trường reason và repair là lựa chọn hữu hạn có ý nghĩa nghiệp vụ. Điểm joint chỉ đạt khi đúng cả verdict, source, reason và repair cho cùng ca. Đây là phép thử chọn quyết định có căn cứ; năng lực viết khuyến nghị tự do, chất lượng trên repository thực, khả năng phát hiện lỗ hổng và năng lực chuyên gia nghiệp vụ ngoài bộ ca còn chưa đo. Hai reviewer có thể dùng cùng checkpoint. Số lượt gọi không đo tính độc lập giữa model.

## Chạy lại trên máy khác

Từ thư mục gốc repo, cài dependencies tooling rồi kiểm archive bằng Python. Git phải tạo được repo tạm trong thư mục TEMP.

```sh
python -m pip install -r engineering/airc500/requirements-pilot.txt
python -m unittest discover -s engineering/airc500 -p test_joint_study.py -v
python engineering/airc500/joint_study.py score --pin 13220927017445a328aabc096359582a3b42a92e02bbe6e4162abefedbb353a7
```

Ledger xác thực SHA fixture, grant, binding reviewer/model, template, peer context, output, usage và chữ ký. Hai archive có runtime fingerprint và thời gian thực thi từng call. Để chạy thí nghiệm mới, dùng một thư mục/version kết quả mới, đóng dấu lại nguồn và đáp án, cấp khóa signer ngoài checkout và dùng checksum của đúng binary/weights ghi trong enrollment. Chạy tuần tự một model trên host và ghi cả kết quả âm. Rollback tooling bằng ngừng runner v5; các archive đã ký tiếp tục replay offline.

[Thiết kế discovery giới hạn](DISCOVERY.md) · [Báo cáo so sánh trên holdout](REPORT.md) · [Gate khi dùng source thực](../PUBLIC-RESEARCH.md).
