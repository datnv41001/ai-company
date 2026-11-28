# AMC-GUIDE-QUAL-01 · Nghiệm thu hướng dẫn sử dụng trên trang sản phẩm

## Ai dùng guide và quyết định điều gì

Editor nhận phiếu Strategy đã ký và biên tập guide. Content reviewer đối chiếu guide với nguồn và yêu cầu của phiếu trước khi ký phiên bản. Người đọc cuối cần thực hiện được các bước trong tình huống dùng sản phẩm. PR #70 đã nghiệm thu đường chạy nội bộ cho hai vai trò đầu trên dữ liệu tổng hợp. Thời gian biên tập và khả năng người đọc làm đúng vẫn cần đo trên người thực hành. [Chứng nhận merge #70](MAIN-70.md)

| Mốc | Bằng chứng để ghi nhận |
|---|---|
| QA approved | Quyết định của Content reviewer có thẩm quyền trên revision và digest của guide |
| Người thực hành sử dụng được | Người đọc hoàn thành đúng nhiệm vụ mô phỏng và nhận ra điều kiện sử dụng trong phép thử đã duyệt |
| Người nhận được ủy quyền tiếp nhận | Quyết định tiếp nhận của đúng người nhận, gắn với phiên bản đã giao |
| Business-accepted Marketing Work Unit | Công việc đủ điều kiện theo Product Mission, có quyết định của doanh nghiệp và chứng cứ thuộc đúng phạm vi |
| Business outcome | Số đo kết quả kinh doanh theo phương pháp và quyền đo đã được phê duyệt |

Vòng này có dữ liệu về QA nội bộ. Chưa có lượt practitioner, recipient acceptance, work unit được ghi vào North Star hoặc số đo kết quả Marketing từ các fixture. [Quy định North Star](../../PRODUCT_MISSION.md)

## Chất lượng nghiệp vụ và quyết định cần quyền riêng

**R70-01 · Giá trị tăng thêm của model còn mở.** Đã chạy cùng composer cho ba lựa chọn trên mỗi ca VI và EN. Cả sáu guide giữ nguyên bước, qualifier và CTA. Ở ca VI, checklist của nhánh mô phỏng model vi phạm yêu cầu đánh số. Ở ca EN, hai cách trình bày đều hợp lệ cho các kiểm tra độc lập. Lựa chọn của editor cũng được ấn định bằng fixture. [Ba nhánh và sáu bản đầu ra](quality/COMPARISON.md) · [Rubric 10 tiêu chí](quality/RUBRIC.md)

**R70-02 · Nghĩa vụ trong Work Order.** Trên #70, reviewer ký được checklist có trình tự bắt buộc mà không thấy yêu cầu đánh số. Bản sửa đưa các mục đã được phép giao vào màn hình Content QA. Reviewer đánh giá từng mục và xác định quan hệ giữa các bước. Kết luận “cần làm rõ”, nghĩa vụ chưa đạt hoặc checklist được phân loại là có thứ tự đều chặn duyệt. Bằng chứng gắn với đúng phiếu, revision và digest. Việc đọc hiểu một yêu cầu bằng ngôn ngữ tự nhiên vẫn là quyết định của reviewer. [Mã kiểm tra quyết định](../../../app/product_guide_studio.py) · [Kiểm thử VI/EN](../../../tests/test_product_guide_order_qa.py)

Quyết định kỹ thuật nằm ở thao tác ký của reviewer. Contract đầu ra của Content worker vẫn nhận `heading` và `layout`. Việc nhận lựa chọn bố cục từ model, việc editor lưu revision và việc con người ký QA là ba thời điểm độc lập. Digest của release và nội dung đã ký trên #70 được giữ nguyên. [Contract WF-06/1](../../../catalog/product-use-guide-v1.json)

**Pilot ở mức đề xuất.** Điều phối viên cần phê duyệt về nhân sự, consent, xử lý dữ liệu và ngân sách trước khi mời người tham gia. Phương án dùng 4 editor, 8 người đọc, 2 QA và 1 điều phối viên. Dự trù 20 giờ công và trần minh họa 6.490.000 đồng. Kết quả sẽ gồm cả ca hold, từ chối hoặc thiếu bằng chứng. [Quy trình đối chứng, phân công, chi phí và điều kiện dừng](quality/PRACTITIONER.md)

Reviewer có thể bắt đầu bằng ca đỏ trên #70, mở checklist VI trong ảnh mobile, đối chiếu phần trả lại và receipt của bản đánh số, rồi so với checklist EN được chấp nhận. [Hồ sơ Studio, receipt và ảnh desktop/tablet/mobile](studio/README.md)

## Tiếp quản và rollback

Full regression trên Windows đạt 836, bỏ qua 2 trong 27 phút 49 giây. Đối chiếu tên testcase và trạng thái skip trong [JUnit của toàn bộ candidate](full-regression.xml). CI trên main trong chứng nhận #70 thuộc phiên bản trước bản sửa QA.

Để chạy riêng 12 ca của vòng này, dùng `python -m pytest -q tests/test_guide_selection_comparison.py tests/test_product_guide_order_qa.py tests/test_product_guide_mailbox.py` trên PostgreSQL thử. Phép thử chuyển phiên bản riêng dùng binary #70 cấp phiếu rồi mới chuyển sang candidate trên cùng database. Dòng tài liệu và dòng receipt giữ nguyên SHA-256 qua việc đọc và phát lại. [JUnit 12 ca](focused.xml) · [Biên nhận của phép thử hai binary](postgresql/historical-qa.json)

**R70-03 · Thẩm quyền trong lúc worker báo kết quả.** Trong sáu ca PostgreSQL, phần chọn tiêu đề và bố cục có thể còn ở mailbox cho đến lần consume kế tiếp. Không ca nào chuyển phần đó thành checkpoint Content hoặc guide sau thu hồi. Dispatcher hạch toán usage cho đúng attempt. Chưa có cam kết thời gian xóa khi dispatcher dừng. [Transaction ID, JUnit và quyền đọc](postgresql/README.md)

So sánh base, head và trial trong mô tả draft. Dùng manifest của nhánh để kiểm lại các tệp. Cài dependency theo README ở gốc repo. Các phép thử PostgreSQL cần database tổng hợp riêng và các biến môi trường CI chuẩn. Không chạy publisher trên database khách hàng. Kiểm lại bộ hồi quy bằng `python -m pytest -q`, và dùng các lệnh browser trong hồ sơ Studio để tái lập màn hình.

Trước khi chuyển writer sang bản mới, rút các instance cũ khỏi đường ghi Content QA và chờ request đang mở hoàn tất. Binary #70 còn chạy có thể tạo quyết định kiểu cũ. Khi quay về #70, tạm dừng nhận quyết định guide mới và giữ toàn bộ receipt, revision, attempt và ledger. Nếu cần dừng commission/worker của riêng guide, dùng cơ chế revoke đúng release hiện có. Lịch sử và các receipt của #70 tiếp tục được nhận diện theo hình thức lúc ký. [Runbook PostgreSQL](../product-guide/POSTGRESQL.md)

## Phạm vi còn mở

- AMC-R60-03 tiếp tục chờ qualification của renderer. Nguyên nhân timeout Storyboard chưa được xác định. [Hồ sơ renderer](../connected-workforce/SEMANTIC-REVIEW.md)
- AMC-R64-02 về độ tin cậy của chuyển trạng thái Sales và AMC-R68-01 về cách trình bày quyết định lịch sử còn mở. [Sales](../round64/closure/README.md) · [Sổ finding](../../SECURITY_AND_GA_BLOCKERS.md)
- PR #65 còn cần provenance Cold Handoff và đồng bộ baseline. Kết quả âm RS-01/02 được giữ. D/A/C 12 brief/72 lượt ở mức PROPOSED. O-09 chờ custodian độc lập và vault. [Bản đồ tri thức](../../KNOWLEDGE_MAP.md)

Production và Commercial GA vẫn NO-GO.
