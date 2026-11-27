# AMC-AI-RS-01 · Kết quả sau chấm mù

**Quyết định: giữ WF-03 hiện hành.** B chỉ giảm số trường cần sửa ở 1/4 cặp, trong khi protocol yêu cầu ít nhất 3/4. Cả bốn bản B còn bỏ sót ràng buộc. Independent AI Reviewer đánh giá cả tám hồ sơ đều cần biên tập trước khi sử dụng. Chưa có nghiệm thu practitioner hoặc số phút biên tập thực đo.

## Kết quả theo cặp

Nguồn điểm là phiên `AMC-AI-RS-01-BLIND-REVIEW-20261127-01`. Sau khi ghép từng case với khóa đã cam kết, cả bốn vị trí Left là A và Right là B. Đây là kết quả của bốn lần gán vị trí riêng; thứ tự **chạy** có hai cặp A trước và hai cặp B trước. Việc cả bốn cặp có cùng vị trí trình bày khiến nghiên cứu này không tách được ảnh hưởng của vị trí khỏi ảnh hưởng của nhánh.

| Brief | A /12 | B /12 | Trường sửa A | Trường sửa B | Phán xét chính từ phiếu khóa |
|---|---:|---:|---:|---:|---|
| Tile | 6 | 5 | 6 | 6 | B mở rộng yêu cầu duyệt phần hao hụt sang cả diện tích phủ của một thùng. A giữ điều kiện nguồn trong Research. |
| Delivery | 4 | 7 | 6 | 4 | A thêm bảo đảm giao hàng thiếu căn cứ. B đưa ra positioning dùng được và lý do mang tính giả thuyết; vẫn thiếu cách đo đầy đủ. |
| Counter | 3 | 6 | 7 | 7 | B nhận diện đúng người mua hơn, nhưng lặp lại sở thích chưa được chứng minh. A nhầm bối cảnh làm việc với phân khúc. |
| Check | 4 | 6 | 6 | 6 | B nhận diện đúng chủ thể. Cả hai còn thiếu phương án so sánh có thể sử dụng và điều kiện đo của thử nghiệm. |
| **Tổng** | **17/48** | **24/48** | **25** | **23** | B thắng/hòa/thua theo số trường sửa: **1/3/0**; theo điểm rubric: **3/0/1**. |

Từng trường sửa chỉ tính một lần trong mỗi vai trò và dossier. Hai trường chênh lệch ròng đều đến từ Delivery. Điểm rubric cao hơn ở ba cặp chưa đạt tiêu chí chính đã đăng ký. [Phiếu gốc, gồm dẫn chứng và cách sửa từng trường](AMC-AI-RS-01-SCORES-LOCKED.json) · [Kết quả có thể tái tính](FINAL.json)

| Tiêu chí, mỗi nhánh tối đa 8 điểm | A | B |
|---|---:|---:|
| Phân khúc và người quyết định | 4 | 8 |
| Dữ kiện, quan sát và giả thuyết | 3 | 3 |
| Câu hỏi nghiên cứu và bằng chứng còn thiếu | **1** | **1** |
| Positioning, rationale và hướng hành động | 3 | 4 |
| Hành động và cách đo | 4 | 4 |
| Nhất quán giữa Research, Strategy và brief | 2 | 4 |

| Loại nhận xét | A | B | Đơn vị |
|---|---:|---:|---|
| Trực tiếp trái nguồn | 0 | 0 | Dossier có cờ theo reviewer |
| Sai thẩm quyền | 0 | 0 | Dossier có cờ |
| Đổi điều kiện thương mại hoặc dịch vụ | 1 | 1 | Delivery A, Tile B |
| Mất ràng buộc quan trọng | 4 | 4 | Dossier có cờ, đặc biệt cửa sổ đo, eligibility hoặc deduplication |
| Nhận định thiếu căn cứ | 5 | 3 | Mục ghi trong phiếu, xuất hiện ở 4 dossier A và 3 dossier B |

Các cờ có thể cùng xuất hiện. Reviewer ghi riêng một nhận định thiếu căn cứ với một phát biểu trực tiếp trái nguồn. Trong ba điều kiện đã khóa, điều kiện về số trường sửa và điều kiện giữ ràng buộc đều trượt; cờ trái nguồn bằng nhau. Kết luận chỉ áp dụng cho bốn brief tổng hợp, một model, một cách kết hợp hướng dẫn B và một người chấm AI.

## Đối chiếu evidence

1. Protocol, packet, schema, seed, giới hạn và commitment được ghim trước inference tại `47b7b9633e44e5d25162fa560b366ab8cfaaeb72`. Candidate mù là `ef158fac6ea634c7f415fd3a608cbce0e100db9a`. [Lock](LOCK.json) · [Manifest vòng mù](MANIFEST.json).
2. SHA-256 trên byte gốc phiếu điểm là `da97785dc1bc9850021b35c9ea101267db7c8c53c6cf4276cced66517da54bec`. Đã đọc lại cùng byte từ [commit nhận điểm trên GitHub](https://github.com/datnv41001/ai-company/blob/2dca5fcc0470bd25ed9e17d581df34d3ea5ee400/docs/evaluation/rs01/AMC-AI-RS-01-SCORES-LOCKED.json) trước khi giải mã archive hoặc đọc mapping ở vòng này. Reviewer xác nhận đã khóa điểm trước khi xem phân nhánh.
3. Đã kiểm tag xác thực AES-GCM của archive cũ, rồi so SHA-256 ZIP rõ với hash công bố trước reveal: `4797e2e0d84498c25a25bdc6faa84217ad08511fff20ebeb4724742565db1ef4`. Dùng `mapping.json` trong ZIP, tính SHA-256 trên UTF-8 JSON sắp key, đóng gói gọn, gồm nonce; kết quả `2c84174c06f805b4823a40e5adadcc4293d77295c3d954c0fe849cf30dba6b6a` khớp LOCK. ZIP chứa 75 mục, gồm intent, raw và receipt cho 24 lượt, mapping, marker khởi động và journal. Không cần khóa giải mã để reviewer đọc bản đã mở. [Ordered evidence](ordered-evidence.zip).
4. Bộ kiểm dựng lại 24 request qua adapter đã khóa với nguồn, facts, qualifiers và measurement contract của cùng packet. A dùng request gốc; B chỉ sắp lại trường context và thêm hướng dẫn chung. Các bước sau nhận output đầu tiên của đúng nhánh. So toàn bộ request, schema, seed 42, temperature 0, model alias và nội dung phản hồi đầu với tám hồ sơ mù. Digest GGUF được đo ở preflight là `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`; raw responses ghi alias của runner. Cả tám chuỗi đủ ba bước; không retry, không có output bị thay.
5. Backend ghi **13.627 token vào**, từng lượt 362–794 (cap 1.500); **2.518 token ra**, từng lượt 57–179 (cap 220). Cả 24 phép đếm input khớp preflight thực tế, tổng nằm dưới 36.000/5.280. Journal ghi **128,031 giây** từ đầu thực thi tới đóng vòng, phản hồi cuối ở giây 127,985; trần 1.800 giây. Phí dịch vụ model USD 0; chi phí máy, điện và lao động chưa được đo. Không cộng thời gian tải model hoặc đóng gói vào thời gian thực thi.
6. Từ checkout của PR có dependencies dự án, chạy `python tests/evaluation/rs01_final.py` để tái tính và so FINAL.json, hoàn toàn offline. So diff với main `a6fa1976f9a5d4557a4e3b64ac28dec2eb0fc0a4` để kiểm phạm vi. [Manifest vòng cuối](FINAL-MANIFEST.json).

## Đề xuất nghiên cứu kế tiếp · chưa cấp quyền chạy

Trong Tile B, một điều kiện duyệt bị gán nhầm đối tượng. Trong cả tám hồ sơ, mô tả đo lường bỏ mất một phần nghĩa vụ. Ngay cả khi bảo toàn hoàn hảo các trường đó, Research vẫn phải đưa ra câu hỏi có thể phân xử giữa các giả thuyết: cả A và B chỉ đạt 1/8 ở tiêu chí này.

| Thành phần có sẵn ở baseline #64 | Câu hỏi nên thử trước khi đề xuất sửa runtime |
|---|---|
| [Projection theo revision và quyền](../../../app/c3_projection.py) kiểm nguồn đủ điều kiện, giữ wording, qualifiers và measurement contract; [role view](../../../app/c3_releases.py) cấp phần measurement phù hợp cho vai trò nội bộ. | Với fixture tổng hợp mới chưa công bố, một bản hiển thị lấy trực tiếp điều khoản, event, eligibility, window và quy tắc dedup từ projection sẽ bảo toàn được bao nhiêu nghĩa vụ? So từng giá trị, scope, revision; thử cả nguồn thiếu hoặc hết quyền. |
| [Adapter kỹ năng và validation](../../../app/c3_skill_library.py) đã có schema, trường chuyên môn và source handles; dấu nguồn hợp lệ chưa kiểm được chất lượng lập luận. | Để model tập trung vào chủ thể quyết định, giả thuyết, câu hỏi có thể bác bỏ, bằng chứng còn thiếu và lý do chọn phương án. Chấm xem bằng chứng đề nghị có làm thay đổi quyết định không. Theo dõi riêng mọi mâu thuẫn giữa văn bản model và dữ kiện kế thừa. |
| [Handoff /2](../../../app/c3_strategy_handoff.py) giữ brief và hướng dẫn phát hành, measurement status và authority theo recipient. | Dùng cơ chế bàn giao hiện hữu để trình bày dữ liệu đã được phép cùng diễn giải. Thử nghiệm phải chặn rò rỉ nguồn nội bộ, phân biệt định nghĩa KPI với kết quả đã đo và không mở quyền hành động mới. |

Đề xuất trước mắt là so sánh cách bàn giao này bằng fixture mới và rubric khóa trước, đo riêng lỗi nghĩa vụ xác định, chất lượng câu hỏi/rationale và số trường người nhận cần sửa. Bốn ca RS-01 chỉ còn phù hợp làm regression công khai. Cần quyết định riêng về protocol, người chấm và ngân sách trước inference mới. Chưa triển khai kiến trúc đề xuất, chưa promote B, chưa có BUSINESS_VALIDATED. Production và Commercial GA vẫn NO-GO.
