# PR #60 · Câu mở đầu có mời người mua làm đúng việc?

Independent Reviewer giữ quyết định HOLD trên head `555b968c85b09d52d50d2fd165ea9ff320e5afcd` (base `4140563a89539acd19f1a7d5a16662c8dec5f6af`). Ở ca Phách Mở, CTA “Chọn buổi” và hook “Quý vị cần báo giá?” có thể cùng vượt qua QA. Thông điệp đầu tiên có thể khiến người học hiểu sai công việc mà đơn vị tổ chức đang mời họ thực hiện. Chuỗi receipt liên phòng ban đã được chấp nhận ở lần review trước. [Gói lịch sử và kết quả kiểm thử trên head cũ](https://github.com/datnv41001/ai-company/tree/db862100aabf76641fe93fd207868c095f9027eb/docs/evaluation/round60-verification)

## Cách người duyệt đối chiếu

1. Xác nhận head và base trên PR. Xem ma trận PostgreSQL với ba hành động `rfq`, `appointment`, `choose_session` và bốn văn phong `plain`, `concise`, `formal`, `friendly`. Đọc nguyên văn hook của Content, storyboard ban đầu, hook đã sửa và CTA trên từng ca.
2. So thông điệp với mục đích và nguồn thương mại được duyệt. Một điều kiện về giá có thể cần xuất hiện trước CTA đặt lịch hoặc chọn buổi. Kiểm trường hợp có nguồn và thiếu nguồn riêng biệt. So hook hiển thị với lời thoại và phụ đề thực ở đầu storyboard.
3. Lần từ manifest và queue tới checkpoint Content, revision/digest của bản sửa, lần nộp và quyết định của người QA khác editor. Đối chiếu các trường khóa của phép thử hook-only, gồm nội dung có nguồn, điều kiện thương mại, quyền, timing, CTA và nguồn phân phối. Một HTTP 200 khi lưu bản nháp chưa đủ để kết luận QA chấp thuận.
4. Mở ảnh đối chứng trên mobile. Kiểm tên thao tác, mã nguồn F1/F2 và nội dung phân công của Director. Người kiểm toán vẫn cần truy lại digest trong chi tiết.

Phép thử dùng brief tổng hợp, queue nội bộ và PostgreSQL. Hướng dẫn chạy stack và publish release ở [hợp đồng Content](../../WF08-CONTENT-HANDOFF.md). CI của PR lưu dữ liệu từng bản checkout trong artifact `connected-review-head` hoặc `connected-review-integration`, cùng JUnit và ảnh Chromium riêng. [Draft PR và hồ sơ bằng chứng gắn SHA](https://github.com/datnv41001/ai-company/pull/60)

**AMC-R60-01.** Trong ca chọn buổi, formal, trên head cũ, người QA đã duyệt “Quý vị cần báo giá?” dù CTA là “Chọn buổi”. Đối chiếu với câu trên bản sửa “Buổi nào phù hợp với quý vị?”. Chạy `python -m pytest -q tests/test_storyboard_semantics.py tests/test_storyboard_runtime_compatibility.py` với PostgreSQL. Đặt `AMC_SEMANTIC_EVIDENCE` vào thư mục mới để lưu JSON theo ca. Bản đầu, thao tác đổi hook và quyết định của người QA đều có trong artifact của chính lần chạy.

**AMC-R60-02.** Chromium Windows tái hiện mã nguồn F1 bị tách thành hai dòng ở 390 px. Sau sửa, F1/F2 giữ trên một dòng. Tên thao tác hook dài nhất đo được 132 px trong vùng hiển thị 246 px. Lần chạy ban đầu tại đúng kích thước trên chưa tái hiện lỗi cắt dropdown. Màn hình Director đã hiện nhiệm vụ từ plan đã khóa và mở được digest qua bàn phím. So bộ ảnh sáng/tối ở 390, 820 và 1280 px.

**Câu hỏi cho Independent Reviewer.** So hai brief có yêu cầu hiển thị điều kiện trước CTA, một brief có nguồn điều kiện và một brief thiếu nguồn. QA có đang cho phép bên Marketing cung cấp đủ thông tin mua hàng và vẫn giữ đúng mục tiêu đã được phê duyệt trong từng ca?

## Versioning và rollback cho môi trường dev

Schema vẫn là v26. WF-08 @1 giữ nguyên catalog và digest manifest `4dd698583db731fc5e02dfba95eeb92c028466a885266b92a48367c8978ad40e`. Với draft @2, release manifest trên head cũ có digest `25bd28157c9b48a49de070857e929acbe5cebeec9fd2b34951c53e5766e44405`. Manifest draft mới là `8751146323a37269206ce40d80465a29155edbad8fcf8b88673f12902fe6b524`, dùng adapter `5ad26a3fd5c2983051b0f600911a1292cdbf189124a1e2d80d646eae2a4bf348`. Hook là nội dung người mua nhìn thấy, vì vậy byte mã xử lý bản biên tập cũng phải thuộc digest adapter @2 và runtime phải có fingerprint tương ứng.

Để thử bản sửa trên máy khác, lấy đúng checkout đã kiểm thử, tạo database/volume dev mới, chạy migration, publish catalog @2 từ checkout đó rồi kích hoạt cho campaign tổng hợp. Trên database đã có draft @2 khác digest, giữ lịch sử release và audit. Pin cũ phải bị từ chối khi xếp việc mới bằng runtime mới. Để tái hiện hoặc rollback, chạy checkout `555b968c` cùng database dev đã sao lưu của chính phiên bản đó. Không ghi đè release, đổi digest bằng tay hoặc chuyển bản QA cũ thành phê duyệt cho bản mới.

<a id="render"></a>
## AMC-R60-03 · phép đo trước production

Trong `app/storyboard_distribution.py:create`, thao tác tạo distribution khóa tài liệu và nguồn, gọi `render_bytes`, ghi biên nhận rồi commit. Thiết kế này giữ snapshot nhất quán nhưng thời gian render cũng nằm trong thời gian giữ khóa. Chưa có giới hạn concurrency hoặc SLO production đã được chứng minh cho đường này.

| Phép đo đề xuất cho Infrastructure và Workforce | Bằng chứng cần có |
| --- | --- |
| Chạy preview tổng hợp ngắn và dài ở mức 1, 2, 4, 8 yêu cầu đồng thời trên cùng tài liệu, khác tài liệu trong tenant và khác tenant | Cấu hình máy/giới hạn, thời lượng clip, cold/warm, số mẫu, throughput, p50/p95/p99 của request, thời gian chờ/giữ khóa, timeout và độ trễ edit/QA đồng thời |
| Theo dõi tiến trình ứng dụng, renderer và PostgreSQL trong lúc tăng tải rồi trả về rỗi | CPU, peak RSS, dung lượng tạm/đỉnh, số byte media và thay đổi dung lượng DB trên mỗi preview đã commit; lưu cả lần cạn tài nguyên |
| Ngắt tiến trình ở bước render và trước commit, gửi lại request ID cũ và gửi một yêu cầu mới | Không có payload hoặc receipt dở dang được ký; giải phóng khóa, giữ đúng revision và quyền giữa hai tenant; replay của yêu cầu đã commit trả đúng một receipt |

Chủ vận hành và Product Owner cần chốt ngân sách tài nguyên, thời gian chờ và ngưỡng tác động sang tenant khác trước phép đo. Lưu kết quả vượt ngưỡng, đo khả năng hồi phục và quyết định giới hạn tải hay tách renderer sau khi có số liệu. Đây là backlog qualification. Production và Commercial GA vẫn **NO-GO**.

## Sau khi Independent Reviewer nghiệm thu

| Thứ tự và người phụ trách | Đề xuất và điều kiện quyết định |
| --- | --- |
| 1. Marketing lead và người giữ consent | Dùng [protocol practitioner](PRACTITIONER.md). Khóa brief, nhánh, bản đầu và tiêu chí đánh giá trước khi giao. So chất lượng bản đầu, phút biên tập, phút QA, số lần trả và quyết định nhận/sửa/từ chối. Báo cả ca bỏ dở và mẫu số từng chỉ số. |
| 2. Sales Operations và chủ KPI | Chốt [hợp đồng qualified RFQ](MEASUREMENT.md) gồm nguồn authority, đơn vị phân bổ, consent, điều kiện SKU/MOQ, thời điểm, cửa sổ, cách xử lý replay/hủy/sửa và mất liên kết. QA xác minh bằng nguồn độc lập trước khi phê duyệt định nghĩa có version. |
| 3. Product Owner và trưởng bộ phận | Dùng lý do trả bản và nút thắt đo được để chọn bước giao việc tiếp theo. Ví dụ, nếu Sales chưa quyết định được yêu cầu hợp lệ dù creative đã được nhận, ưu tiên hợp đồng qualification và đường phản hồi Sales → Marketing theo dependency V1. Đánh giá bằng số công việc được người nhận chấp thuận và thời gian thực tế. |

Các mục trên mới là đề xuất. Số người hành nghề trong thử nghiệm này bằng 0. Quyết định tuyển, chạy thử trên khách thật và chi phí cần thẩm quyền riêng.
