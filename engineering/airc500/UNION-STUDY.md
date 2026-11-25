# Kiểm định v3 · verifier độc lập và bằng chứng ba trạng thái

Trong 24 nghĩa vụ bắt buộc của bộ quảng cáo tổng hợp Meridian, bộ so sánh định kiểu đọc mọi giá, MOQ và cơ sở tính giá. Nó tự phát hiện lỗi và xác nhận giá trị khớp nguồn. Các reviewer chỉ nhận 12 nghĩa vụ ngữ nghĩa còn lại. Mỗi kết quả cuối giữ ID nghĩa vụ, đội tạo kết quả, nguồn, trạng thái và căn cứ. [Đo lường tại đúng enrollment](evidence/union-v3/REPORT.md).

## B1–B3 · Hợp nhất, độ phủ và thiết kế thí nghiệm

Nguồn và bản copy nằm trong hai commit Git tổng hợp. Sáu trong 12 ca định kiểu có lỗi, sáu ca sạch. Bốn miền ngữ nghĩa gồm đặt lịch, bảo quản, giao hàng và bảo hành. Mỗi miền có một lỗi, một ca sạch và một ca thiếu thông tin. Một bản ghi sản phẩm tương tự xuất hiện làm nguồn nhiễu. Model chỉ nhận phạm vi đã cấp. Answer key và đánh giá của peer được tách khỏi lượt mù. Đây là holdout mới tại thời điểm đăng ký, hiện được công bố để chạy hồi quy.

Bộ quét luôn đưa 12 kết luận typed vào kết quả. Với ca ngữ nghĩa, bộ xác minh kiểm ID nguồn, đúng đối tượng, quan hệ có căn cứ và verdict của từng đề xuất. Chỉ tập cách diễn đạt tương đương có sẵn trong fixture mới có thể làm chứng cứ độc lập. Các báo cáo trùng ID hợp nhất. Một ý kiến thiểu số đủ chứng cứ có thể được giữ sau phản biện. Lịch sử đề xuất ban đầu nằm trong journal ký. Dữ liệu ngoài phạm vi và trường hợp không có đề xuất đủ căn cứ nhận trạng thái `unresolved`.

- `verified_defect` cần căn cứ cho một sai lệch. `verified_clean` cần căn cứ cho đúng claim, đúng sản phẩm. Thiếu cờ hoặc chỉ có đồng thuận vẫn có thể là `unresolved`.
- Mỗi domain và mức độ nghiêm trọng có số ca theo cả ba trạng thái. Còn thiếu một nghĩa vụ bắt buộc thì release là `inconclusive`.
- Với ca typed, verifier tạo đủ actual, expected và sửa đổi. Với ca ngữ nghĩa, model chọn operation và bản ghi nguồn. Bộ xác minh điền giá trị thực và giá trị chuẩn từ dữ liệu đã pin. Ghi riêng sửa bằng code, đề xuất kết hợp và bản sửa hoàn chỉnh do AI tự viết. Wire v3 không yêu cầu model viết toàn văn thay thế, nên số sửa đầy đủ do AI tự viết bằng 0.

Qwen 0.5B chạy hai seed 19/47. Chỉ một yếu tố thay đổi trong mỗi phép so mù. Hai lần của cùng reviewer và hai reviewer khác nhau chia sẻ lượt đầu, cùng số request, scope, seed của lượt hai và trần output. Nhánh thêm chỉ dẫn đọc nguồn giữ nguyên reviewer, model, số lượt và tập ca. Nhánh chia batch từ 6 thành 3 giữ cùng tổng trần output nhưng thêm phần đầu prompt. Phép so model chỉ thay checkpoint trên hai batch gốc. Bộ prompt xoay thứ tự của verdict, nguồn, lý do, thao tác theo ca và seed, đồng thời xen kẽ dạng record và listing. Trình bày rõ sai số do cùng template, một host, cùng dữ liệu qua nhiều seed và số mẫu nhỏ. So sánh vai trò bao gồm thay đổi chỉ dẫn chuyên môn của vai trò. Thời gian thực khi hai process chạy song song chịu ảnh hưởng tải máy.

Hai vòng bổ sung kiểm tra toàn bộ tập ngữ nghĩa nhỏ đã chọn, một lần challenge và một lần arbitration. Họ đọc các ý kiến ký của đúng ca từ các assignment trước. Điểm thô cho nhiều lượt dùng cùng quy tắc đồng thuận hoặc abstain. Phép hợp nhất cuối kiểm từng đề xuất theo chứng cứ. Thí nghiệm chưa đo tranh luận tự do, lỗi Marketing ngoài từ vựng tổng hợp hoặc ca do người làm Marketing gán nhãn.

## B4–B5 · Năng lực và ranh giới tin cậy

GGUF chính thức SmolLM2-1.7B-Instruct Q4_K_M có SHA-256 `decd2598bc2c8ed08c19adc3c8fdd461ee19ed5708679d1c54ef54a5a30d4f33`, 1.055.609.536 byte, revision `2d4a76a30b4af41ecd395c35725ac11688d4cfe4`. Hai Qwen dùng đúng revision và digest của study #20. Các file trọng số chỉ nằm trên máy của operator. Phiên đo trả 0 phí API. Đọc thời gian, throughput, RSS peak của process, VRAM đã lấy mẫu và lỗi request theo model trong report. Giá trị VRAM của toàn GPU gồm cả ứng dụng khác. Nếu driver không cấp counter theo process, giá trị là null. [Publisher model artifact](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF/blob/2d4a76a30b4af41ecd395c35725ac11688d4cfe4/smollm2-1.7b-instruct-q4_k_m.gguf).

Admission v2 chỉ chấp nhận đúng Git fixture, catalog, scope từng obligation, principal, key/model, runtime manifest và tool grant. Broker tái tạo exact template và chỉ bổ sung phần phản hồi đã ký của peer cùng scope. Digest context và principal phải khớp khi cấp lease. Kiểm tra lại các ràng buộc đó khi replay. Run thật giới hạn concurrency 1/run, tổng 2 process/máy; timeout 180 giây, 0 retry, 55 phút, 90.000 token cho primary và 12.000 cho từng checkpoint phụ. Các release archive trước tiếp tục dùng wire đã ký ban đầu.

Các số liệu cuối được tái lập ngoài model process rồi ký bằng khóa verifier riêng, với public fingerprint trong source đã review. Các vai trò native còn dùng chung OS principal. Trước khi xử lý repository thật cần credential custody riêng, scoped read-only source và cô lập network/filesystem cho chính model runtime. Phép thử Docker Linux ở #20 chỉ xác nhận worker xác định của fixture đó. Nguồn repository thật tiếp tục HOLD.

## B6 · Generation và outbox cục bộ

`event_intake.py` xác thực từng delivery rồi đối chiếu trạng thái PR, SHA nguồn/đích và branch đích. Mỗi chuyển đổi thực tạo generation mới. Reopen hoặc retarget cùng SHA vẫn fence gói cũ. A → B → A giữ nguyên giới hạn hai chu kỳ sửa và deadline. Ticket v1 đã tồn tại cần event mới để vào generation có quyền handoff. Mỗi generation ghim exact plan và package index/trust ngoài archive. Trước và sau replay, bước tạo draft kiểm lại generation. Chỉ finding đã xác minh, có hành động được đối chiếu với nguồn mới trở thành assignment, kèm gap còn mở. Gói lịch sử #17 đã đo 0 sửa actionable nên trả 0 assignment, các gap còn truy được. Archive v3 chọn nhánh q05/full_union seed 19 cố định.

SQLite commit draft một lần theo generation và key nội dung. Sau crash, gọi lại `handoff` với cùng delivery để lấy lại gói pending và key. Lệnh `ack --outbox-key KEY` trên cùng delivery lưu đúng một xác nhận có thể gọi lặp. Head đổi, hết deadline hoặc PR đóng sẽ chặn ACK cũ. Lệnh chỉ ghi cục bộ, không gửi dữ liệu cho Codex hoặc GitHub. Lấy repository thật qua adapter metadata chỉ đọc. Nếu receiver bỏ mất toàn bộ một chuỗi chuyển đổi và nguồn metadata không phát lộ thay đổi, SHA hiện tại đơn lẻ không thể chứng minh lịch sử; trước external handoff cần reconcile timeline có generation từ provider.

## B7 · Research Broker

Chạy `python engineering/airc500/research_cards.py offers` hoặc dùng topic `market`. Broker chỉ đọc thẻ nguồn công khai đã chọn cùng câu hỏi qualification. Dùng `--answers FILE` để so từng lựa chọn nguồn/quyết định. Ví dụ merchant thảo luận về bán theo lô chỉ tạo câu hỏi về MOQ của một người bán khác. Dữ liệu điều tra thị trường cần đúng phạm vi mẫu. Các thẻ không xác nhận claim riêng của khách, không truy cập repository riêng và không thêm nội dung web vào prompt của nghiên cứu đã đóng băng. Chưa đo cải thiện năng lực từ việc đọc các thẻ.

- Google mô tả thời hạn áp dụng giá khuyến mãi. [Merchant Center](https://support.google.com/merchants/answer/6324460?hl=en)
- Shopify mô tả tách số đo sản phẩm và cơ sở tính giá để hiển thị unit price. [Shopify Help Center](https://help.shopify.com/en/manual/products/details/product-pricing/unit-pricing)
- Một merchant muốn phân biệt giá theo chai, giá theo gói và số lượng đặt theo lô. Đây là câu hỏi thực hành cho reviewer. [Shopify Community](https://community.shopify.com/t/sell-products-with-minimum-quantity-and-increment-quantity-with-fixed-number-of-units/39933)
- Cần xem xét tổng thể mẫu và độ bất định trước khi suy diễn từ thống kê doanh số thương mại điện tử của Hoa Kỳ. [U.S. Census Bureau methodology](https://www.census.gov/retail/ecommerce/how_surveys_are_collected.html)

## B8 · Điều kiện đề xuất trước mỗi bước mở rộng

| Quy mô thử | Điều kiện cần đo trước khi cấp |
|---|---|
| 25–50 | Bảo toàn 100% finding typed và fixture permissions qua hai đợt. Trên holdout mới có nhãn nghiệp vụ độc lập, mỗi miền cần tối thiểu 35 ca sạch và 35 ca lỗi, cận trên Wilson 95% FPR ≤ 10%, cận dưới Wilson 95% cho tỷ lệ sửa dùng được ≥ 70%, và cải thiện ít nhất 10 điểm phần trăm recall đã xác minh của ca ngữ nghĩa ở cùng ngân sách. Tất cả P0/P1 bắt buộc có evidence. |
| 100–150 | Lặp lại mức trên ở ít nhất ba campaign tách biệt, tăng ≥ 5 điểm phần trăm recall đã xác minh so với 25–50, chi phí/true finding không tăng hơn 20%. Cần rehearsal cancellation, resource exhaustion, late usage và zero external write theo đúng runtime sẽ dùng. |
| 500 | Dùng cho release audit đã được owner duyệt ngân sách và phạm vi. Chứng minh đủ capacity, độc lập principal/nguồn, đủ coverage bắt buộc, quá trình xử lý dissent và đường rollback trong rehearsal đầy đủ. |

Registry vẫn có đúng 500 hồ sơ. Đợt đo này không cấp quyền mở rộng, không triển khai chức năng AMC. Commercial GA tiếp tục NO-GO.

## Tái lập và rollback

Từ gốc repo với Python 3.12, Git và venv đã cài `engineering/airc500/requirements-pilot.txt`:

~~~sh
python engineering/airc500/union_release.py
python -m unittest discover -s engineering/airc500 -p "test_*.py" -v
python -m unittest discover -s engineering/airc500/stronger -p "test_evidence.py" -v
~~~

Để chạy inference mới, dùng đường dẫn public/private mới, giữ private key ở ngoài checkout, ghi pin trả về từ enroll trước khi gọi model. Ba tên label là `q05`, `q15`, `smol`. Operator chạy mỗi label một lần. `replay` không cần model hoặc mạng.

~~~sh
python engineering/airc500/union_study.py enroll --out PUBLIC_DIR --private PRIVATE_DIR
python engineering/airc500/union_study.py run --out PUBLIC_DIR --private PRIVATE_DIR --pin PIN --label q05 --binary LLAMA_SERVER --weight Q05_GGUF
python engineering/airc500/union_study.py run --out PUBLIC_DIR --private PRIVATE_DIR --pin PIN --label q15 --binary LLAMA_SERVER --weight Q15_GGUF
python engineering/airc500/union_study.py run --out PUBLIC_DIR --private PRIVATE_DIR --pin PIN --label smol --binary LLAMA_SERVER --weight SMOL_GGUF
python engineering/airc500/union_study.py replay --out PUBLIC_DIR --pin PIN
~~~

Rollback bằng ngừng launcher/inbox và xác nhận model process đã thoát. Giữ bản SQLite trước nâng cấp cùng receipt, outbox và archive. Nếu quay lại runtime cũ, dùng bản inbox trước nâng cấp trong thư mục riêng; ticket/generation v3 đang pending cần tái đối soát trước bất kỳ retry. Không có migration sản phẩm.
