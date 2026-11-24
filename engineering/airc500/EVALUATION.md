# Kế hoạch kiểm thử và hiệu chuẩn

## Các phép kiểm tra chạy được ở giai đoạn thiết kế

Từ thư mục gốc, chạy hai lệnh trong [hướng dẫn tiếp quản](README.md#tiếp-quản-trên-máy-mới). Bộ unittest kiểm phân bổ, ID, rubric, quyền, hợp đồng của các reviewer và khả năng phát hiện catalog bị lệch. Bộ chấm minh họa trong [calibration.py](calibration.py) chỉ nhận bộ đơn vị đã phân xử. Có thể chạy trực tiếp `python engineering/airc500/calibration.py`. Hai tập [fixture tổng hợp](fixtures/units.json) và [đáp án cho self-test](fixtures/scoring-example.json) là dữ liệu công khai của test. Output dùng để kiểm số học; không có kết quả invocation để suy ra chất lượng hội đồng.

Kiểm cấu trúc wire contract theo JSON Schema Draft 2020-12 trong venv engineering tách khỏi ứng dụng:

```sh
python -m pip install "jsonschema==4.25.1"
python -m unittest discover -s engineering/airc500 -p "test_wire.py" -v
```

## Đơn vị chấm và nhãn

Workflow [AIRC design contracts](../../.github/workflows/airc-design.yml) chạy lại catalog và hai bộ unittest khi PR chạm thư mục tooling hoặc chính workflow. Job dùng quyền đọc và dữ liệu tổng hợp. Bộ test runtime AMC tiếp tục dùng cấu hình hiện hữu.

Đóng băng casebook, SHA và tập các cặp `case × invariant` trước khi chạy. Mỗi đơn vị có nguồn oracle, nhãn present/absent, severity nếu có và provenance. Tập hợp phải có ca sạch và ca lỗi cùng hình thức, lịch sử regression đã xử lý, khác biệt Agency/In-house, quyền, chi phí và Content/SEO. Fixture tổng hợp công khai chỉ dùng kiểm harness. Với pilot đánh giá chất lượng, tách development/holdout theo họ regression và campaign, so digest để tránh trùng. Broker không phát answer key, expected labels hoặc trạng thái trước/sau sửa cho reviewer. Sau blind seal, verifier độc lập match finding tới unit theo nguyên nhân và observable effect; lưu bản đồ match và quyết định về duplicate. Finding mới ngoài oracle có thể được xác minh riêng; chỉ thay đổi tập nhãn ở phiên bản corpus tiếp theo.

Cho mỗi nhãn ghi `deterministic_fixture`, `historical_regression`, `human_domain` hoặc `ai_adjudicated`, cùng reviewer/nguồn nhãn và mâu thuẫn. Báo riêng chất lượng theo từng nguồn. Ở thời điểm thiết kế chưa có ground truth nghiệp vụ độc lập cho bộ 24 ca Content/SEO trước đây. Báo cáo PR #14 ghi 18 trùng, 15 thừa, 22 sót theo nhãn AI: precision 54,5%, recall 45,0% cho QA v2 ở phép so đó. Không chuyển số liệu lịch sử này sang AIRC. [Hồ sơ gốc](../../docs/reviews/ai-panel-20261124/README.md)

| Chỉ số | Cách tính và mẫu số |
|---|---|
| Precision và recall | TP/(TP+FP), TP/(TP+FN), khử trùng theo unit; công bố cả TP, FP, FN |
| False-positive rate | FP/(FP+TN) trên tập unit âm xác định trước, có ca sạch |
| Critical defect detection | Số unit P0/P1 thật tìm đúng / tổng unit P0/P1 thật, báo riêng từng severity |
| Evidence validity | Số candidate có locator, provenance và đối chiếu hợp lệ / số candidate đã kiểm evidence; nêu số chưa được kiểm |
| Duplicate rate | Số candidate bổ sung cùng nguyên nhân / tổng số candidate đã phân cụm |
| Actionability | Số verified finding có owner, hướng sửa, criterion quan sát được và regression khả thi / số verified finding đã thẩm định |
| Cost per verified finding | Tổng chi phí đã đối soát của run / số verified finding duy nhất; dư uncertain báo bằng khoảng, chưa đo thì N/A |
| Phát hiện lỗi implementer bỏ sót | Giao của TP với known defects còn thiếu trong baseline implementer niêm phong trước review / số known defects bị baseline bỏ sót; luôn báo cả số tuyệt đối |

Mẫu số bằng 0 trả N/A. Report số đếm, nguồn nhãn, phạm vi, micro theo unit, macro theo discipline khi đủ mẫu, khoảng tin cậy và phần chưa đo. So sánh cùng holdout/budget giữa một reviewer, targeted và full. Chạy nhiều seed theo family; tách hiệu quả độc lập theo model ra khỏi lặp lại cùng checkpoint. Ngưỡng pilot đề xuất: phát hiện đủ P0 đã cài, FPR ≤10% trên tập sạch đủ lớn, ≥95% candidate được kiểm evidence có nguồn hợp lệ. Nếu có dưới 30 unit âm hoặc dưới 10 positive severity cao, chỉ báo kết quả mô tả. Các ngưỡng này cần owner phê duyệt và hoàn toàn riêng với release gates thương mại.

## Ma trận nghiệm thu runtime đề xuất

| Ca | Quan sát chấp nhận |
|---|---|
| A01 PR bị cập nhật trong lúc review, file rename/delete | Pin hai SHA và side; run cũ superseded; số dòng resolve được từ đúng blob |
| A02 routing theo dependency và risk | Hai PR cùng số dòng nhưng tác động khác nhận coverage khác; unknown path tạo gap rõ ràng |
| A03 độc lập tác giả, mù và niêm phong | Không thể self-review hoặc đọc peer trước barrier; output ban đầu giữ nguyên sau rebuttal |
| A04 authority và proof | Receipt thiếu/sai key, sai model revision, output digest hoặc repo không được tính; completed rỗng có scope vẫn hợp lệ |
| A05 trao đổi và gộp | Request evidence, object, propose alternative, corroborate và refer có trace; duplicate giữ ID; hai root cause riêng không gộp |
| A06 dissent / arbitration | Một quan sát tin cậy thắng đa số; hòa chứng cứ kết thúc unresolved và có người tiếp quản; round luôn có trần |
| A07 budget và tải | Tranh reservation cuối, thử vượt token/tiền/slots; paid cap 0 không route ra paid adapter; full thiếu ngân sách dừng tại admission |
| A08 retry, timeout, cancel và checkpoint | Crash trước/sau dispatch, receipt trễ, journal lặp, cancel khi in-flight; không thanh toán hai lần hoặc tái mở barrier |
| A09 sandbox và ACL | Fixture hai khách cùng agency, hai tenant, hai run, marker bí mật tổng hợp; broker, trace và report chỉ lộ dữ liệu được cấp |
| A10 source/label integrity | Trộn snapshot hoặc lộ answer key bị phát hiện; URL đơn lẻ không xác minh được finding; nhãn AI và nhãn nghiệp vụ báo riêng |
| A11 full-council | 490 initial + 10 trọng tài có receipt thật; đếm riêng 500 ID, attempts và family; reviewer thiếu/timeout dẫn đến incomplete |
| A12 báo cáo và bàn giao | Tái tạo report từ journal đã pin cho cùng digest; đủ 15 mục, quyết định và test có thể giao, mọi gap/dissent còn nguyên |
| A13 phục hồi và rollback | Khôi phục backup + journal trên máy sạch; chữ ký, CAS, mở reservation, deadline và cancel epoch nhất quán |
| A14 fixture nghiệp vụ | Claim nguồn/bản sao, CTA thiếu điều kiện, KPI sai đơn vị, charge trùng và đối chứng sạch phân biệt bằng oracle |
| A15 cô lập roadmap | Khởi động và chạy bộ test AMC khi tooling vắng mặt; product schema, runtime registry và quyền reviewer tách biệt |

Mỗi ca runtime cần lưu fixture digest, SHA phần mềm, policy, environment, expected, actual, log đã lọc và verifier. A01–A15 là kế hoạch nghiệm thu, chưa phải chứng nhận hệ thống đã vận hành. Không mở gate vì một ca DTO hợp lệ hoặc vì có 500 dòng trong catalog.

**Đề bài cho người review thiết kế.** Chọn một finding đúng nhưng thiểu số trên cùng một checkpoint; yêu cầu truy ngược đến nguồn và chỉ ra trạng thái nếu nguồn bị thu hồi. Chọn lần ngắt sau dispatch, trước receipt; kiểm xem tiền và số reviewer tham gia còn có thể bị đếm sai ở bước nào.
