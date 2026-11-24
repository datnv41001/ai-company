# Ngân sách và lập lịch AIRC-500

## Chính sách pilot đề xuất

Đơn vị ngân sách là **run engineering**. Khi chưa có phê duyệt chi phí, dùng adapter local đã allowlist, không credential dịch vụ trả phí, network model đóng. Dù đơn giá API bằng 0, local vẫn tiêu thụ GPU/CPU, giờ máy và điện. Báo riêng loại chi phí nào đã đo, loại nào chưa đo. Không ghi con số chi phí hạ tầng bằng 0 chỉ vì không gọi API.

| Tham số | Targeted pilot | Full rehearsal đề xuất |
|---|---:|---:|
| ID theo nghĩa vụ | ví dụ 8 chuyên viên + 1 trọng tài | 490 chuyên viên + 10 trọng tài |
| Concurrency tối đa cả run | 2 | 4 |
| Input + output trần mỗi attempt, gồm cả prompt và context | 3.000 + 1.000 token | 3.000 + 1.000 token |
| Vòng trao đổi tối đa | 2 | 2 |
| Số lần retry tối đa mỗi assignment | 1 | 1 |
| Deadline run / timeout attempt | 45 phút / 90 giây | 12 giờ / 90 giây |
| Trần microusd trả nhà cung cấp, mặc định | 0 | 0 |

**Ước lượng trước khi nhận run.** Targeted minh họa dành 8 lượt blind, 2 lượt cross tổng cộng cho cả hai vòng và 1 lượt arbitration. 11 lượt đầu, tối đa 22 attempts tính cả retry → 88.000 token. Full dành 490 blind, 40 lượt cross tổng cộng và 10 lượt trọng tài (chia các hồ sơ); 540 lượt đầu, tối đa 1.080 attempts → 4.320.000 token. Nếu cần thêm trao đổi, coordinator tái lập kế hoạch hoặc để unresolved. Không tự mở rộng quota. Nếu một batch có nhiều finding, packet vẫn phải nằm trong trần context; phần không đọc ghi rõ. Đây là số dự trù, chưa có model được gọi để lập thiết kế.

**Ví dụ phép tính tiền.** Chỉ để test số học, giả sử tariff giả lập là 1 micro-USD/input token và 3 micro-USD/output token, chưa gồm phí cố định. Reserve tối đa 6.000 micro-USD/attempt; targeted tối đa 132.000 micro-USD (0,132 USD), full tối đa 6.480.000 micro-USD (6,48 USD). Đây không phải báo giá nhà cung cấp hoặc ngân sách đã được duyệt. Tariff thực phải pin version, currency, rounding và mọi overhead tính phí, gồm reasoning/cached tokens nếu adapter hỗ trợ. Thiếu trần chắc chắn thì loại adapter đó khỏi lịch.

## Sổ chi phí và thất bại giao dịch

1. Admission giả định deadline, worker slots, token cap và model đã pin. Đối chiếu cận dưới thời gian với số slot và phụ thuộc barrier. Đánh dấu chưa chắc hoàn tất khi throughput chưa đo. Giữ chỗ cho veriﬁcation và arbitration trong kế hoạch; không tiêu hết vào blind.
2. Mỗi attempt ghi một reservation bền vững **trước** lệnh gọi. Khóa theo account/run; trần hiệu lực là giá trị nhỏ nhất của account, run và assignment. Chỉ nhận nếu `settled + open reservations + new maximum ≤ cap` cho cả token và tiền. Giới hạn slot toàn cục lẫn theo run. Phê duyệt trả phí phải do chủ ngân sách ký, khớp repo/run, model, tariff, mức tiền, token và hạn. Budget dương đơn thuần không cấp quyền.
3. Ledger đi qua reserved → dispatched → settled hoặc uncertain. Trước dispatch có thể release; sau dispatch chỉ trả lại phần chênh khi có usage tin cậy. Timeout/mất ACK giữ phần phơi nhiễm tối đa. Retry chỉ khi biết an toàn hoặc adapter bảo đảm idempotency, có reservation riêng và còn deadline. Cấm retry mù giao dịch chưa rõ kết quả.
4. Receipt lặp cùng attempt/usage là no-op; cùng key nhưng usage xung đột đưa vào reconciliation. Usage vượt reserve đánh dấu vi phạm, khóa admission tiếp và báo cho chủ ngân sách. Journal ghi đủ trace nhưng không chứa secret hay raw prompt của khách hàng.
5. Cancel tăng fencing epoch, chặn mọi lease mới, thu hồi grant và kết thúc in-flight theo timeout. Usage đến muộn chỉ vào ledger. Checkpoint ghi event root, outstanding reservations, lease epoch, seal, round và deadline; resume phát lại theo idempotency key. Hết thời gian hoặc hết ngân sách sinh báo cáo partial với coverage thiếu.
6. Báo cáo có planned/selected/invoked/completed/accepted theo ID; attempts, retries, input/output, settled/uncertain theo family; wall-clock, peak slots và cost per unique verified finding. Nếu chưa có finding đã xác minh, ghi N/A. Nhiều lượt cùng checkpoint chia sẻ sai lệch, không được tính là bằng chứng độc lập.

Thử tải trước full mode bằng đo throughput local trên fixture vô hại. Điều chỉnh lượng context, slot hoặc thời hạn ở phiên bản policy mới trước run. Tất cả con số ở trên là giới hạn thiết kế, không phải kết quả benchmark.
