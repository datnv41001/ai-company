# AIRC · nghiên cứu so sánh trên holdout tổng hợp v2

Mục tiêu là đo xem việc đổi reviewer và bổ sung tranh luận có thay đổi phát hiện, lời giải thích và hướng sửa trên **cùng một quan sát** hay không. Công cụ ở nhánh engineering. [Pilot 19 lượt trước đó](PILOT.md) giữ nguyên raw output, khóa public, thuật toán chấm v1 và kết quả 0/2 hướng sửa có thể giao.

## Năm cấu hình, hai seed

| Cấu hình | Đầu vào và cách chấm |
|---|---|
| Verifier xác định | Kiểm tra mọi field kiểu dữ liệu được hỗ trợ và công bố danh sách miền ngữ nghĩa phải abstain. Không có inference. |
| Một AI | Cùng ID đánh giá hai lần độc lập trên mỗi batch. Union candidate mù là output. |
| Nhiều AI độc lập ở vòng mù | Một lượt chung từ nhánh một AI + một lượt của chuyên môn khác. Giữ đúng số lượt, thứ tự case, tập nguồn và seed theo vị trí so với cấu hình một AI. |
| Một AI + verifier | Gửi tất cả candidate đã xuất của cấu hình một AI qua verifier, yêu cầu citation và đúng đối tượng. Verifier không tự thêm lỗi mà AI chưa đề xuất. |
| Nhiều AI + cross + arbitration + verifier | Dùng lại hai lượt mù của nhánh nhiều AI. Challenger và arbitrator đọc đúng phạm vi đã pin; có quyền bổ sung, phản đối hoặc hiệu chỉnh. Cuối cùng verifier kiểm lại mọi candidate từng nêu, kể cả ý kiến thiểu số đã bị bác. |

Lượt chung chỉ được thực thi một lần rồi dùng cho phép so ghép cặp. Không cộng tổng số call của năm dòng làm participation. Seed 17 và 43 đánh giá cùng một holdout. Từng seed báo riêng để tránh giả định hai lần chạy cùng ca là hai mẫu độc lập. Ngân sách engineering tối đa 88.000 token/seed/cohort, concurrency 1, 90 giây/attempt, deadline 45 phút, chi phí API trả ngoài bằng 0. Một AI và nhiều AI ở vòng mù có cùng số lượt, trần token và phạm vi. Nhánh đầy đủ có thêm hai vòng và trả thêm chi phí compute tương ứng. Hai coordinator có thể chạy đồng thời trên hai slot vật lý của cùng host. Report công bố số token thực và thời gian dispatch → receipt trong điều kiện máy đó; đây là thời gian quan sát, không phải benchmark latency phần cứng cô lập. Cùng Qwen 0.5B không tạo ra bằng chứng về model diversity.

## Dữ liệu và oracle

[Casebook tái lập](quality_corpus.py) tạo 96 ca trong 12 miền. Mỗi miền có bốn lỗi và bốn ca sạch. Giá trị tiền, tiền tệ, số lượng/đơn vị, nhầm variant, nhầm thị trường, khuyến mãi hết hiệu lực, điều kiện bị bỏ sót, phủ định, CTA sai, claim thiếu nguồn, scope hai khách và đếm một lần cho receipt lặp đều có ca đối chứng. Một số cặp giá đảo chiều nguồn/quan sát và một số ca sạch có diễn đạt tương đương. Cohort bổ sung có 16 trạng thái identity tổng hợp, gồm xác minh, hết hạn, người nhận sai, lời mời đã dùng/đã thu hồi và trạng thái đăng nhập. Hai cohort có cặp commit Git/manifest độc lập. Cả hai chỉ xử lý dữ liệu Marketing và policy fixture an toàn.

Trước lượt đầu, admission pin hash casebook mà model được thấy, hash answer key riêng, hai Git SHA nguồn, catalog, kế hoạch đầy đủ, hai public key khác nhau và nghĩa vụ từng batch. Dữ liệu chấm không có trong messages model. Context blind chứa nguồn, bản quan sát, các lựa chọn trả lời và rubric. Peer packet chỉ xuất hiện sau seal. Mỗi trường hợp chia sẻ verdict, operation và loại lý do đã chọn; reviewer đọc lại nguồn và các giá trị độc lập. Thí nghiệm chưa đo tranh luận tự do hoặc hiệu quả trao đổi nguồn mới. Tập này là holdout mù với model; mã sinh nhãn được công bố để engineering replay. Không dùng tập công khai để nhận chứng chỉ năng lực nghiệp vụ.

Nguồn nhãn là fixture deterministic hoặc synthetic regression lấy cảm hứng từ invariant đã review. Số nhãn từ quan sát sự cố lịch sử thực, nghiệp vụ do người chấm và AI phân xử đều bằng 0. Trong 12 miền, ba miền ngữ nghĩa (phủ định, CTA và claim định tính) có truth tổng hợp nhưng verifier typed chủ động abstain. Người đọc có thể so số candidate đúng trên toàn holdout với số finding có thể xác minh tự động. So sánh giá trị định kiểu không đủ để xác nhận nội dung Marketing thực tế.

## Vòng đời và hướng sửa

`candidate → challenged | corroborated | revised → rejected | unresolved | verified`. Một candidate mới có thể xuất hiện ở bất kỳ vòng AI nào. Mỗi sự kiện giữ finding ID, unit, phase, reviewer, attempt và bản đề xuất cụ thể. Lời giải thích mù còn nguyên trong bằng chứng ký. Chỉ verifier cuối mới đặt `verified`. Khi cross hoặc trọng tài muốn bác một lỗi thật, verifier vẫn kiểm lại lịch sử đề xuất đã nêu và nguồn đã pin.

Hướng sửa có sáu field: đối tượng chịu ảnh hưởng, giá trị quan sát, giá trị cần đạt, operation, nguồn chứng minh, criterion hồi quy. Cohort chính mã hóa tám chỉ số menu thành một chuỗi tám chữ số để giới hạn token, replay mở rộng thành record có tên và giá trị cụ thể. Với cohort identity bổ sung, model chọn trực tiếp chuỗi giá trị trong các trường JSON có tên. Năm cấu hình trong mỗi cohort giữ cùng wire. Không gộp hai cohort để suy ra ảnh hưởng độc lập của kiểu wire hay của domain. Menu verdict cố định `flag` ở vị trí đầu cho cả hai kiểu wire. Lựa chọn mặc định của model nhỏ có thể làm tăng FP; benchmark tiếp theo cần counterbalance thứ tự lựa chọn trên ca mới. Cần đúng cả sáu field và xác định có lỗi mới nhận credit. Câu phủ định có chứa giá đúng, đảo nguồn/bản viết, sửa nhầm SKU, nhầm căn cứ hoặc dùng operation giữ nguyên đều thất bại. Lời giải thích chấm riêng theo loại sai lệch, chiều current/expected, subject và nguồn. Đây là phép đo có cấu trúc, chưa đo chất lượng văn xuôi tự do.

Ở mỗi phase, báo precision, recall, FPR, false finding đã gỡ, true finding mới, true finding bị mất, ca còn bỏ sót cùng hướng sửa và lời giải thích đúng. Tỷ lệ nhóm được tính theo unit sau khử trùng. Một hướng sửa tốt ở lượt mù có thể được ghi nhận khi ít nhất một người cung cấp đủ cả sáu trường; phase sau dùng bản đã được sửa gần nhất. Tách số nhiệm vụ đã thực thi, số nghĩa vụ có căn cứ xác nhận, và chất lượng. Thiếu evidence bắt buộc dẫn tới `inconclusive` dù mọi receipt đã hợp lệ.

Khoảng 95% dùng Wilson với số đơn vị trong từng seed. Chạy lại cùng seed hoặc cùng template không tăng mẫu số. Mỗi miền nhỏ chỉ có bốn ca âm, bốn ca dương (identity bổ sung có tám mỗi loại); số liệu ở cấp miền chỉ dùng để phát hiện điểm yếu. Để đánh giá FPR mục tiêu 10%, ngay cả 0 lỗi trên 4 ca âm vẫn có cận trên khoảng 49%. Trước nghiệm thu yêu cầu tối thiểu 35 ca âm độc lập cho mỗi miền (0/35 cho cận trên xấp xỉ 9,9%), đủ ca dương critical, và nguồn nhãn nghiệp vụ độc lập. Khi có false positive, cần nhiều mẫu hơn. Công bố khoảng toàn corpus như mô tả engineering; các template cùng họ còn có tương quan.

## Quyết định về mở rộng

1. Bắt đầu ở fixture và protocol review có version. Nếu trả lời sai hướng hoặc bỏ sót domain thiết yếu, ưu tiên điều chỉnh model/rubric và thu nhãn mới. Giữ một tập chưa từng dùng để tuning.
2. Chỉ thí điểm trên PR lịch sử được phép khi quyền read-only, filesystem/network isolation, custody khóa, host capacity và provenance được kiểm chứng cho hình thức vận hành đó; cấu hình fixture hiện tại vẫn giữ HOLD cho nguồn thực.
3. Đặt ngưỡng trước khi mở lên 25–50 ID, đánh giá mức tăng TP so với FP, chi phí/lỗi đúng, thời gian và độ an toàn ở nhiều vòng. Mức 100–150 chỉ sau khi có bằng chứng lợi ích tăng thêm và đủ capacity. Chế độ 500 ID dùng cho release audit đủ điều kiện. Commercial GA tiếp tục NO-GO.

## Tiếp quản

Từ gốc repo dùng Python 3.12, Git và venv engineering với `engineering/airc500/requirements-pilot.txt`. Tái lập số liệu công bố theo [hồ sơ nghiên cứu](evidence/quality-v2/README.md). Chỉ lệnh `run` mới khởi động model.

```sh
python -m unittest discover -s engineering/airc500 -p "test_*.py" -v
python engineering/airc500/quality_study.py run --cohort marketing --server /path/to/approved/llama-server.exe --model /path/to/local/model.gguf --out .local/quality-new
python engineering/airc500/quality_study.py run --cohort identity --server /path/to/approved/llama-server.exe --model /path/to/local/model.gguf --out .local/quality-identity-new
```

Đầu ra giữ journal trong thư mục private và bản xuất gzip dùng cho replay. Với hồ sơ đã phát hành, lấy pin enrollment và index từ commit Git đã được review riêng (`test_quality_evidence.py`). Đối chiếu hai pin trước khi mở archive và tái dựng mọi request, receipt, lượt sửa kết luận và chỉ số; chỉ public key được công bố. Khi dùng bản Windows đã pin, executable + thư viện phải khớp manifest trước khi process được cấp quyền chạy. Tại thời điểm đóng băng hai cohort chính, trong workspace, Hugging Face cache, LM Studio và Ollama chỉ có checkpoint Qwen2.5-0.5B-Instruct Q4_K_M đã duyệt. Máy đo có 16 CPU logic, khoảng 15,8 GiB RAM và GTX 1660 SUPER 6 GiB. Các bảng cohort v2 chỉ dùng checkpoint đó; [phép so ghép cặp 0.5B và 1.5B](stronger/README.md) có enrollment, chi phí và tập con tám ca riêng. Giới hạn vận hành cho nguồn thực ghi trong tài liệu hardening. Rollback bằng dừng process, giữ archive và quay lại revision engineering trước đó; runtime/schema AMC độc lập với tool này.

## Truy vết tiêu chí phản biện

| Yêu cầu | Điểm kiểm tra và bằng chứng |
|---|---|
| B1. Finding theo phiên bản | `quality_eval.py` tạo history và bốn mốc chấm; raw response trong journal và trace gzip tái tạo được từ hai SHA. |
| B2. Chống thu hẹp coverage | `review_plan.py`, `Journal.start_planned`, `Journal.coverage_report` và test missing assignment/obligation, sai catalog, thiếu arbitration. |
| B3. Phân vùng tin cậy | [Quyết định runtime](RUNTIME-HARDENING.md), [phép thử Docker Linux](SANDBOX-CONTAINER.md), pin executable/DLL/GGUF, khóa adapter/verifier riêng; physical slot và process lifecycle test. |
| B4. Năm chế độ | `quality_study.py`, cùng holdout và hai seed, cùng số lượt blind; báo cost/time thực cùng giới hạn model. |
| B5. Corpus và cách chấm | 96 ca và cohort identity 16 ca; oracle, bộ chấm hướng sửa sáu field, Wilson 95%, kiểm thử nghịch đảo và phủ định. |
| B6. Mở rộng | Ở lại fixture khi trust hoặc quality chưa đạt. Điều kiện 25–50, 100–150 và full theo mục quyết định trên. |
| B7. Loop có giới hạn | `event_intake.py` xác thực sự kiện và head, gói việc cục bộ từ archive; quyền handoff bên ngoài phải cấp riêng. |

**Thử thách cho reviewer độc lập.** Chọn một true finding xuất hiện lần đầu sau blind, nếu có. Đối chiếu assignment, receipt, input scope, output nguyên bản và nguồn đã pin. Dùng ca phủ định có chứa đúng con số để thử chấm hướng sửa. Thu hẹp danh sách nghĩa vụ sau khi bắt đầu rồi kiểm tra evidence coverage có thực sự giữ số thiếu không.
