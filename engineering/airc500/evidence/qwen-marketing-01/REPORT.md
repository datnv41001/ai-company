# AIRC-500 · kết quả pilot Qwen local

## 1. Tóm tắt

Đã chạy pipeline trên cặp Git commit tổng hợp về điều khoản vé và thông tin triển lãm. Bằng chứng là raw response Qwen, bundle đầu vào, public key và receipt Ed25519.

## 2. Phạm vi

Base `6f23449c5a3467ddcb5e8e773c40768837d5bbc5`, head `a381db60e8b539b3cdd06c0bee343b3348f204c4`. Tám đơn vị gồm bốn lỗi đã gieo và bốn ca sạch. Cùng holdout cho hai cấu hình.

## 3. Người tham gia

Targeted: 9 ID, 11 assignments, 11 calls, 11 receipt được chấp nhận, 0 receipt bị từ chối. Hai người phản biện được phân lại sang miền khác. Tất cả dùng cùng checkpoint Qwen. Baseline dùng một reviewer, tám lượt mù, cùng phân vùng và giới hạn mẫu với tám lượt mù của targeted.

## 4. Bằng chứng và chi phí

Targeted sử dụng 4473 input, 2419 output, concurrency 1. Baseline dùng 2960 input và 2025 output. Chi phí API trả phí 0 USD. Chưa đo điện và giá giờ máy. Tử số/mẫu số evidence validity: 2/4.

## 5. Finding đã xác minh

H01, H04

## 6. Finding bị bác

targeted-07-H02, targeted-07-H03

## 7. Bất đồng

Không ghi nhận ca thiểu số đúng thắng từ hai ý kiến sai trở lên trong lượt này. Test deterministic riêng kiểm chứng quy tắc; xem raw verdict từng người trong results.json. Verifier đối chiếu độc lập với hai Git blob, ý kiến trọng tài được lưu cùng mọi phản đối.

Ca phản chứng đưa vào lượt Qwen phân xử thật: hai nhận định biên soạn cho fixture nói giá khớp, một nhận định trỏ tới hai dòng Git. Đối chiếu USD 18 với USD 12 xác nhận kết luận thiểu số. Ba lập luận đầu vào này là dữ liệu tổng hợp. Ý kiến Qwen thực về H01: insufficient. Disposition của verifier độc lập: verified.

## 8. Nghiệp vụ

Baseline raw: TP=4 · FP=4 · FN=0 · TN=0 · critical_detected=3 · critical_total=3. Targeted raw: TP=2 · FP=2 · FN=2 · TN=2 · critical_detected=2 · critical_total=3. Sau xác minh: TP=2 · FP=0 · FN=2 · TN=4 · critical_detected=2 · critical_total=3. Duplicate rate: 0/4. Actionability: 0/2. Mẫu quá nhỏ để kết luận về chất lượng Marketing thực tế.

Các finding khớp vị trí nhưng model đảo giá trị nguồn và bản viết trong lời giải thích: targeted-07-H01, targeted-07-H04. Evidence validity ở trên chấm đúng dòng và có chênh lệch thực. Độ chính xác của lời giải thích là phép kiểm riêng.

## 9. Kỹ thuật

Đọc source qua immutable Git blob; mỗi lượt blind nhận context chuyên môn riêng. Tất cả output blind đã niêm phong trước khi trao đổi. Archive lưu checksum của adapter binary và GGUF.

## 10. Bảo mật

Adapter riêng chỉ nghe loopback, context là dữ liệu fixture tổng hợp, inference không có tool. Danh tính chứng thực là adapter local. Public key phải so với fingerprint đã duyệt qua kênh tin cậy.

## 11. Release blockers

Thiếu ground truth nghiệp vụ độc lập và cỡ mẫu; commercial GA NO-GO.

## 12. Quyết định

Kết luận cho PR fixture: changes_requested. Chỉ đánh giá các field được ghim.

## 13. Đầu việc Codex

Chủ nội dung đối chiếu từng giá trị trong verified_units với nguồn tại head, sửa đúng trường và giữ nguồn đã duyệt.

## 14. Hồi quy

Chạy lại kiểm chữ ký, Git blob, phản chứng thiểu số, giữ ca sạch và chấm lại đầu ra trên một head mới.

## 15. Ưu tiên tiếp theo

Tăng corpus theo domain, khóa holdout kín, phê duyệt ngưỡng trước khi mở rộng 25–50, 100–150 rồi 500 ID. Thử thêm family model thực sự độc lập. Nguồn hiện tại là fixture engineering deterministic.
