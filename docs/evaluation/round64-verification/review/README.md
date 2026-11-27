# Bàn giao Research → Strategy → Content trong Studio

Người phụ trách Marketing cần biết có thể giao Content soạn gì, cho ai, dùng câu chữ nào và trên kênh nào. Lát cắt này phục vụ một commission **in-house** với nguồn tổng hợp. Nó kết thúc ở việc chuẩn bị bản nháp trong AMC. Quyết định phát hành, quyền dùng creative hiện hữu, ngân sách và phép đo hiệu quả cần thẩm quyền riêng.

## Từ brief đến người nhận

1. Director phân công WF-03 @3 cho Research/Strategy @4 theo brief, snapshot và manifest được chốt. Worker chỉ nhận projection theo vai trò. Checkpoint giữ lại đề xuất ban đầu.
2. Trong Marketing Studio, editor đối chiếu nguồn rồi lưu các nhóm nội dung. Đổi Research hoặc Strategy tạo revision mới. Claim gate, signoff từng nhóm và QA cuối kiểm revision cùng digest của bản khách có thể xem.
3. Sau QA, người có quyền và mandate hiện hành mở phần bàn giao trong cùng Studio. Người này ghi tình huống mua, đối tượng, giới hạn mẫu, nhận định, đoạn nguồn có thể đối chiếu, nguồn sản phẩm riêng, ý kiến trái chiều và quyết định. Mỗi phương án có trade-off. Mẫu tiếp cận nhỏ chỉ cho phép diễn giải trong phạm vi đã ghi.
4. Cặp phương án và placement xác định loại bản mới có thể giao. Với thẻ tại quầy, người phụ trách phải chọn loại thẻ phù hợp. Tài sản cho product page giữ quyền sử dụng riêng. Khi thiếu dữ kiện/quyền, đọc lý do, người chịu trách nhiệm, phần được chuẩn bị nội bộ và điều kiện để tiếp tục.
5. Người nhận được chỉ định mở Studio bằng tài khoản của mình. Họ nhận mục đích, đối tượng, câu chữ sản phẩm được phép, giới hạn và điều kiện QA của bản nháp. Bằng chứng nguồn hạn chế và thảo luận thượng nguồn dành cho người có quyền đối chiếu. Measurement ở trạng thái lập kế hoạch. Không có thao tác phát hành, chi tiền, cập nhật CRM hoặc thực thi thử nghiệm ở luồng này.

## Vì sao quyết định nằm sau Studio

Trong DAG đã phát hành, worker Strategy đọc đầu ra Research của cùng lượt chạy trước khi editor vào Studio. Quyết định bàn giao đọc bản Research **và** Strategy sau biên tập, cùng signoff và QA của revision hiện hành. Nó không thay đổi những gì worker Strategy đã đọc hoặc tái chạy model. Bước bàn giao dùng hợp đồng staff riêng `amc.internal-strategy-handoff/1`, ghi biên nhận restricted vào kho lệnh tri thức hiện có. Trên lần nhận lại, backend kiểm authority và provenance; quyết định đã lưu có thể đối chiếu theo revision. Scope, khóa giao dịch và policy QA được kế thừa.

Registry và các release WF-03 @1/@2/@3 vẫn là hợp đồng gốc. So sánh Git của `catalog/` với parent, các test fingerprint, historical replay và manifest xác nhận ranh giới versioning. Runtime lock ghi nhận mã ứng dụng mới. Schema core v26, bảy lớp, 49 module, 37 vai trò, 24 workflow mẹ và roadmap P00–P12 tiếp tục áp dụng.

## Hai finding và ranh giới kiểm chứng

Nguồn của quan sát phải xuất hiện ở span đã xác minh hoặc đã được người có mandate chấp thuận trong `studio.research.buyer_problem`. Dữ kiện sản phẩm phải được chấp thuận riêng ở `studio.strategy.positioning`. Biên nhận giữ span ID, claim/source revision, locator và đoạn trích. Đổi hai nguồn cho nhau hoặc chọn một nguồn cùng manifest nhưng chưa dùng ở trường tương ứng đều giữ việc. Với phạm vi hiện tại, người nhận Content phải là owner/admin đã có quyền đọc commission hạn chế, khác người quyết định và tác giả. Việc hợp lệ cho người nhận khác chức danh này cần thiết kế quyền riêng.

| Finding | Hành vi cũ | Cách kiểm ở runtime |
| --- | --- | --- |
| AMC-R63-01 | Đổi kênh hợp lệ sang thẻ tại quầy vẫn giao hình minh họa dành cho product page | Cùng phương án, thay placement hoặc chọn sai loại tài sản phải giữ việc. Giao được một bản mới khi nguồn, người nhận, QA và loại thẻ khớp. |
| AMC-R63-02 | Workpaper có dữ kiện trong JSON nhưng người nhận chủ yếu thấy “hold” | Kiểm nội dung hiện trực tiếp trong Studio bằng Chromium ở ba độ rộng, hai theme, thao tác bằng bàn phím, trạng thái lỗi và phiên riêng của người nhận. |

Ca RED trên main ghi nhận một claim sai có source ID hợp lệ đã vào checkpoint/staff composition. Cổng evidence của nhóm và QA cuối đã trả 409. Quyết định bàn giao dùng lại các cổng này. Digest xác nhận nội dung đang xét; người được ủy quyền chịu trách nhiệm về chủ thể, diễn giải và giới hạn mẫu. [Biên nhận trước sửa](BASELINE-63.json) · [Các phương pháp nghiên cứu đã áp dụng](METHODS.md)

## Chạy lại trên máy khác

Dùng bản checkout theo head trong draft PR và PostgreSQL thử nghiệm riêng (role ứng dụng, RLS và migration như CI). Cài dependency phát triển và Chromium theo [hướng dẫn PostgreSQL trên Windows](../../../README.md) và [bàn giao Docker](../../../HANDOFF.md) và bước `api-tests` trong [.github/workflows/ci.yml](../../../.github/workflows/ci.yml). Dùng fixture tổng hợp. Từ gốc repository:

```sh
python -m pytest -q --junitxml=api-regression.xml
python -m pytest -q tests/browser_strategy_handoff.py --junitxml=browser.xml
```

Đặt `AMC_RUNTIME_STRATEGY_EVIDENCE` và `AMC_STRATEGY_UI_EVIDENCE` về hai thư mục kết quả riêng để lưu biên nhận và ảnh. Mở `lineage.json` trong thư mục đầu, dùng brief ID, manifest, run ID, document ID, revision, digest và receipt để tra một đường đi. Hai campaign có cùng tên vẫn là hai scope khác nhau. Khi bản đã xem hết hạn, tải lại trước khi ghi quyết định. Nâng cấp và rehearsal khôi phục thực hiện theo job API trên database dùng một lần.

## Đọc bằng chứng và quyết định còn mở

Đối chiếu từng điều kiện và các lần thử chưa đạt trong [ma trận 18 điều kiện](ACCEPTANCE.md).

- [Chứng nhận main #63](MAIN-63.json) gồm hai parent, tree, CI sau merge, JUnit và kết quả kiểm ZIP gốc.
- Gói bằng chứng trên draft PR chứa JUnit head/trial, ca bị giữ, ảnh UI, biên nhận phân quyền, đề xuất gốc, phần editor sửa, quyết định QA và dữ kiện được giao. Các session fixture đóng vai nhân sự thử nghiệm. Lượt model thực trong CI có job, checkout và artifact riêng. Chỉ đối chiếu token ở những bước có telemetry.
- `actual-model.json` trích phản hồi thật của các lượt WF-03 @3 trong CI chuẩn. `model-resources.json` liên kết artifact gốc, attempt, wall time của job, usage có thể đếm và outcome của smoke cũ @1. Phí model loopback và tiền GitHub Actions là hai khoản riêng; hóa đơn runner và công lao động chưa có. Giới hạn budget trong fixture chỉ dùng để kiểm ledger.
- Người duyệt chọn người nhận theo role và ID thành viên trong workspace thử nghiệm. Chưa có kiểm chứng khả năng nhận biết người nhận đúng từ danh sách đông thành viên bởi practitioner.
- Khôi phục bằng cách quay lại bản ứng dụng đã chứng nhận trên schema v26, giữ nguyên receipt lịch sử. Không cần xóa dữ liệu. Trước khi áp dụng rollback ngoài môi trường thử nghiệm, operator đối chiếu app/runtime lock và chính sách phát hành của workspace.
- O-09 vẫn đợi custodian và vault, 12 họ/24 thẻ chưa niêm phong và chưa chạy. R62-02 cần giải quyết trước khi khóa cohort. Practitioner pilot /2 chờ người thật, consent, vault, nguồn AI và hạn mức chi phí; tám work order chưa cấp. R60-03 chờ quota renderer và R62-01 phải xử lý trước khi tái sử dụng RFQ renderer. RFQ primary KPI và intake-funnel/2 nằm ngoài lát cắt. Production và Commercial GA vẫn NO-GO.
