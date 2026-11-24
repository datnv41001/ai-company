# Đối chiếu độc lập kết quả pilot Qwen

Ngày 24/11/2026. Agent kiểm tra đã đọc lại byte kết quả sau khi adapter hoàn thành, không thực hiện thêm lượt suy luận. Phạm vi độc lập là đối chiếu dữ liệu và kết luận của pilot; người kiểm tra cũng tham gia xây dựng journal, nên ghi chú này không phải chứng nhận độc lập cho chính journal hoặc hạ tầng ký.

**Nguồn đối chiếu.** PR tổng hợp có base `6f23449c5a3467ddcb5e8e773c40768837d5bbc5`, head `a381db60e8b539b3cdd06c0bee343b3348f204c4`. SHA-256 của trust registry khớp giá trị ghi lúc khởi chạy: `400f86483df5c4521ace9c26c5f83975f2e45415d56c8af1a6e684e259948ca9`. Hai file [targeted](evidence/qwen-marketing-01/targeted/calls.jsonl) và [baseline](evidence/qwen-marketing-01/baseline/calls.jsonl) có SHA-256 lần lượt `708c1df97eda9b55b5b40b451a8fabe266a5b838152ae3fe12fae7c6556d1128` và `e4003e2751b7aed84c0fa8d363e48cec948ac98ec097d7c486459de7b91a7bd8`.

Đã kiểm chữ ký Ed25519 của từng receipt bằng public key và RFC 8785, độc lập với mã tổng hợp báo cáo. Với từng lượt gọi, phép kiểm giải mã raw response, băm lại request và output, đối chiếu nhà cấp execution ID, model alias, số token, run ID và hai SHA. Các request blind chỉ có system message và bundle riêng cho reviewer; các field fixture chứa hai trích đoạn cần so, không có ý kiến peer hoặc nhãn đúng/sai. Cả hai cấu hình dùng cùng một GGUF Qwen2.5 có digest `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`.

| Quan sát | Targeted | Baseline |
|---|---:|---:|
| Reviewer ID khác nhau | 9 | 1 |
| Calls blind / cross / arbitration | 8 / 2 / 1 | 8 / 0 / 0 |
| Input / output token | 4.473 / 2.419 | 2.960 / 2.025 |
| TP / FP / FN / TN trước xác minh | 2 / 2 / 2 / 2 | 4 / 4 / 0 / 0 |
| Lỗi được phát hiện và được verifier xác nhận | H01, H04 | H01, H04, H05, H08 |
| Candidate có evidence hợp lệ | 2/4 | 10/20 |
| Candidate trùng | 0/4 | 12/20 |
| Finding xác minh có đề xuất nêu đúng giá trị cần sửa | 0/2 | 0/4 |
| Chi phí API trả phí | 0 USD | 0 USD |

**Thiểu số và phân xử.** Không có ca mù tự phát nào trong đó một nhận xét đúng thắng ít nhất hai nhận xét khẳng định sai. Ở bài tập phản chứng H01, hai ý kiến sai và một ý kiến có locator là ba lập luận được biên soạn trước khi đưa vào packet sau seal. Trong lượt phân xử thật, Qwen ghi `insufficient`, đề xuất `keep` và nhầm vai trò của hai mức giá. Verifier riêng đối chiếu giá đã duyệt USD 18 với giá đăng USD 12, từ đó xác nhận finding thiểu số. Ba lập luận fixture không được cộng vào số reviewer hoặc lượt gọi.

Tám đơn vị đều là fixture có đáp án xác định theo giá trị nguồn. Cỡ mẫu, việc dùng chung checkpoint, và cách chấm actionability chỉ qua giá trị cần thay thế giới hạn kết luận về năng lực chuyên môn thực tế. Chi phí điện và giờ máy chưa được đo. [Báo cáo cùng các hiện vật có thể kiểm lại](evidence/qwen-marketing-01/REPORT.md).
