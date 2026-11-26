# Trạng thái hiện thực và nghiệm thu V1

**Cây tích hợp đang review.** Phần bổ sung sau mốc main gồm chuỗi #49–52, #54–55 và tài liệu quản trị #53. Sales/Service và các chỉ số RFQ được kiểm định với giao dịch tổng hợp. Pilot nghề nghiệp chỉ có bằng chứng thiết kế và diễn tập. Bằng chứng kỹ thuật thuộc nhánh review, chưa có quyết định nâng mức nghiệm thu nghiệp vụ của module, vai trò hoặc workflow nào. [Công việc hiện hành](../HANDOFF.md) · [Sổ năng lực trên checkout](evaluation/DEPARTMENT-CAPABILITY-REGISTER.md) · [Quyết định theo finding](evaluation/department-review/ROUND-53-55.md)

**Mốc đối chiếu ngày 26/11/2026** là `main` sau PR #48, commit `380be3eb70a41424c6d45318b0b1890fa950970a`, core v26, Business v3, C3 v5 và journal `ops/2`. Trên mốc này có bằng chứng tích hợp sandbox từ brief tới bản giao, QA, thực thi cục bộ và đối soát. Số yêu cầu **đầy đủ** có quyết định nghiệm thu nghiệp vụ ghi nhận trong hồ sơ là **0/49 module, 0/37 vai trò, 0/24 workflow**. Số đơn vị công việc được doanh nghiệp thực tiếp nhận trong các phép đo là **0**. Chi phí trên một đơn vị được tiếp nhận chưa xác định. Production và Commercial GA giữ **NO-GO**. [Commit nền][main] · [Cutover][cutover] · [Hồ sơ pilot][pilot] · [Điều kiện GA][ga]

## Cách đọc trạng thái

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

Trong các bảng dưới đây, **Thành phần** có nghĩa phần việc ghi ở dòng đó đã có mã trên main. Liên kết chỉ rõ mã, ca thử hoặc biên nhận hiện có. **Đặc tả** có nghĩa sổ này mới xác nhận được yêu cầu ở phạm vi nêu. Cả hai nhãn đều giữ mở quyết định nghiệp vụ toàn hàng. Thử kỹ thuật và tích hợp được ghi riêng cho đúng phiên bản.

## 49 module

Mỗi ID dưới đây tra được mô tả đầy đủ ở mục 3 của [đặc tả][prd]. Với nhóm ID chung dòng, phạm vi hoặc giới hạn áp dụng cho từng ID theo thứ tự ghi.

| ID | Trạng thái trên main | Phần đã có, phần còn mở và căn cứ |
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
| MKT-07, MKT-08 | Thành phần | Có lịch biên tập, brief ảnh/video, QA trường và snapshot. Đầu ra Creative trên main là brief phục vụ người thiết kế. File ảnh/video dựng được thuộc đề xuất #51 bên dưới. [Hai bộ tài liệu theo kênh][factory] |
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

Tất cả **37/37 ID** trong [catalog][roles] mang `specification_only` ở cấp vai trò đầy đủ. Bảng ánh xạ của runtime có **5 ID riêng biệt**. Ba lượt commission có biên nhận từng request và bản giao dừng ở `awaiting_qa`. Nghiên cứu hai brief khác ghi lại đầu ra trước/sau biên tập và các quyết định của tài khoản fixture. [Ánh xạ adapter](../app/registry_adapters.py) · [Biên nhận commission][commission] · [Nghiên cứu hai brief][study]

| ID | Phần việc được gọi trong runtime trên main |
|---|---|
| `ai-managing-director` | Lập phân công trong cả hai tiểu quy trình. [WF-03 @3][wf03] · [WF-13 @6][wf13] |
| `ai-market-researcher`, `ai-marketing-strategist` | Đọc nguồn ghim rồi soạn chiến lược trong WF-03. [Manifest][wf03] · [Ba request cho một brief](evaluation/campaign-engine/commission/acoustic-panel/strategy/commission-receipts.json) |
| `ai-copywriter-content-strategist`, `ai-seo-geo-specialist` | Soạn landing copy và metadata trong WF-13. [Manifest][wf13] · [Ba request cho một brief](evaluation/campaign-engine/commission/acoustic-panel/landing/commission-receipts.json) |

**32 ID còn lại** ở mức đặc tả vai trò, chưa có binding của chính ID trong bảng adapter trên main. Có thể tra nguyên văn từng ID dưới đây trong [catalog][roles]. Một chức danh ghi trong brief, tài khoản fixture, bước QA của người hoặc nội dung do bộ soạn theo quy tắc tạo ra không chứng minh agent tương ứng đã chạy.

| Nhóm tra cứu | ID |
|---|---|
| Điều hành, khách hàng | `ai-marketing-operations-director`, `ai-resource-project-manager`, `ai-executive-assistant`, `ai-business-development`, `ai-solutions-consultant`, `ai-account-director`, `ai-client-success`, `ai-commercial-proposal-specialist` |
| Nghiên cứu, chiến lược | `ai-consumer-insights-analyst`, `ai-competitor-intelligence`, `ai-brand-strategist`, `ai-product-marketing-gtm`, `ai-customer-journey-planner` |
| Nội dung, sáng tạo | `ai-creative-director`, `ai-social-content-specialist`, `ai-visual-design`, `ai-video-storyboard`, `ai-editorial-localization`, `ai-digital-asset-librarian` |
| Media, web, CRM, PR | `ai-performance-media-planner`, `ai-google-ads-specialist`, `ai-meta-ads-specialist`, `ai-tiktok-linkedin-channel-specialist`, `ai-website-cro-specialist`, `ai-crm-lifecycle-specialist`, `ai-pr-influencer-event-coordinator` |
| Đo lường, QA, kiểm soát | `ai-marketing-data-analyst`, `ai-attribution-experiment-analyst`, `ai-martech-tracking-specialist`, `ai-content-qa`, `ai-policy-brand-compliance`, `ai-cost-capacity-analyst` |

## 24 workflow nghiệp vụ

Tất cả **24/24 workflow mẹ** giữ nhãn catalog `specification_only`. Hai họ tiểu quy trình có manifest chạy, gồm `WF-03/research-strategy-draft@3` và `WF-13/landing-seo-draft@6` ở release C3 hiện hành. Phần mềm giữ các phiên bản cũ cho lịch sử và tương thích. Khi tra một ID bên dưới, đối chiếu phần đã chạy với trigger, các bước cuối và quy tắc duyệt trong [catalog][flows]. [Mã nhận dạng release](../app/c3_assets.py) · [Điều phối theo phiên bản](../app/c3_releases.py)

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

Ngày 26/11/2026, bốn PR dưới đây đang mở dưới dạng draft, xếp nối nhau. Mỗi dòng là hiện thực và bằng chứng kỹ thuật **trên nhánh đề xuất**. Kiểm lại merge commit, cây và CI trên main trước khi thay đổi trạng thái tương ứng ở trên.

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
