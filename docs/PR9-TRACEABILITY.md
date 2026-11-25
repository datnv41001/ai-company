# Ma trận truy vết V1.0 · Mốc 2846c174

B1–B8 AIRC sau PR #20 được kiểm theo ma trận engineering, riêng với chức năng Marketing sản phẩm. [Acceptance, journal và outbox](../engineering/airc500/UNION-STUDY.md).


Đối soát theo [PRD](PRODUCT_SPEC_V1.md), [37 vai trò](../catalog/agent_roles.json) và [24 workflow](../catalog/workflows.json). Đơn vị đếm là một yêu cầu đầy đủ. Tại mốc gốc, số hàng có đủ bằng chứng và quyết định `verified` trong ma trận là **0/49 module, 0/37 vai trò và 0/24 workflow**. Các luồng đã được nghiệm thu nội bộ ở v13 có bằng chứng riêng dưới đây. Không quy đổi tỷ lệ nghiệm thu thành phần trăm công sức đã hoàn thành.

## Cách đọc và cập nhật

Mỗi hàng có khóa PRD/catalog, tình trạng, bằng chứng thành phần và quyết định của reviewer cho toàn bộ hàng. Dấu **—** ở cột bằng chứng nghĩa là ma trận chưa liên kết bằng chứng thực thi cho hàng đó. Ở cột duyệt, **mở** nghĩa là đang thiếu quyết định nghiệm thu toàn bộ yêu cầu. `specification_only` là giá trị trong catalog hiện tại. `in_progress` ở một module ghi nhận bằng chứng thành phần. `not_started` trong cột nghiệm thu module nghĩa là chưa mở hồ sơ nghiệm thu module trong ma trận này.

Khi đưa hàng vào `in_review`, thay mã tham chiếu hoặc bổ sung một bộ bằng chứng gồm **ID yêu cầu + phiên bản, SHA/file hoặc API/UI, ID test và fixture, đầu ra mong đợi/thực tế, URL job CI và artifact, ngày, danh tính người duyệt và quyết định**. Chỉ chuyển thành `verified` cho phạm vi mà người duyệt ký xác nhận. Khi đổi version phải mở hồ sơ mới và giữ liên kết tới quyết định cũ. Reviewer kỹ thuật của #7/#8 duyệt phạm vi runtime trong trao đổi ngày 24/11/2026. Các hàng V1.0 còn mở dưới đây đều cần reviewer sản phẩm được phân công.

## Mã bằng chứng tại mốc gốc

| Mã | Khả năng đã đối chiếu | Mã và test | CI trên main |
|---|---|---|---|
| I | Đăng ký nội bộ, tenant, client và quyền đọc/ghi | [API](../app/main.py), [API tests](../tests/test_api.py), [client isolation](../tests/test_client_isolation.py) | [CI v13](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292737) |
| C | Đọc danh mục khai báo và kiểm tra trạng thái specification_only | [API catalog](../app/main.py), [test_role_and_workflow_spec_catalogs_are_not_claimed_implemented](../tests/test_api.py) | [CI v13](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292737) |
| B | Brief có nguồn, chuyên môn sinh bản nháp và đường giao QA | [Gateway](../app/workforce_gateway.py), [workforce tests](../tests/test_workforce.py), [Qwen và client approval](../tests/pool_model_smoke.py) | [Model v13](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292261) |
| D | Director lập graph, freeze và nhiều node theo dependency | [Compiler](../app/dynamic_plan.py), [freeze và replay](../tests/test_dynamic_execution.py) | [CI merge #7](https://github.com/datnv41001/ai-company/actions/runs/45307415696) |
| L | Hai lease, quyền worker, hold/receipt, retry và Join | [Node attempts](../app/node_attempts.py), [kiểm thử tài chính và fencing](../tests/test_node_leases.py) | [CI merge #8](https://github.com/datnv41001/ai-company/actions/runs/45308565924) |
| Q | Bằng chứng QA theo revision và snapshot khách duyệt | [QA](../app/revision_qa.py), [test QA](../tests/test_revision_evidence.py), [vòng đời bản giao](../tests/test_review_lifecycle.py) | [Chromium v13](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292624) |

## 49 module

| Yêu cầu | Module | Nghiệm thu | Bằng chứng | Ví dụ điều kiện còn mở | Duyệt |
|---|---|---|---|---|---|
| SAA-01 | Website thương mại & đăng ký | in_progress | I | [Onboarding nội bộ](PR16-ONBOARDING.md), hành trình thương mại còn mở | mở |
| SAA-02 | Identity/Access | in_progress | I · [PR #15, xác minh địa chỉ và chấp nhận lời mời](PR15-IDENTITY.md) · [test PostgreSQL](../tests/test_verified_identity.py) | PR #15 đã merge. [PR #16, tài khoản độc lập và lời mời qua email tổng hợp](PR16-ONBOARDING.md) chờ review. MFA/SSO và quản lý phiên còn mở | mở |
| SAA-03 | Tenant Lifecycle | in_progress | I | [Tạo workspace chủ động](PR16-ONBOARDING.md). Suspend, phục hồi và xóa/export tenant | mở |
| SAA-04 | Company Builder | in_progress | C | Cấu hình vai trò, version và kích hoạt đúng workspace | mở |
| SAA-05 | Subscription & Billing | not_started | — | Hóa đơn, gia hạn, hoàn tiền và đối soát PSP | mở |
| SAA-06 | Usage & Cost | in_progress | L | Phân bổ đủ loại compute, storage, tool và phí nhà cung cấp | mở |
| SAA-07 | Marketplace nội bộ | not_started | — | Phát hành, quyền cài và rollback gói nội bộ | mở |
| SAA-08 | Workspace / Team | in_progress | I · [Mời và nhận vai trò trong workspace](PR15-IDENTITY.md) | [Lời mời trước đăng ký](PR16-ONBOARDING.md). Còn vòng đời thành viên và thiết lập workspace | mở |
| SAA-09 | Support/Admin | not_started | — | Quy trình support, incident, SLA | mở |
| AGY-01 | Client CRM | in_progress | I | Danh bạ, lead và lịch sử dịch vụ | mở |
| AGY-02 | Discovery & Brief | in_progress | B | Khảo sát, yêu cầu tài sản và nguồn brief có phiên bản | mở |
| AGY-03 | Commercial | not_started | — | Phê duyệt SOW, giá và hợp đồng | mở |
| AGY-04 | Client Portal | in_progress | Q · [Lời mời cho đúng client](../tests/test_recipients.py) | [Nhận quyền portal từ link](PR16-ONBOARDING.md). Còn hành trình portal đầy đủ | mở |
| AGY-05 | Project/PMO | in_progress | D | Mốc dự án, SLA và năng lực nguồn lực | mở |
| AGY-06 | Account Operations | not_started | — | Vận hành inbox, health score và handoff khách | mở |
| AGY-07 | Service Finance | not_started | — | Invoice phí dịch vụ và biên lợi nhuận | mở |
| AGY-08 | Feedback & Change | in_progress | Q | Tác động scope/giá và chấp thuận change order | mở |
| MKT-01 | Market Intelligence | in_progress | B | Độ mới, đối chiếu nguồn và báo cáo nghiên cứu | mở |
| MKT-02 | Audience & Customer Journey | not_started | — | Phân khúc có bằng chứng và journey theo persona | mở |
| MKT-03 | Brand Management | in_progress | B | Version Brand Kit, quyền nguồn và ảnh hưởng khi sửa | mở |
| MKT-04 | Product Marketing & GTM | not_started | — | GTM nối dữ liệu sản phẩm với launch và đo lường | mở |
| MKT-05 | Marketing Strategy | in_progress | B | Chiến lược được duyệt với giả định, KPI và ngân sách | mở |
| MKT-06 | Integrated Campaign | in_progress | D | Chiến dịch đa kênh hoàn chỉnh từ mục tiêu tới đo lường | mở |
| MKT-07 | Content & Editorial | in_progress | B,Q | Lịch biên tập, quyền tác giả và duyệt theo kênh | mở |
| MKT-08 | Creative Asset Studio | not_started | — | Quyền tài sản, render và nghiệm thu media | mở |
| MKT-09 | Social & Community | not_started | — | Kênh có quyền, moderation và escalation | mở |
| MKT-10 | Paid Media / Ads | not_started | — | Đối soát chi quảng cáo, phê duyệt và receipt nền tảng | mở |
| MKT-11 | SEO/GEO | in_progress | D,B | Audit có quyền, metadata, đề xuất và cập nhật CMS được duyệt | mở |
| MKT-12 | Website & CRO | not_started | — | Thử nghiệm chuyển đổi và rollback trang thật | mở |
| MKT-13 | CRM & Lifecycle | not_started | — | Consent, phân khúc và dừng gửi | mở |
| MKT-14 | PR & Influence | not_started | — | Hợp đồng, quyền và kết quả sự kiện | mở |
| MKT-15 | Ecommerce/Trade | not_started | — | Giá, tồn kho, giao dịch có nguồn | mở |
| MKT-16 | Marketing Data Hub | not_started | — | Ingestion có lineage và xử lý mất nguồn | mở |
| MKT-17 | Analytics & Attribution | not_started | — | Tái lập số liệu và phân bổ với giả định | mở |
| MKT-18 | Reporting & Intelligence | not_started | — | Báo cáo có nguồn, kỳ và trạng thái thiếu dữ liệu | mở |
| MKT-19 | Budget & Optimization | not_started | — | Đối soát ngân sách Marketing và quyết định điều chỉnh | mở |
| MKT-20 | Localization & Regional | not_started | — | QA ngôn ngữ, thị trường và phê duyệt địa phương | mở |
| AIO-01 | AI Director Command Center | in_progress | D | Điều phối chuyên môn và truy vết quyết định theo hợp đồng | mở |
| AIO-02 | Orchestration | in_progress | D,L | Bằng chứng tải, phục hồi và chất lượng nhiều workflow | mở |
| AIO-03 | Agent Registry | in_progress | C | Manifest phiên bản, policy scope và kiểm thử bốn skill | mở |
| AIO-04 | Model Gateway | in_progress | B | Hạn mức, fallback, chất lượng và đối soát provider | mở |
| AIO-05 | Tools/Connectors Gateway | not_started | — | Adapter có scope, phê duyệt và receipt của từng hành động | mở |
| AIO-06 | Knowledge & Memory | in_progress | B | Lineage, độ mới, retention và thu hồi nguồn | mở |
| AIO-07 | Human-in-the-loop | in_progress | Q | Chính sách duyệt đầy đủ theo vai trò và tác động | mở |
| AIO-08 | Artifact/Version | in_progress | Q | Version, lineage, export và quyền trên từng loại tài sản | mở |
| AIO-09 | Evals & QA | in_progress | Q | Bộ eval theo role có gold fixture và reviewer nghiệp vụ | mở |
| AIO-10 | Security & Audit | in_progress | I,L · [Audit khi hai giao dịch tranh cùng lời mời](../tests/test_verified_identity.py) | [Kiểm tra chữ ký theo mục đích](PR16-ONBOARDING.md). Còn kiểm định toàn bộ ranh giới và phục hồi audit | mở |
| AIO-11 | Scheduling & Incident | in_progress | L | Diễn tập sự cố, restore và tải có bằng chứng | mở |
| AIO-12 | Usage Economics | in_progress | L | Chi phí ngoài inference, quota và economics thực đo | mở |

## 37 vai trò logic

Các liên kết D/B/Q dưới đây chỉ đến công việc runtime liên quan. Hồ sơ vai trò cần thêm hợp đồng có phiên bản, quyền hiệu lực, QA đặc thù và E2E đúng nhiệm vụ. Bốn skill chuyên môn được đề xuất đầu tiên có tiêu chí riêng trong [thiết kế](PR9-AGENT-CONTRACTS-WORKFLOW-REGISTRY.md).

| Role ID | Tên trong catalog | Trạng thái catalog | Bằng chứng liên quan | Duyệt |
|---|---|---|---|---|
| ai-managing-director | AI Managing Director | specification_only | D | mở |
| ai-marketing-operations-director | AI Marketing Operations Director | specification_only | — | mở |
| ai-resource-project-manager | AI Resource/Project Manager | specification_only | — | mở |
| ai-executive-assistant | AI Executive Assistant | specification_only | — | mở |
| ai-business-development | AI Business Development | specification_only | — | mở |
| ai-solutions-consultant | AI Solutions Consultant | specification_only | — | mở |
| ai-account-director | AI Account Director | specification_only | — | mở |
| ai-client-success | AI Client Success | specification_only | — | mở |
| ai-commercial-proposal-specialist | AI Commercial/Proposal Specialist | specification_only | — | mở |
| ai-market-researcher | AI Market Researcher | specification_only | B | mở |
| ai-consumer-insights-analyst | AI Consumer Insights Analyst | specification_only | — | mở |
| ai-competitor-intelligence | AI Competitor Intelligence | specification_only | — | mở |
| ai-marketing-strategist | AI Marketing Strategist | specification_only | B | mở |
| ai-brand-strategist | AI Brand Strategist | specification_only | — | mở |
| ai-product-marketing-gtm | AI Product Marketing/GTM | specification_only | — | mở |
| ai-customer-journey-planner | AI Customer Journey Planner | specification_only | — | mở |
| ai-creative-director | AI Creative Director | specification_only | — | mở |
| ai-copywriter-content-strategist | AI Copywriter/Content Strategist | specification_only | B,Q | mở |
| ai-social-content-specialist | AI Social Content Specialist | specification_only | — | mở |
| ai-visual-design | AI Visual Design | specification_only | — | mở |
| ai-video-storyboard | AI Video/Storyboard | specification_only | — | mở |
| ai-editorial-localization | AI Editorial/Localization | specification_only | — | mở |
| ai-digital-asset-librarian | AI Digital Asset Librarian | specification_only | — | mở |
| ai-performance-media-planner | AI Performance Media Planner | specification_only | — | mở |
| ai-google-ads-specialist | AI Google Ads Specialist | specification_only | — | mở |
| ai-meta-ads-specialist | AI Meta Ads Specialist | specification_only | — | mở |
| ai-tiktok-linkedin-channel-specialist | AI TikTok/LinkedIn Channel Specialist | specification_only | — | mở |
| ai-seo-geo-specialist | AI SEO/GEO Specialist | specification_only | D,B | mở |
| ai-website-cro-specialist | AI Website/CRO Specialist | specification_only | — | mở |
| ai-crm-lifecycle-specialist | AI CRM/Lifecycle Specialist | specification_only | — | mở |
| ai-pr-influencer-event-coordinator | AI PR/Influencer/Event Coordinator | specification_only | — | mở |
| ai-marketing-data-analyst | AI Marketing Data Analyst | specification_only | — | mở |
| ai-attribution-experiment-analyst | AI Attribution/Experiment Analyst | specification_only | — | mở |
| ai-martech-tracking-specialist | AI MarTech/Tracking Specialist | specification_only | — | mở |
| ai-content-qa | AI Content QA | specification_only | — | mở |
| ai-policy-brand-compliance | AI Policy/Brand Compliance | specification_only | — | mở |
| ai-cost-capacity-analyst | AI Cost & Capacity Analyst | specification_only | — | mở |

## 24 workflow nghiệp vụ

Cột điều kiện trích từ quy tắc duyệt và xử lý lỗi trong catalog. Nghiệm thu một hàng đòi hỏi chạy từ trigger tới kết quả cuối của workflow và ghi được quyết định người duyệt. [Thiết kế `WF-13/landing-seo-draft@1`](PR9-AGENT-CONTRACTS-WORKFLOW-REGISTRY.md) là tiểu quy trình soạn bản nháp của WF-13 Landing/CRO. Phần SEO metadata liên kết WF-11 SEO/GEO và module MKT-11. Cả hai workflow mẹ tiếp tục ở `specification_only`. Tiểu quy trình dùng mã riêng trong registry đề xuất và không thêm hàng vào 110 yêu cầu gốc.

| ID | Workflow | Trạng thái catalog | Bằng chứng liên quan | Điều kiện nghiệp vụ | Duyệt |
|---|---|---|---|---|---|
| WF-01 | Lead-to-Client | specification_only | — | hợp đồng giá/điều khoản do người duyệt, chống trùng lead | mở |
| WF-02 | Brand Onboarding | specification_only | B | thiếu tài liệu = chờ bổ sung, không tạo sự thật giả | mở |
| WF-03 | Audit & Research | specification_only | B | nguồn không truy cập = ghi 'không có dữ liệu' | mở |
| WF-04 | Annual/Quarter Strategy | specification_only | B | gắn giả định, không bảo đảm tăng trưởng | mở |
| WF-05 | Product Launch/GTM | specification_only | — | thông số sản phẩm từ tài liệu chính thức | mở |
| WF-06 | Campaign Factory | specification_only | D | quản lý phụ thuộc, scope, deadline | mở |
| WF-07 | Content Calendar | specification_only | Q | sửa có version, không xuất bản thiếu duyệt | mở |
| WF-08 | Creative & Video | specification_only | — | provider quota, tài sản đầu vào phải có quyền | mở |
| WF-09 | Social Publishing | specification_only | — | retry có idempotency; token hết hạn chờ reconnect | mở |
| WF-10 | Community & Reputation | specification_only | — | khiếu nại/khủng hoảng escalate | mở |
| WF-11 | SEO/GEO | specification_only | D,B | không tự đăng hàng loạt nội dung kém giá trị | mở |
| WF-12 | Ads Planning/Execution | specification_only | — | chưa được API quyền = draft/export, không giả lập thành công | mở |
| WF-13 | Landing/CRO | specification_only | — | production publish phải duyệt, rollback | mở |
| WF-14 | Lifecycle/CRM | specification_only | — | không gửi spam, không contact chưa có quyền | mở |
| WF-15 | PR/Influencer/Events | specification_only | — | KOL/giá/thỏa thuận cần người phê duyệt | mở |
| WF-16 | Ecommerce/Trade | specification_only | — | giá/tồn từ source of truth | mở |
| WF-17 | Analytics Ingestion | specification_only | — | lỗi nguồn phát cảnh báo, không bịa dữ liệu | mở |
| WF-18 | Marketing Reporting | specification_only | — | trace raw source, thiếu nguồn = null/not available | mở |
| WF-19 | Optimization Loop | specification_only | — | không tự chi vượt ngân sách | mở |
| WF-20 | Lead-to-Sales | specification_only | — | privacy/consent, dữ liệu chuyển giao phải đúng quyền | mở |
| WF-21 | Client Feedback & Change | specification_only | Q | không làm tăng phạm vi không kiểm soát | mở |
| WF-22 | Incident & Recovery | specification_only | L | fail closed, không báo success giả | mở |
| WF-23 | Weekly/Monthly Operations | specification_only | — | số liệu kiểm chứng, lịch đúng timezone | mở |
| WF-24 | Subscription Lifecycle | specification_only | — | billing idempotency, ngừng agent theo policy | mở |

## Bằng chứng bổ sung cho nền tảng danh tính

Hạng mục onboarding có nhánh v21 chờ review cho admission theo tài khoản, tenant, người nhận và nguồn kết nối. Điểm kiểm chứng gồm hồi quy SQLite/PostgreSQL, giới hạn đồng thời, Chromium và đường nâng cấp từ v20. [Hợp đồng và giới hạn](IDENTITY-ADMISSION.md).

## Business Profile C0 · phạm vi thiết kế

MKT-03, MKT-20 và AIO-06 có bổ sung nền backend C1 tại schema v22. Các ca đo gồm 29 kiểm thử thực thi trên PostgreSQL/SQLite, CAS, quyền theo scope, giá thương mại, thu hồi nguồn trước/sau QA/share và tái lập snapshot. WF-03 và WF-13 vẫn dùng các adapter đã ghim. C2–C4 tiếp nhận giao diện, adapter phiên bản mới và đánh giá nghiệp vụ. [Ma trận 16 tiêu chí, mã kiểm thử và cách chạy](business-profile/C1-RUNBOOK.md)

MKT-03 Brand Management, MKT-20 Localization & Regional và AIO-06 Knowledge & Memory có [hợp đồng C0 và fixture](business-profile/README.md) cho dữ kiện theo sản phẩm/variant/market, source revision và hiệu lực khi share. WF-03/WF-13 tiếp tục dùng các release đã duyệt đến khi C1/C3 chứng minh adapter mới. Nhãn tiến độ là design + synthetic contract checks; tính năng và business acceptance còn chờ.

## SAA-02 · session và recovery

[Thiết kế và tiêu chí nghiệm thu](IDENTITY-SESSION-RECOVERY.md) bao gồm thu hồi giữa hai worker, recovery khi cooldown, xoay khóa và so sánh OIDC. Những gate này chờ triển khai và kiểm thử độc lập.
