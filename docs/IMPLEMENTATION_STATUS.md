# Trạng thái hiện thực và nghiệm thu V1

**Mốc tích hợp nội bộ:** main `a6fa1976f9a5d4557a4e3b64ac28dec2eb0fc0a4`. WF-03 đã có handoff /2 trên dữ liệu tổng hợp. R64-02 còn mở. Bằng chứng về phiếu Content giới hạn ở việc giao lập nháp. Nghiệm thu của practitioner, quyền thực thi bên ngoài và hiệu quả Marketing vẫn cần kiểm riêng. Các mốc dưới đây giữ phạm vi và thời điểm ban đầu. [Chứng nhận #64](evaluation/round64/MAIN-64.json) · [Việc tiếp theo](../HANDOFF.md)

**Vòng #64.** Studio chuẩn bị lệnh soạn Content nội bộ từ quyết định Strategy có biên nhận. Phạm vi hiện tại là commission in-house, với nguồn và người nhận đủ quyền trên cùng manifest. Bản thực thi, nghiệp vụ thương mại và kết quả thị trường vẫn chờ các cổng riêng. [Luồng, giới hạn và bằng chứng](evaluation/round64/README.md)

**Vòng #63.** Bản làm việc nội bộ của Marketing lead thử đối chiếu checkpoint Research/Strategy @4 với các quan sát được mã hóa trong brief tổng hợp. Có thể giao Content một bản nháp có điều kiện hoặc giữ việc để làm rõ. Runtime WF-03 @3 vẫn dùng bản registry đã phát hành. Năng lực suy luận trên brief mới và giá trị công việc đối với practitioner còn chờ đánh giá. [Đầu ra đối chứng và trạng thái](evaluation/round63/README.md)

**Vòng #62.** Sales và Marketing có thể đối chiếu quantity, nguồn MOQ, revision và mốc thương mại trong ba phiếu ngoại tuyến tổng hợp. Hợp đồng `rfq-qualification/1` ở trạng thái proposed. Chi phí lao động tiết kiệm và độ hữu ích cho người dùng thực chưa được đo. [Phạm vi và quyết định còn mở](evaluation/round62/README.md)

**Sau merge #60, vòng #61.** WF-08 @1/@2 có baseline nội bộ trên main `83894ffe`, core v26. R60-01 và R60-02 đã đóng trong phạm vi chứng minh. R60-03 và qualification nghiệp vụ còn mở. Đã chuẩn bị đề xuất RFQ chỉ đọc và pilot tám việc; số việc được người dùng doanh nghiệp tiếp nhận trong vòng này bằng 0. [Biên nhận và trạng thái bốn luồng](evaluation/round61/README.md)

**PR #60 · vòng QA ngữ nghĩa.** Phạm vi là câu mở đầu của bản Content và storyboard tiếng Việt ở WF-08 @2, ba hành động người mua, bốn văn phong và thao tác đổi hook. Người làm Content và QA dùng brief đã duyệt để đối chiếu ý định của câu mở, CTA và nguồn điều kiện thương mại. Đọc [hồ sơ phản biện](evaluation/connected-workforce/SEMANTIC-REVIEW.md) để xác định bản chạy, giới hạn và cổng còn mở. Chưa có phút biên tập/QA hoặc quyết định tiếp nhận từ người hành nghề. Phạm vi V1 vẫn gồm 49 module, 37 vai trò và 24 workflow mẹ.

## Vòng sau #59 · bàn giao giữa Content, Video, Creative và Sales

Scope V1 là 49 module, 37 vai trò, 24 workflow mẹ. Main đã nhận WF-08 @1. Nhánh thử nội bộ phát triển tiếp trên schema v26. Bảng nghiệm thu theo từng finding và artefact ở [Connected Marketing Workforce](evaluation/connected-workforce/README.md). Năng lực đạt ở từng ca tổng hợp; đánh giá kinh tế cần người nhận công việc thực tế.

**Vòng WF-08 sau #58.** Main đã tích hợp bộ campaign cũ ở `1c40ad31`. Nhánh kế tiếp tập trung một nhiệm vụ director → storyboard qua queue nội bộ, trên manifest của từng khách, với biên nhận và QA. [Trạng thái theo bản](evaluation/workforce-video/README.md) · [KPI và ranh giới bằng chứng](evaluation/workforce-video/MEASUREMENT.md). Các mốc dưới đây mô tả khả năng ở phiên bản ghi trên từng dòng.

**Mốc sau PR #57.** Main nội bộ `26578088519d99f4aed5be9c516ac247f3d4735e` giữ core v26, Business v3, C3 v5 và journal ops/2. Tạo và bổ sung RFQ theo m² đã được sửa. Bước rút hồ sơ trước phân công và pilot v2 có nghiệm thu kỹ thuật. Trên head sửa và trial, cả ba JUnit ghi 622 đạt, 2 skip. [CI trước merge](https://github.com/datnv41001/ai-company/actions/runs/45777424779) · [CI trên main](https://github.com/datnv41001/ai-company/actions/runs/45780019694). Nhánh kế tiếp có hai gói sản xuất, preflight grammar và bộ mời practitioner. Chưa có người hành nghề tham gia. Số Business-accepted Marketing Work Units vẫn là 0. [Bằng chứng theo luồng](evaluation/department-review/ROUND-57-PRODUCTION.md)

**Mốc main sau PR #56.** Đã hợp nhất chuỗi #49–55 qua một merge commit `bbb0b9c41b92e666e133499e9c71f53592828c3d`, tree `46fc7eaffa03c78f738d64a35a1e5dc13a794072`. CI push trên commit này có 3 job bắt buộc đạt. JUnit ghi 602 đạt và 2 skip. Core v26, Business v3, C3 v5, journal ops/2. Các kiểm thử sandbox cho WF-14, WF-18 và WF-20 đã có trên main. Chưa có nghiệm thu toàn bộ nào trong 49 module, 37 vai trò, 24 workflow. Phần sau merge đang được phản biện ở [báo cáo thị trường và handoff](evaluation/department-review/MARKET-HANDOFF.md). [Biên nhận theo SHA](evaluation/department-review/MAIN-56.json) · [GitHub Actions](https://github.com/datnv41001/ai-company/actions/runs/45770716137)

**Mốc đối chiếu ngày 26/11/2026** là `main` sau PR #48, commit `380be3eb70a41424c6d45318b0b1890fa950970a`, core v26, Business v3, C3 v5 và journal `ops/2`. Trên mốc này có bằng chứng tích hợp sandbox từ brief tới bản giao, QA, thực thi cục bộ và đối soát. Số yêu cầu **đầy đủ** có quyết định nghiệm thu nghiệp vụ ghi nhận trong hồ sơ là **0/49 module, 0/37 vai trò, 0/24 workflow**. Số đơn vị công việc được doanh nghiệp thực tiếp nhận trong các phép đo là **0**. Chi phí trên một đơn vị được tiếp nhận chưa xác định. Production và Commercial GA giữ **NO-GO**. [Commit nền][main] · [Cutover][cutover] · [Hồ sơ pilot][pilot] · [Điều kiện GA][ga]

## Cách đọc trạng thái

Quy đổi L0–L6 vào tám trạng thái dưới đây theo từng năng lực. Ý tưởng đứng trước L0. Đặc tả = L0, hiện thực = L1, kiểm kỹ thuật = L2, tích hợp đã xác minh = L3, nghiệm thu nghiệp vụ = L4, đủ điều kiện và được cấp quyền production = L5, xác minh giá trị thương mại = L6. Quyết định GA toàn V1 còn phải đạt mọi gate trong đặc tả. Trạng thái tiến độ của ticket, verdict của reviewer và bảy lớp kiến trúc đo các việc khác nhau.

| Trạng thái | Căn cứ cần tra |
|---|---|
| Ý tưởng | Giả thuyết sản phẩm, người dùng và phép thử. Các ý tưởng nghiên cứu nằm trong [sổ cơ hội](research/PRODUCT_OPPORTUNITIES.md). |
| Đặc tả | Yêu cầu có ID trong [đặc tả V1][prd], [catalog vai trò][roles] hoặc [catalog workflow][flows]. Các định nghĩa và tiêu chí đầy đủ được giữ ở những nguồn này. |
| Đã hiện thực | Có mã nguồn hoặc API/UI xử lý phần việc mô tả. Kiểm tra nhánh và SHA chứa mã. |
| Đã kiểm kỹ thuật | Có kết quả thử, đầu vào, đầu ra, môi trường và phạm vi kiểm cụ thể. File test cho biết cách kiểm, kết quả chạy cho biết đã kiểm trên cây nào. |
| Đã tích hợp | Mã có trong cây tích hợp được định danh. Muốn ghi đã vào main cần commit thực tế trên main. Kết quả ở một PR hoặc cây ghép thử chỉ áp dụng cho cây đó. |
| Nghiệm thu nghiệp vụ | Người có đúng vai trò và thẩm quyền quyết định trên bản giao, phiên bản, tiêu chí và kết quả công việc xác định. Phiếu pilot còn thiếu được ghi là mở. |
| Được phép chạy production | Cần quyết định phát hành cho môi trường, quyền và tác động cụ thể, kèm bằng chứng an toàn và vận hành. |
| Sẵn sàng thương mại | Cần quyết định GA cho toàn bộ V1, gồm bằng chứng giá trị, kinh tế, bảo mật, pháp lý và vận hành. [Điều kiện sản phẩm][prd] · [Sứ mệnh][mission] |

## Các thay đổi đã vào main sau mốc #48

| Phạm vi | Trạng thái tại main sau #57 | Phần còn trên nhánh #58 |
| --- | --- | --- |
| MKT-07/08 và công việc sáng tạo | #51 đã vào main qua #56. Studio có nguồn chỉnh sửa, ba tỷ lệ PNG, video VP8 và landing/form sandbox với revision và receipt. [Hồ sơ #51](https://github.com/datnv41001/ai-company/tree/a5909321ed012c6ea99fcc0fdfadceb3c334c3ca) · [Tree đã tích hợp](evaluation/department-review/MAIN-56.json) | Hai bộ campaign, storyboard có điều kiện giá tham khảo v2 và phụ đề có kiểm thử. [Gói giao](evaluation/campaign-production-review/README.md) |
| Handoff, CRM, reporting và Role Desk | #49–55 bổ sung KPI theo cohort, người nhận theo campaign, đối soát giao dịch và kiểm điều kiện trên snapshot. #57 sửa đúng đơn vị m², cho rút RFQ trước khi giao và tách treatment exposure của producer. [Biên nhận #56](evaluation/department-review/MAIN-56.json) · [Sửa #57](evaluation/department-review/R57-MATERIAL-UNITS.md) | Nghiên cứu grammar, preflight measurement và phiếu mời practitioner. Chưa có binding mới vào runtime cho model hoặc connector ngoài. |

## Cách đối chiếu các bảng lịch sử

Các bảng 49 module, 37 vai trò và 24 workflow bên dưới ghi **main tại PR #48**. Đọc cùng bảng thay đổi ở trên để xác định trạng thái hiện tại. Trong các bảng lịch sử, **Thành phần** có nghĩa phần việc ghi ở dòng đó đã có mã tại mốc #48. Liên kết chỉ rõ mã, ca thử hoặc biên nhận hiện có. **Đặc tả** có nghĩa sổ này mới xác nhận được yêu cầu ở phạm vi nêu. Cả hai nhãn đều giữ mở quyết định nghiệp vụ toàn hàng. Thử kỹ thuật và tích hợp được ghi riêng cho đúng phiên bản.

## 49 module

Mỗi ID dưới đây tra được mô tả đầy đủ ở mục 3 của [đặc tả][prd]. Với nhóm ID chung dòng, phạm vi hoặc giới hạn áp dụng cho từng ID theo thứ tự ghi.

| ID | Trạng thái tại main #48 | Phần đã có, phần còn mở và căn cứ |
|---|---|---|
| SAA-01 | Thành phần | Đăng ký tài khoản, xác minh qua hộp thư thử, tạo hoặc tham gia workspace. Hành trình mua gói thương mại còn mở. [Onboarding](PR16-ONBOARDING.md) |
| SAA-02 | Thành phần | Mời và xác minh, quota admission, thu hồi phiên thiết bị, refresh và tái xác thực. MFA, SSO và vận hành email thật còn mở. [Phiên thiết bị](DEVICE-SESSIONS-A1.md) · [Ca tranh chấp phiên](../tests/test_device_sessions.py) |
| SAA-03, SAA-08 | Thành phần | SAA-03 có tạo workspace. SAA-08 có mời người và phân quyền thành viên/khách. Chưa có nghiệm thu vòng đời tenant và quản trị nhóm đầy đủ. [Onboarding](PR16-ONBOARDING.md) · [Vòng đời người nhận](../tests/test_recipient_lifecycle.py) |
| SAA-04 | Thành phần | Có chọn release và cấp quyền workflow cho campaign. Chưa nghiệm thu cấu hình tổ chức và tuyển agent theo yêu cầu Company Builder. [Registry](../app/registry.py) |
| SAA-05, SAA-09 | Đặc tả | Chưa có hồ sơ nghiệm thu hệ thuê bao/PSP cho SAA-05 hoặc dịch vụ help desk/ticket/SLA cho SAA-09. [Đặc tả][prd] · [Truy vết lịch sử][trace] |
| SAA-06 | Thành phần | Ghi lần thử, token, hold, đối soát chi phí và phần chưa đo. Chi phí toàn bộ hạ tầng thật còn thiếu. [Sổ chi phí sandbox][ops] |
| SAA-07 | Thành phần | Có thư viện kỹ năng Marketing được ghim và kiểm thử. Luồng cài đặt, cấp quyền và rollback một gói marketplace bởi workspace còn mở. [Thư viện](../app/c3_skill_library.py) · [Ca thử](../tests/test_c3_skill_library.py) |
| AGY-01, AGY-02 | Thành phần | AGY-01 có hồ sơ client và lịch sử RFQ theo campaign. AGY-02 có brief, dữ kiện và revision được duyệt. Chưa nghiệm thu trọn CRM khách hàng và quy trình discovery. [API](../app/main.py) · [Hành trình chiến dịch][engine] |
| AGY-03 | Đặc tả | SOW, hợp đồng, thay đổi giá/phạm vi dịch vụ agency và ký thương mại còn mở. [Đặc tả][prd] |
| AGY-04, AGY-08 | Thành phần | AGY-04 chia sẻ snapshot theo quyền client. AGY-08 hỗ trợ phản hồi, yêu cầu sửa và nộp revision mới. Chưa có nghiệm thu portal toàn diện hoặc change order có ảnh hưởng giá. [Bàn giao Studio][studio] · [Vòng đời review](../tests/test_review_lifecycle.py) |
| AGY-05, AGY-06 | Thành phần | AGY-05 có gói việc, hạn, dependency và biên nhận trong campaign. AGY-06 có bàn giao Sales và theo dõi lịch dịch vụ trong sandbox. Điều phối liên dự án, sức khỏe tài khoản và gia hạn còn mở. [Commission][commission] · [Lịch hẹn][ops] |
| AGY-07 | Thành phần | Kiểm kê chi phí theo việc và khoản phân bổ được xác thực trên fixture. Hóa đơn phí dịch vụ, đối soát kế toán thực và margin chưa nghiệm thu. [Sổ chi phí sandbox][ops] |
| MKT-01, MKT-02 | Thành phần | WF-03 soạn nghiên cứu từ nguồn ghim. Brief lưu ICP và tình huống mua. Cần kiểm tính đại diện thị trường và xác minh phân khúc với khách. [Đối chiếu MKT][mkt] · [Các lần chạy][commission] |
| MKT-03, MKT-04 | Thành phần | Có guideline, revision, claim và dữ kiện sản phẩm. WF-03 tạo đề xuất định vị. Quyền sử dụng thực, battlecard và kế hoạch ra mắt chưa được nghiệp vụ duyệt. [Tri thức](business-profile/C1-RUNBOOK.md) · [Đối chiếu MKT][mkt] |
| MKT-05, MKT-06 | Thành phần | Có chiến lược và kế hoạch đo, planner ghim brief, manifest, deadline, ngân sách và giao cho worker. Chuyên viên chưa nghiệm thu lịch và chiến lược đa chiến dịch. [Hành trình][engine] · [Commission][commission] |
| MKT-07, MKT-08 | Thành phần | Có lịch biên tập, brief ảnh/video, QA trường và snapshot. Ở mốc #48, đầu ra là brief cho người thiết kế. #51 bổ sung file ảnh/video và đã vào main qua #56. [Hai bộ tài liệu theo kênh][factory] |
| MKT-09, MKT-10 | Thành phần | Copy social, kế hoạch/mẫu quảng cáo, QA và diễn tập đúng nhóm tài sản. Đăng bài, moderation, chi tiền, xác nhận nền tảng thật còn mở. [Studio theo kênh][factory] · [Biên nhận thực thi cục bộ][dispatch] |
| MKT-11, MKT-12 | Thành phần | WF-13 cho landing copy, CTA và SEO metadata qua Studio. Audit/crawl, CMS, trang production và thử nghiệm CRO thực còn mở. [Bản giao Studio][studio] · [Commission][commission] |
| MKT-13 | Thành phần | Ghi consent, RFQ đến Sales và lịch hẹn tới hoàn thành/hủy/vắng. CRM bên ngoài, nurture và retention còn mở. [Giao Sales][engine] · [Lịch hẹn][ops] |
| MKT-14 | Đặc tả | Chưa có run đủ điều kiện cho PR/Influencer/Events. [Đối chiếu từng module][mkt] |
| MKT-15, MKT-16 | Thành phần | Có SKU, giá/đơn vị/điều kiện, manifest nguồn và lineage theo scope. Feed hàng hóa và đầu nối dữ liệu doanh nghiệp thực còn mở. [Tri thức thương mại](business-profile/C1-RUNBOOK.md) · [Đối chiếu MKT][mkt] |
| MKT-17, MKT-18 | Thành phần | Funnel và báo cáo từ journal phân biệt nguồn thiếu, hoàn tiền và lịch hẹn. Đối soát ERP và báo cáo kỳ được khách duyệt còn mở. [Đối soát RFQ][engine] · [Hành trình dịch vụ][ops] |
| MKT-19, MKT-20 | Thành phần | Có hạn mức AI, ngân sách media mô phỏng và khoản chưa đo. Có locale, thị trường và đơn vị theo brand. Hiệu quả chi phí và QA bản địa hóa đa thị trường còn mở. [Chi phí][ops] · [Phạm vi locale][mkt] |
| AIO-01, AIO-02 | Thành phần | Director giao việc, compiler đóng băng DAG, worker dùng dependency, lease và retry. Điều phối toàn bộ workflow V1 và tải production còn mở. [Compiler](../app/dynamic_plan.py) · [Biên nhận chạy][commission] |
| AIO-03, AIO-04 | Thành phần | Registry kiểm profile, phiên bản và adapter. Gateway dự phòng token, gọi model và tính usage. Bộ release, model và chất lượng đã đo xem ở các hàng vai trò bên dưới. [Registry](../app/registry_compatibility.py) · [Gateway](../app/workforce_gateway.py) · [Nghiên cứu model][study] |
| AIO-05 | Thành phần | Có danh sách tác vụ cho phép, duyệt theo nhóm và dispatcher loopback. Quyền OAuth và receipt nền tảng bên ngoài còn mở. [Biên nhận dispatch][dispatch] |
| AIO-06 | Thành phần | Nguồn, quyền, version, scope, claim và thu hồi được kiểm khi QA/chia sẻ. Retention và kiểm định toàn kho còn mở. [Hồ sơ C1](business-profile/C1-RUNBOOK.md) |
| AIO-07, AIO-08 | Thành phần | Có QA đúng revision/digest, thay đổi làm mất hiệu lực chữ ký, snapshot và quyết định riêng theo client. Còn thiếu nghiệm thu vòng đời đầy đủ cho mọi loại tài sản. [Studio][studio] · [Bàn giao theo kênh][factory] |
| AIO-09, AIO-10 | Thành phần | QA claim và so sánh đầu ra theo rubric trên fixture. Có RLS, kiểm scope, quyền writer và biên nhận. Đánh giá người làm nghề và kiểm định bảo mật production còn mở. [Nghiên cứu][study] · [Cutover][cutover] · [Cổng GA][ga] |
| AIO-11, AIO-12 | Thành phần | Có scheduler, lease, chẩn đoán chờ và diễn tập restore. Có hold/usage, retry, chi phí xác nhận hoặc chưa đo. SLA sự cố và giá thành thực trên việc được khách tiếp nhận còn mở. [Scheduler](../tests/test_wait_diagnostics.py) · [Cutover][cutover] · [Chi phí][ops] |

## 37 vai trò AI

Tất cả **37/37 ID** trong [catalog][roles] mang `specification_only` ở cấp vai trò đầy đủ. Main sau #58 có 5 ID đã chạy. Trên nhánh WF-08 có **6 ID riêng biệt** với binding cho từng nhiệm vụ. Ba lượt commission có biên nhận từng request và bản giao dừng ở `awaiting_qa`. Nghiên cứu hai brief khác ghi lại đầu ra trước/sau biên tập và các quyết định của tài khoản fixture. [Ánh xạ adapter](../app/registry_adapters.py) · [Biên nhận commission][commission] · [Nghiên cứu hai brief][study]

| ID | Phần việc được gọi trong runtime và bản áp dụng |
|---|---|
| `ai-managing-director` | Lập phân công cho các tiểu quy trình WF-03, WF-13 và, trên nhánh mới, WF-08. [WF-03 @3][wf03] · [WF-13 @6][wf13] |
| `ai-market-researcher`, `ai-marketing-strategist` | Đọc nguồn ghim rồi soạn chiến lược trong WF-03. [Manifest][wf03] · [Ba request cho một brief](evaluation/campaign-engine/commission/acoustic-panel/strategy/commission-receipts.json) |
| `ai-copywriter-content-strategist`, `ai-seo-geo-specialist` | Soạn landing copy và metadata trong WF-13. [Manifest][wf13] · [Ba request cho một brief](evaluation/campaign-engine/commission/acoustic-panel/landing/commission-receipts.json) |
| `ai-video-storyboard` | Từ nhánh sau #58, nhận nhiệm vụ từ Director và tạo storyboard bằng adapter tất định nội bộ. [Lượt chạy thật](evaluation/workforce-video/README.md) |

**31 ID còn lại** ở mức đặc tả vai trò, chưa có binding của chính ID trên nhánh này. Có thể tra nguyên văn từng ID dưới đây trong [catalog][roles]. Một chức danh ghi trong brief, tài khoản fixture, bước QA của người hoặc nội dung do bộ soạn theo quy tắc tạo ra không chứng minh agent tương ứng đã chạy.

| Nhóm tra cứu | ID |
|---|---|
| Điều hành, khách hàng | `ai-marketing-operations-director`, `ai-resource-project-manager`, `ai-executive-assistant`, `ai-business-development`, `ai-solutions-consultant`, `ai-account-director`, `ai-client-success`, `ai-commercial-proposal-specialist` |
| Nghiên cứu, chiến lược | `ai-consumer-insights-analyst`, `ai-competitor-intelligence`, `ai-brand-strategist`, `ai-product-marketing-gtm`, `ai-customer-journey-planner` |
| Nội dung, sáng tạo | `ai-creative-director`, `ai-social-content-specialist`, `ai-visual-design`, `ai-editorial-localization`, `ai-digital-asset-librarian` |
| Media, web, CRM, PR | `ai-performance-media-planner`, `ai-google-ads-specialist`, `ai-meta-ads-specialist`, `ai-tiktok-linkedin-channel-specialist`, `ai-website-cro-specialist`, `ai-crm-lifecycle-specialist`, `ai-pr-influencer-event-coordinator` |
| Đo lường, QA, kiểm soát | `ai-marketing-data-analyst`, `ai-attribution-experiment-analyst`, `ai-martech-tracking-specialist`, `ai-content-qa`, `ai-policy-brand-compliance`, `ai-cost-capacity-analyst` |

## 24 workflow nghiệp vụ

Tất cả **24/24 workflow mẹ** giữ nhãn catalog `specification_only`. Nhánh WF-08 bổ sung `WF-08/video-storyboard@1`, nâng số họ tiểu quy trình có manifest chạy từ hai lên ba. Hai họ có trước gồm `WF-03/research-strategy-draft@3` và `WF-13/landing-seo-draft@6` ở release C3 hiện hành. Phần mềm giữ các phiên bản cũ cho lịch sử và tương thích. Khi tra một ID bên dưới, đối chiếu phần đã chạy với trigger, các bước cuối và quy tắc duyệt trong [catalog][flows]. [Mã nhận dạng release](../app/c3_assets.py) · [Điều phối theo phiên bản](../app/c3_releases.py)

| ID workflow mẹ | Bằng chứng thành phần trên main và giới hạn |
|---|---|
| WF-01, WF-02 | Có client/workspace và hồ sơ brand có nguồn. Chưa có E2E từ lead tới hợp đồng agency hoặc toàn bộ brand onboarding. [Onboarding](PR16-ONBOARDING.md) · [Tri thức brand](business-profile/C1-RUNBOOK.md) |
| WF-03, WF-04 | **WF-03** có run research → strategy từ nguồn ghim. WF-04 nhận đóng góp từ bản chiến lược. Thu nguồn/audit độc lập và kế hoạch quý/năm chưa có nghiệm thu toàn trình. [Manifest][wf03] · [Run và bản giao][commission] |
| WF-05, WF-10, WF-15, WF-23, WF-24 | Chưa xác nhận một run từ trigger đến kết quả cuối cho GTM, community/crisis, PR/influencer, vận hành định kỳ hoặc vòng đời thuê bao. Điều kiện từng ID ở [catalog][flows] và [ma trận gốc][trace]. |
| WF-06, WF-07, WF-08 | Planner giao việc, Studio tạo lịch và brief sản xuất ảnh/video rồi QA theo nhóm. Các ca dùng RFQ và lịch dịch vụ tổng hợp. [Commission][commission] · [Bốn gói Studio][factory] |
| WF-09, WF-12 | Social và ad có copy đã duyệt với preview/diễn tập ở đích cục bộ. Quyền đăng thật và đối soát chi tiêu thật chưa mở. [Biên nhận bốn nhóm][dispatch] |
| WF-11, WF-13 | **WF-13** có run content → SEO, bàn giao landing copy và metadata. WF-11 hưởng phần metadata. Crawl/CMS, publish/rollback trang production hoặc A/B thực chưa nghiệm thu. [Manifest][wf13] · [Bản giao][studio] |
| WF-14, WF-20 | Có consent, chuyển RFQ đến Sales, phân công lịch hẹn và theo dõi kết quả tổng hợp. CRM sync và doanh nghiệp tiếp nhận lead thật còn mở. [Engine][engine] · [Lịch hẹn][ops] |
| WF-16, WF-17 | Có SKU/đơn vị, journal đơn hàng và nguồn để đối soát trong sandbox. Feed/tồn kho thực và thu nhận dữ liệu đa nền tảng còn mở. [Đối soát][engine] · [Tri thức](business-profile/C1-RUNBOOK.md) |
| WF-18, WF-19 | Có funnel, điều chỉnh doanh thu và đề xuất tối ưu theo trạng thái có nguồn. Chưa xác nhận báo cáo kỳ được khách nhận hoặc hiệu quả thay đổi thật. [Engine][engine] |
| WF-21, WF-22 | WF-21 có quyết định trên snapshot, trả sửa và nộp lại. WF-22 có diễn tập backup/restore và fence writer qua cutover. Hành trình change order theo hợp đồng và xử lý sự cố vận hành thực còn mở. [Vòng đời review](../tests/test_review_lifecycle.py) · [Cutover][cutover] |

## Lịch sử bốn đề xuất tại mốc main #48

Khi lập bảng ở mốc #48, bốn PR dưới đây là các draft xếp nối nhau. Bảng giữ nguyên head và bằng chứng ở thời điểm đó. Các thay đổi đã vào main qua #56. [Đối chiếu ancestry, tree và CI](evaluation/department-review/MAIN-56.json)

| PR và base | Head khi đối chiếu | Phần bổ sung đề xuất và hồ sơ |
|---|---|---|
| [#49](https://github.com/datnv41001/ai-company/pull/49) trên main #48 | `0498949e` | Giữ nguyên định nghĩa KPI từ brief đến báo cáo và tách cohort theo kỳ. [Kết quả theo SHA](https://github.com/datnv41001/ai-company/blob/0498949e64f4d030cc9ba2f0f961ab4dfc2e2ab0/docs/evaluation/kpi-integrity/RESULTS.md) |
| [#50](https://github.com/datnv41001/ai-company/pull/50) trên #49 | `104af78b` | Hộp việc và chuyển giao cho nhân sự Marketing/Sales/Service theo campaign. [Hồ sơ theo SHA](https://github.com/datnv41001/ai-company/tree/104af78ba2475973404c1043706042595b3b97bf/docs/evaluation/campaign-role-desk) |
| [#51](https://github.com/datnv41001/ai-company/pull/51) trên #50 | `a5909321` | Nguồn chỉnh sửa, ba tỷ lệ PNG, video VP8, landing và form HTML sandbox. [Qualification theo SHA](https://github.com/datnv41001/ai-company/blob/a5909321ed012c6ea99fcc0fdfadceb3c334c3ca/docs/evaluation/real-production/QUALIFICATION.md) |
| [#52](https://github.com/datnv41001/ai-company/pull/52) trên #51 | `95aed621` | Duyệt nghĩa thương mại theo nguồn, biên tập theo kênh, quảng cáo gắn đúng landing sandbox. [Đầu ra và giới hạn theo SHA](https://github.com/datnv41001/ai-company/blob/95aed621381c782114b18521d2b2d58eb17a7828/docs/evaluation/commercial-meaning/README.md) |

## Bằng chứng lịch sử và lần xác minh kế tiếp

Bản ghi starter ngày 23/11/2026 mô tả endpoint lập bảy task xác định và portal schema 3. Endpoint `.../campaigns/{campaign_id}/plan` vẫn ghi `llm_called: false`. Điểm vào Workforce, Studio và dispatcher có hồ sơ chạy độc lập. Ma trận PR9 ghi tình trạng 110 yêu cầu ở mốc ban đầu `2846c174`. Sổ 19 năng lực và bảng MKT ở mốc #44 giúp tìm đầu ra và trách nhiệm người làm nghề. Các mốc #45–#48 trên main lần lượt bổ sung nghiên cứu, giao việc, Studio theo kênh và journal sandbox. [Ảnh chụp starter](https://github.com/datnv41001/ai-company/blob/3434a42/docs/IMPLEMENTATION_STATUS.md) · [Endpoint](../app/main.py) · [Truy vết gốc][trace] · [Sổ 19 năng lực](evaluation/campaign-engine/CAPABILITIES.md) · [Lịch sử main][main]

Bước nghiệm thu nghiệp vụ tiếp theo là giao cùng hai brief cho người làm Marketing, reviewer độc lập và Sales hoặc chủ doanh nghiệp, khóa rubric rồi thu bản đầu, công sửa, QA, quyết định trên đúng revision và chi phí có nguồn. Lưu cả việc bị trả lại và lần chạy thất bại. Khi bổ sung bằng chứng, chỉ cập nhật ID có liên quan và ghi SHA, môi trường, ca thử, artifact, kết quả, thẩm quyền người quyết định và việc còn mở. [Thủ tục pilot][pilot] · [Đơn vị đo](evaluation/RFQ-WORK-UNITS.md)

[main]: https://github.com/datnv41001/ai-company/commit/380be3eb70a41424c6d45318b0b1890fa950970a
[prd]: PRODUCT_SPEC_V1.md
[mission]: PRODUCT_MISSION.md
[ga]: SECURITY_AND_GA_BLOCKERS.md
[roles]: ../catalog/agent_roles.json
[flows]: ../catalog/workflows.json
[trace]: PR9-TRACEABILITY.md
[mkt]: evaluation/department-study/V1-COVERAGE.md
[commission]: evaluation/campaign-engine/commission/README.md
[study]: evaluation/department-study/RESULTS.md
[pilot]: evaluation/department-study/PILOT.md
[engine]: evaluation/campaign-engine/README.md
[studio]: evaluation/studio-customer-assets/README.md
[factory]: evaluation/content-factory/README.md
[ops]: evaluation/sandbox-operations/README.md
[dispatch]: evaluation/sandbox-operations/channel-dispatch.json
[cutover]: evaluation/sandbox-operations/CUTOVER.md
[wf03]: ../catalog/research-strategy-v3.json
[wf13]: ../catalog/landing-seo-v6.json
