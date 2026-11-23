# Kiểm kê sản phẩm theo hiện vật

## 49 phân hệ

Mỗi dòng ghi phạm vi tối thiểu từ đặc tả và phần tìm thấy trong starter đã rà. Chưa phân hệ nào đủ bằng chứng nghiệm thu GA. Dòng ghi “Đặc tả” nghĩa là chưa thấy đường nghiệp vụ tương ứng trong API, model và UI.

| ID | Phân hệ | Phạm vi V1.0 | Bằng chứng / phần còn thiếu |
|---|---|---|---|
| SAA-01 | Website thương mại & đăng ký | Landing, mô tả dịch vụ, pricing, demo, đăng ký, onboarding, chính sách | Một phần · form đăng ký ở /, API trả 201. Thiếu website thương mại và onboarding theo gói. |
| SAA-02 | Identity/Access | Đăng nhập, mời người, MFA, SSO Enterprise, phiên/token, RBAC/ABAC, user-agent identities | Một phần · JWT/Argon2, kiểm tra thành viên/role. tests/test_api.py:33,132. Thiếu MFA, revoke, client grants. |
| SAA-03 | Tenant Lifecycle | tạo, ngừng, gia hạn, suspend, xóa/export, quota, dữ liệu vùng triển khai, consent | Một phần · tạo tenant hai mode, inhouse có client nội bộ. tests/test_api.py:114. Thiếu suspend/export. |
| SAA-04 | Company Builder | tạo AI company, phòng ban, sơ đồ, vai trò, tuyển agent, mô hình, ngân sách, skills | Danh mục · endpoint roles chỉ đọc, chưa có builder. |
| SAA-05 | Subscription & Billing | gói cước, entitlements, chu kỳ, invoice, thanh toán qua PSP hỗ trợ, công nợ, refund, trial/credit | Đặc tả. |
| SAA-06 | Usage & Cost | ledger chi phí token/model, compute, browser, tools, storage, thống kê theo tenant/brand/campaign | Đặc tả. |
| SAA-07 | Marketplace nội bộ | thư viện agent, skill, template, workflow đã kiểm duyệt, versioning, rollback; không mặc định mở marketplace tự do bên thứ ba | Đặc tả. |
| SAA-08 | Workspace / Team | phân quyền, hoạt động gần đây, thông báo, hồ sơ nhân sự AI, setting cá nhân và tổ chức | Một phần · admin thêm tài khoản đã đăng ký. app/main.py:109. Thiếu lời mời có chấp nhận. |
| SAA-09 | Support/Admin | help center, ticket, SLA, incident, audit, feature flag, cấu hình model, connector, giá nội bộ | Đặc tả. |
| AGY-01 | Client CRM | Lead, khách hàng, contact, ngành, status, yêu cầu, lịch sử tương tác | Một phần · tạo/liệt kê client. app/main.py:123. Thiếu CRM và lịch sử tương tác. |
| AGY-02 | Discovery & Brief | biểu mẫu khảo sát, phỏng vấn có cấu trúc, yêu cầu tài sản, xác nhận brief | Một phần · brief text trên campaign. app/schemas.py:29. Thiếu discovery và phiên bản brief. |
| AGY-03 | Commercial | proposal, service catalog, báo giá, SOW, order, hợp đồng, phụ lục, điều chỉnh phạm vi, client signoff | Đặc tả. |
| AGY-04 | Client Portal | hồ sơ dự án, tiến độ, lịch hẹn, xem/nhận tài sản, bình luận, yêu cầu sửa, phê duyệt | Đặc tả. |
| AGY-05 | Project/PMO | dự án, milestone, deadline, SLA, kế hoạch nguồn lực, dependency, workload, lịch biểu | Một phần · campaign + bảy task, gọi lại tuần tự tạo 0 task mới. tests/test_api.py:47. |
| AGY-06 | Account Operations | ghi chú, cuộc họp, task follow-up, health score, gia hạn, upsell, handoff | Đặc tả. |
| AGY-07 | Service Finance | ngân sách delivery, thời gian/AI cost, invoice phí dịch vụ agency, chốt đối soát, margin | Đặc tả. |
| AGY-08 | Feedback & Change | request sửa, lượt sửa, scope creep, change order, đánh giá chất lượng dịch vụ | Đặc tả. |
| MKT-01 | Market Intelligence | nghiên cứu khách, đối thủ, ngành, xu hướng, cơ hội; source citation/freshness/confidence | Đặc tả. |
| MKT-02 | Audience & Customer Journey | ICP, persona có nguồn, STP, phân khúc, journey, đề xuất kênh/hành trình | Đặc tả. |
| MKT-03 | Brand Management | Brand Kit, visual guidance, tone, product truth, approved/prohibited claims, đa ngôn ngữ | Một phần · brand_guidelines và product_truth là trường văn bản. app/models.py:48. Thiếu kiểm duyệt, phiên bản. |
| MKT-04 | Product Marketing & GTM | value proposition, messaging, positioning, competitor battlecard, kế hoạch ra mắt | Đặc tả. |
| MKT-05 | Marketing Strategy | annual/quarter/month strategy, 7P/4P khi thích hợp, objectives, budget, KPI, forecast scenario | Một phần · strategy lưu draft mock; đường gọi thật chưa đo. tests/test_api.py:156. |
| MKT-06 | Integrated Campaign | campaign brief, phân phối kênh, lịch, dependency, workback schedule, approval checkpoints | Một phần · tạo/đọc campaign và phân rã. app/main.py:156. Thiếu điều phối kênh và đo lường. |
| MKT-07 | Content & Editorial | topic cluster, content pillar, SEO brief, long/short-form copy, email, scripts, edits, A/B variants | Đặc tả. |
| MKT-08 | Creative Asset Studio | brief, image/video generation qua provider được cấp quyền, thiết kế template, version, DAM, license log | Đặc tả. |
| MKT-09 | Social & Community | calendar, lịch đăng, trạng thái tài khoản, moderation draft, reply review, social insights | Đặc tả. |
| MKT-10 | Paid Media / Ads | channel plan, audiences chính sách cho phép, campaign draft, budget, testing, read analytics, approved actions | Đặc tả. |
| MKT-11 | SEO/GEO | technical audit, content gap, keyword clusters, structured content, internal linking, Search Console, AI visibility hypotheses | Đặc tả. |
| MKT-12 | Website & CRO | landing-page brief/builder, tracking QA, funnel, heatmap/source nhập ngoài, experimentation, conversion backlog | Đặc tả. |
| MKT-13 | CRM & Lifecycle | CRM sync, lead enrichment permitted, segmentation, nurture, email journey, consent/opt-out, retention | Đặc tả. |
| MKT-14 | PR & Influence | media list, PR brief, press release draft, KOL research, outreach draft, rights/contract records, events | Đặc tả. |
| MKT-15 | Ecommerce/Trade | product feeds, merchandising content, promotion calendars, channel-specific listings, retail-media planning khi có quyền | Đặc tả. |
| MKT-16 | Marketing Data Hub | connectors, raw snapshots, normalized canonical metrics, lineage, QA, reconciliation, identity/consent controls | Đặc tả. |
| MKT-17 | Analytics & Attribution | dashboards, acquisition/funnel/conversion, MMM/attribution only where data supports, experiment readout | Đặc tả. |
| MKT-18 | Reporting & Intelligence | daily/weekly/monthly client report, narrative tied to evidence, anomalies, recommendations, export | Đặc tả. |
| MKT-19 | Budget & Optimization | marketing spend vs plan, rate/burn, alerts, ROI where properly attributed, optimization approval | Đặc tả. |
| MKT-20 | Localization & Regional | multi-market, language, currency, timezone, policy by channel and locale, translations under Brand Kit | Đặc tả. |
| AIO-01 | AI Director Command Center | chat theo mục tiêu, kế hoạch có cấu trúc, giao việc, điều chỉnh, trạng thái rõ ràng | Đặc tả. |
| AIO-02 | Orchestration | flow/event/task engine, parent-child, retries, checkpoints, idempotency, pause/resume/cancel | Khung · bảy bước cố định, chưa có worker/checkpoint. |
| AIO-03 | Agent Registry | vai trò, policy, model, skills, version, owner, health, eval, hiệu quả | Danh mục · 37 role cùng tools rỗng, chưa có assignment/version/runtime registry. |
| AIO-04 | Model Gateway | nhiều model/provider, routing, quota, fallback, latency/cost, redaction, provider health | Đặc tả. |
| AIO-05 | Tools/Connectors Gateway | MCP/API/OAuth, action classification, permission check, resource scope, secret broker | Đặc tả. |
| AIO-06 | Knowledge & Memory | documents, brand knowledge, source citation, embeddings, RBAC, freshness/TTL, unlearning/delete | Đặc tả. |
| AIO-07 | Human-in-the-loop | thông báo, approval queue, diff, preview, vai trò, SOW/side-effect gates | Một phần · submit/review, cấm tự duyệt theo user ID. tests/test_api.py:74,97. Thiếu khóa phiên bản. |
| AIO-08 | Artifact/Version | asset store, provenance, draft/review/approved/published, compare, restore, exports | Một phần · lưu deliverable JSON. app/models.py:82. Thiếu version, provenance và rollback. |
| AIO-09 | Evals & QA | chất lượng theo task, kiểm tra factual/brand/policy/schema, benchmark golden datasets | Đặc tả. |
| AIO-10 | Security & Audit | policy as code, prompt-injection containment, logs redacted, tamper-evident action receipts | Một phần · membership và audit sự kiện. app/main.py:296. Thiếu RLS và chống sửa log. |
| AIO-11 | Scheduling & Incident | cron/webhook triggers, queue, backoff, DLQ, recovery, runbooks, support escalation | Đặc tả. |
| AIO-12 | Usage Economics | pre-run cost estimation, reservation, hard-stop, post-run settlement, margin, anomaly alerts | Đặc tả. |

## 37 vai trò

Tất cả có status specification_only và tools rỗng. Cột cuối ghi tham chiếu tĩnh của planner. Chưa có vai trò nào được thực thi tự động.

| Nhóm | Vai trò | ID | Task có tham chiếu |
|---|---|---|---|
| Ban điều hành | AI Managing Director | ai-managing-director | — |
| Ban điều hành | AI Marketing Operations Director | ai-marketing-operations-director | — |
| Ban điều hành | AI Resource/Project Manager | ai-resource-project-manager | — |
| Ban điều hành | AI Executive Assistant | ai-executive-assistant | — |
| Khối khách hàng và kinh doanh | AI Business Development | ai-business-development | — |
| Khối khách hàng và kinh doanh | AI Solutions Consultant | ai-solutions-consultant | — |
| Khối khách hàng và kinh doanh | AI Account Director | ai-account-director | intake |
| Khối khách hàng và kinh doanh | AI Client Success | ai-client-success | — |
| Khối khách hàng và kinh doanh | AI Commercial/Proposal Specialist | ai-commercial-proposal-specialist | — |
| Khối Insights, Strategy & Brand | AI Market Researcher | ai-market-researcher | research |
| Khối Insights, Strategy & Brand | AI Consumer Insights Analyst | ai-consumer-insights-analyst | — |
| Khối Insights, Strategy & Brand | AI Competitor Intelligence | ai-competitor-intelligence | — |
| Khối Insights, Strategy & Brand | AI Marketing Strategist | ai-marketing-strategist | strategy |
| Khối Insights, Strategy & Brand | AI Brand Strategist | ai-brand-strategist | — |
| Khối Insights, Strategy & Brand | AI Product Marketing/GTM | ai-product-marketing-gtm | — |
| Khối Insights, Strategy & Brand | AI Customer Journey Planner | ai-customer-journey-planner | — |
| Khối Creative & Content | AI Creative Director | ai-creative-director | creative |
| Khối Creative & Content | AI Copywriter/Content Strategist | ai-copywriter-content-strategist | content (sau bản vá) |
| Khối Creative & Content | AI Social Content Specialist | ai-social-content-specialist | — |
| Khối Creative & Content | AI Visual Design | ai-visual-design | — |
| Khối Creative & Content | AI Video/Storyboard | ai-video-storyboard | — |
| Khối Creative & Content | AI Editorial/Localization | ai-editorial-localization | — |
| Khối Creative & Content | AI Digital Asset Librarian | ai-digital-asset-librarian | — |
| Khối Activation & Growth | AI Performance Media Planner | ai-performance-media-planner | — |
| Khối Activation & Growth | AI Google Ads Specialist | ai-google-ads-specialist | — |
| Khối Activation & Growth | AI Meta Ads Specialist | ai-meta-ads-specialist | — |
| Khối Activation & Growth | AI TikTok/LinkedIn Channel Specialist | ai-tiktok-linkedin-channel-specialist | — |
| Khối Activation & Growth | AI SEO/GEO Specialist | ai-seo-geo-specialist | — |
| Khối Activation & Growth | AI Website/CRO Specialist | ai-website-cro-specialist | — |
| Khối Activation & Growth | AI CRM/Lifecycle Specialist | ai-crm-lifecycle-specialist | — |
| Khối Activation & Growth | AI PR/Influencer/Event Coordinator | ai-pr-influencer-event-coordinator | — |
| Khối Data, Governance & Quality | AI Marketing Data Analyst | ai-marketing-data-analyst | reporting |
| Khối Data, Governance & Quality | AI Attribution/Experiment Analyst | ai-attribution-experiment-analyst | — |
| Khối Data, Governance & Quality | AI MarTech/Tracking Specialist | ai-martech-tracking-specialist | — |
| Khối Data, Governance & Quality | AI Content QA | ai-content-qa | quality |
| Khối Data, Governance & Quality | AI Policy/Brand Compliance | ai-policy-brand-compliance | — |
| Khối Data, Governance & Quality | AI Cost & Capacity Analyst | ai-cost-capacity-analyst | — |

## 24 quy trình

Cả 24 đều có status specification_only. Catalog được test số lượng. Chưa có runner nghiệm thu đầu-cuối. WF-02, WF-04 và WF-06 có một phần dữ liệu đầu vào hay sản phẩm trung gian trong starter.

| Quy trình | Trigger theo đặc tả | Điểm cần chứng minh khi nghiệm thu |
|---|---|---|
| WF-01 Lead-to-Client | lead/form/API | hợp đồng giá/điều khoản do người duyệt, chống trùng lead |
| WF-02 Brand Onboarding | khách đăng ký/khởi tạo brand | thiếu tài liệu = chờ bổ sung, không tạo sự thật giả |
| WF-03 Audit & Research | brief nghiên cứu | nguồn không truy cập = ghi 'không có dữ liệu' |
| WF-04 Annual/Quarter Strategy | business objective | gắn giả định, không bảo đảm tăng trưởng |
| WF-05 Product Launch/GTM | launch brief | thông số sản phẩm từ tài liệu chính thức |
| WF-06 Campaign Factory | approved strategy | quản lý phụ thuộc, scope, deadline |
| WF-07 Content Calendar | content brief | sửa có version, không xuất bản thiếu duyệt |
| WF-08 Creative & Video | approved creative brief | provider quota, tài sản đầu vào phải có quyền |
| WF-09 Social Publishing | approved assets + schedule | retry có idempotency; token hết hạn chờ reconnect |
| WF-10 Community & Reputation | inbound authorized comments | khiếu nại/khủng hoảng escalate |
| WF-11 SEO/GEO | website access | không tự đăng hàng loạt nội dung kém giá trị |
| WF-12 Ads Planning/Execution | campaign approval | chưa được API quyền = draft/export, không giả lập thành công |
| WF-13 Landing/CRO | conversion objective | production publish phải duyệt, rollback |
| WF-14 Lifecycle/CRM | consented segment/event | không gửi spam, không contact chưa có quyền |
| WF-15 PR/Influencer/Events | communications brief | KOL/giá/thỏa thuận cần người phê duyệt |
| WF-16 Ecommerce/Trade | catalog update/promo | giá/tồn từ source of truth |
| WF-17 Analytics Ingestion | schedule/API sync/CSV | lỗi nguồn phát cảnh báo, không bịa dữ liệu |
| WF-18 Marketing Reporting | period close | trace raw source, thiếu nguồn = null/not available |
| WF-19 Optimization Loop | performance anomaly | không tự chi vượt ngân sách |
| WF-20 Lead-to-Sales | qualified opt-in lead | privacy/consent, dữ liệu chuyển giao phải đúng quyền |
| WF-21 Client Feedback & Change | edit request | không làm tăng phạm vi không kiểm soát |
| WF-22 Incident & Recovery | error/provider outage/security | fail closed, không báo success giả |
| WF-23 Weekly/Monthly Operations | schedule | số liệu kiểm chứng, lịch đúng timezone |
| WF-24 Subscription Lifecycle | billing event | billing idempotency, ngừng agent theo policy |
