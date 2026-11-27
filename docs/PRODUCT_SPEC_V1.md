# AI MARKETING COMPANY — FULL COMMERCIAL PRODUCT V1.0

**Ngày định hướng:** 23/11/2026  
**Loại tài liệu:** Product Requirements Document (PRD) + Solution Architecture + Functional Coverage + Operating Model + Acceptance Framework  
**Trạng thái:** BẢN ĐẶC TẢ SẢN PHẨM ĐẦY ĐỦ — CHƯA PHẢI PHẦN MỀM ĐÃ XÂY DỰNG, CHƯA ĐƯỢC CHỨNG NHẬN PRODUCTION  
**Quyết định phạm vi:** Một sản phẩm hoàn chỉnh, một lần nghiệm thu thương mại (General Availability), KHÔNG chia thành nhiều MVP / không công bố chức năng dở dang là đã hoàn thành.

## 0. Product charter — các nguyên tắc không được thay đổi âm thầm

Dùng tôn chỉ chính thức khi lựa chọn năng lực và nghiệm thu giá trị đối với khách hàng. Các module và workflow trong đặc tả này cung cấp phạm vi để đối chiếu. [Product Mission & Commercial North Star](PRODUCT_MISSION.md)

1. Chỉ phát triển **AI Marketing Company**: phần mềm công ty Marketing vận hành với đội ngũ AI Agent; không xây công ty đa ngành ngoài Marketing. Phục vụ khách hàng ở nhiều ngành.
2. Phần mềm dùng cho hai chế độ **Agency Mode** (agency cung cấp dịch vụ cho nhiều khách) và **In-house Mode** (phòng Marketing AI của doanh nghiệp). Một bộ máy chuyên môn, hai mô hình quản trị.
3. Kinh doanh **B2B SaaS multi-tenant**; có thể có Private Deployment/Enterprise và white-label sau đánh giá hợp đồng.
4. **Không chỉ có chat:** AI phải hoàn thành công việc, có hồ sơ đầu vào, tài sản đầu ra, nguồn dữ liệu, người duyệt, lịch sử, KPI, giá thành.
5. Bản thương mại là **full scope** theo danh mục của tài liệu này. Có thể triển khai kỹ thuật theo luồng phụ thuộc, nhưng không chia nhỏ các sản phẩm phát hành với nhãn MVP.
6. **Con người giữ trách nhiệm quyết định:** hành động công khai, chi tiêu quảng cáo, giao dịch, gửi hàng loạt, xóa dữ liệu hoặc thay đổi tài sản quan trọng phải theo quyền được cấp và chính sách phê duyệt.
7. **Không được tuyên bố sai về tích hợp:** chỉ đánh dấu tính năng là hỗ trợ trực tiếp sau khi API, app review, quyền người dùng, quota và E2E test thành công. Trường hợp chưa có quyền, hỗ trợ quy trình thủ công/export hoặc ghi rõ không khả dụng. Không vượt chính sách nền tảng.
8. **Thiết kế theo quyền dữ liệu:** tách biệt tuyệt đối tenant, khách hàng agency, thương hiệu, nguồn tri thức, file, secrets, logs, dòng chi phí.
9. **Giấy phép:** chỉ nhúng/fork mã nguồn cho phép kinh doanh thương mại theo phương thức được chọn; không suy ra quyền host SaaS từ việc được xem source.
10. Mọi thay đổi phạm vi yêu cầu quyết định được ghi trong Decision Log. Bản cũ 'AI Company SaaS + Marketing Agency' 0.1 chỉ làm tài liệu tham khảo; bản này là charter mới.

## 1. Sản phẩm và lời hứa giá trị

**Tên sản phẩm tạm:** AI Marketing Company (AMC). Tên thương mại/chủ sở hữu nhãn hiệu phải tra cứu trước khi phát hành.

**Định nghĩa:** Nền tảng cho phép tổ chức hoặc agency thuê một đội Marketing AI có thể nhận brief, nghiên cứu, lập chiến lược, quản lý thương hiệu, tạo tài sản, phối hợp công việc, thực hiện công việc trên ứng dụng được cho phép, lấy và phân tích số liệu, báo cáo, tối ưu, phục vụ khách hàng, chịu các ràng buộc về chi phí/phê duyệt/bảo mật.

**Không cam kết:** doanh thu được bảo đảm; thay thế mọi nhân sự; mọi quảng cáo tự đăng ngay; mọi nội dung tạo tự động đều có bản quyền riêng; đáp ứng mọi quy định pháp luật ở mọi nơi mà không cần tư vấn.

**North-star metric:** số 'Business-accepted Marketing Work Units' trong kỳ (nhiệm vụ/kết quả Marketing được khách hàng phê duyệt hoặc tự động hoàn tất theo tiêu chí đã duyệt), đi kèm đo thời gian tiết kiệm và chi phí thực hiện.

### 1.1. Người sử dụng chính

| Persona | Mục tiêu | Những màn hình/quyền quan trọng |
|---|---|---|
| Platform Super Admin | quản trị SaaS, thuê bao, biên lợi nhuận, bảo mật | Tenant, Billing, Incident, Support, Models, Feature Controls |
| Agency Owner/Managing Director | quản lý nhiều khách, dịch vụ, chi phí, đội Marketing | Company Dashboard, Accounts, Projects, SOW, Finance |
| CMO/Head of Marketing | điều phối Marketing nội bộ, ngân sách, chiến lược | Strategy, Brand, Campaigns, Approvals, KPI |
| Account Manager | nhận brief, chăm khách, bàn giao, xử lý yêu cầu thay đổi | Client Portal, Account Inbox, Scope/Changes |
| Content/Creative Editor | xem, chỉnh, duyệt, xuất bản tài sản | Studio, DAM, Calendar, Review |
| Ads Specialist | kiểm soát media plan, chiến dịch, hiệu suất | Ads Workbench, Spend Controls, Analytics |
| Client Reviewer/Approver | duyệt đầu ra và ngân sách của thương hiệu | Client Portal, Proof, Approvals |
| Analyst | quản lý dữ liệu, chuẩn đo lường, kiểm chứng báo cáo | Analytics, Data Quality, Attribution |
| AI Agent identity | thực thi đúng task, scope, công cụ, ngân sách | Policy-limited tool/API access; audit every side effect |

### 1.2. Cây thực thể phân quyền

Platform -> Tenant/Organization -> Workspace/AI Company -> (Agency Client Account) -> Brand -> Product/Service -> Goal/Strategy -> Campaign -> Project -> Task -> Agent Run -> Artifact/Action -> Review/Approval -> Evidence/Metrics.

Trong In-house Mode, `Client Account` có thể là bộ phận kinh doanh/đơn vị trong cùng tổ chức. Trong Agency Mode, `Client Account` là khách agency; một khách có thể có nhiều Brand. Không dùng `company_id` thay thế cho `tenant_id` trong toàn bộ hệ thống nếu hai khái niệm mang phạm vi khác nhau.

## 2. Cơ cấu tổ chức Marketing AI hoàn chỉnh

**Ban điều hành (4):** AI Managing Director; AI Marketing Operations Director; AI Resource/Project Manager; AI Executive Assistant.

**Khối khách hàng và kinh doanh (5):** AI Business Development; AI Solutions Consultant; AI Account Director; AI Client Success; AI Commercial/Proposal Specialist.

**Khối Insights, Strategy & Brand (7):** AI Market Researcher; AI Consumer Insights Analyst; AI Competitor Intelligence; AI Marketing Strategist; AI Brand Strategist; AI Product Marketing/GTM; AI Customer Journey Planner.

**Khối Creative & Content (7):** AI Creative Director; AI Copywriter/Content Strategist; AI Social Content Specialist; AI Visual Design; AI Video/Storyboard; AI Editorial/Localization; AI Digital Asset Librarian.

**Khối Activation & Growth (8):** AI Performance Media Planner; AI Google Ads Specialist; AI Meta Ads Specialist; AI TikTok/LinkedIn Channel Specialist; AI SEO/GEO Specialist; AI Website/CRO Specialist; AI CRM/Lifecycle Specialist; AI PR/Influencer/Event Coordinator.

**Khối Data, Governance & Quality (6):** AI Marketing Data Analyst; AI Attribution/Experiment Analyst; AI MarTech/Tracking Specialist; AI Content QA; AI Policy/Brand Compliance; AI Cost & Capacity Analyst.

**Tổng:** 37 **vai trò logic** — không phải 37 process độc lập hay 37 thuê bao LLM. Vai trò và cấp quản lý có thể cấu hình, ghép hoặc mở rộng. Mỗi vai trò bắt buộc có Agent Contract.

### 2.1. Agent Contract (bắt buộc với mọi vai trò)

`role_id, display_name, reports_to, objective, success_metric, input_schema, required_knowledge, allowed_tools, denied_actions, model_profile, compute_budget, max_iterations, timeout, output_schema, qa_policy, approval_policy, fallback, escalation_target, version, owner`.

Mỗi agent chạy theo **Task Contract**: mục tiêu, phạm vi, nguồn dữ liệu và timestamp, điều kiện bắt đầu/dừng, ngân sách, phụ thuộc, tài sản cần giao, cách kiểm chứng, ai duyệt. AI có thể đề xuất cách thực thi nhưng không tự ý nới quyền hoặc tiền.

## 3. FULL PRODUCT MODULE MATRIX — bắt buộc cho General Availability

### 3.1. SaaS & Organization (SAA)

| ID | Module | Phạm vi chức năng bắt buộc |
|---|---|---|
| SAA-01 | Website thương mại & đăng ký | Landing, mô tả dịch vụ, pricing, demo, đăng ký, onboarding, chính sách |
| SAA-02 | Identity/Access | Đăng nhập, mời người, MFA, SSO Enterprise, phiên/token, RBAC/ABAC, user-agent identities |
| SAA-03 | Tenant Lifecycle | tạo, ngừng, gia hạn, suspend, xóa/export, quota, dữ liệu vùng triển khai, consent |
| SAA-04 | Company Builder | tạo AI company, phòng ban, sơ đồ, vai trò, tuyển agent, mô hình, ngân sách, skills |
| SAA-05 | Subscription & Billing | gói cước, entitlements, chu kỳ, invoice, thanh toán qua PSP hỗ trợ, công nợ, refund, trial/credit |
| SAA-06 | Usage & Cost | ledger chi phí token/model, compute, browser, tools, storage, thống kê theo tenant/brand/campaign |
| SAA-07 | Marketplace nội bộ | thư viện agent, skill, template, workflow đã kiểm duyệt, versioning, rollback; không mặc định mở marketplace tự do bên thứ ba |
| SAA-08 | Workspace / Team | phân quyền, hoạt động gần đây, thông báo, hồ sơ nhân sự AI, setting cá nhân và tổ chức |
| SAA-09 | Support/Admin | help center, ticket, SLA, incident, audit, feature flag, cấu hình model, connector, giá nội bộ |

### 3.2. Agency Operations (AGY)

| ID | Module | Phạm vi chức năng bắt buộc |
|---|---|---|
| AGY-01 | Client CRM | Lead, khách hàng, contact, ngành, status, yêu cầu, lịch sử tương tác |
| AGY-02 | Discovery & Brief | biểu mẫu khảo sát, phỏng vấn có cấu trúc, yêu cầu tài sản, xác nhận brief |
| AGY-03 | Commercial | proposal, service catalog, báo giá, SOW, order, hợp đồng, phụ lục, điều chỉnh phạm vi, client signoff |
| AGY-04 | Client Portal | hồ sơ dự án, tiến độ, lịch hẹn, xem/nhận tài sản, bình luận, yêu cầu sửa, phê duyệt |
| AGY-05 | Project/PMO | dự án, milestone, deadline, SLA, kế hoạch nguồn lực, dependency, workload, lịch biểu |
| AGY-06 | Account Operations | ghi chú, cuộc họp, task follow-up, health score, gia hạn, upsell, handoff |
| AGY-07 | Service Finance | ngân sách delivery, thời gian/AI cost, invoice phí dịch vụ agency, chốt đối soát, margin |
| AGY-08 | Feedback & Change | request sửa, lượt sửa, scope creep, change order, đánh giá chất lượng dịch vụ |

### 3.3. Marketing Professional Suite (MKT)

| ID | Domain | Chức năng đầy đủ trong V1.0 |
|---|---|---|
| MKT-01 | Market Intelligence | nghiên cứu khách, đối thủ, ngành, xu hướng, cơ hội; source citation/freshness/confidence |
| MKT-02 | Audience & Customer Journey | ICP, persona có nguồn, STP, phân khúc, journey, đề xuất kênh/hành trình |
| MKT-03 | Brand Management | Brand Kit, visual guidance, tone, product truth, approved/prohibited claims, đa ngôn ngữ |
| MKT-04 | Product Marketing & GTM | value proposition, messaging, positioning, competitor battlecard, kế hoạch ra mắt |
| MKT-05 | Marketing Strategy | annual/quarter/month strategy, 7P/4P khi thích hợp, objectives, budget, KPI, forecast scenario |
| MKT-06 | Integrated Campaign | campaign brief, phân phối kênh, lịch, dependency, workback schedule, approval checkpoints |
| MKT-07 | Content & Editorial | topic cluster, content pillar, SEO brief, long/short-form copy, email, scripts, edits, A/B variants |
| MKT-08 | Creative Asset Studio | brief, image/video generation qua provider được cấp quyền, thiết kế template, version, DAM, license log |
| MKT-09 | Social & Community | calendar, lịch đăng, trạng thái tài khoản, moderation draft, reply review, social insights |
| MKT-10 | Paid Media / Ads | channel plan, audiences chính sách cho phép, campaign draft, budget, testing, read analytics, approved actions |
| MKT-11 | SEO/GEO | technical audit, content gap, keyword clusters, structured content, internal linking, Search Console, AI visibility hypotheses |
| MKT-12 | Website & CRO | landing-page brief/builder, tracking QA, funnel, heatmap/source nhập ngoài, experimentation, conversion backlog |
| MKT-13 | CRM & Lifecycle | CRM sync, lead enrichment permitted, segmentation, nurture, email journey, consent/opt-out, retention |
| MKT-14 | PR & Influence | media list, PR brief, press release draft, KOL research, outreach draft, rights/contract records, events |
| MKT-15 | Ecommerce/Trade | product feeds, merchandising content, promotion calendars, channel-specific listings, retail-media planning khi có quyền |
| MKT-16 | Marketing Data Hub | connectors, raw snapshots, normalized canonical metrics, lineage, QA, reconciliation, identity/consent controls |
| MKT-17 | Analytics & Attribution | dashboards, acquisition/funnel/conversion, MMM/attribution only where data supports, experiment readout |
| MKT-18 | Reporting & Intelligence | daily/weekly/monthly client report, narrative tied to evidence, anomalies, recommendations, export |
| MKT-19 | Budget & Optimization | marketing spend vs plan, rate/burn, alerts, ROI where properly attributed, optimization approval |
| MKT-20 | Localization & Regional | multi-market, language, currency, timezone, policy by channel and locale, translations under Brand Kit |

### 3.4. AI Operating System (AIO)

| ID | Module | Chức năng bắt buộc |
|---|---|---|
| AIO-01 | AI Director Command Center | chat theo mục tiêu, kế hoạch có cấu trúc, giao việc, điều chỉnh, trạng thái rõ ràng |
| AIO-02 | Orchestration | flow/event/task engine, parent-child, retries, checkpoints, idempotency, pause/resume/cancel |
| AIO-03 | Agent Registry | vai trò, policy, model, skills, version, owner, health, eval, hiệu quả |
| AIO-04 | Model Gateway | nhiều model/provider, routing, quota, fallback, latency/cost, redaction, provider health |
| AIO-05 | Tools/Connectors Gateway | MCP/API/OAuth, action classification, permission check, resource scope, secret broker |
| AIO-06 | Knowledge & Memory | documents, brand knowledge, source citation, embeddings, RBAC, freshness/TTL, unlearning/delete |
| AIO-07 | Human-in-the-loop | thông báo, approval queue, diff, preview, vai trò, SOW/side-effect gates |
| AIO-08 | Artifact/Version | asset store, provenance, draft/review/approved/published, compare, restore, exports |
| AIO-09 | Evals & QA | chất lượng theo task, kiểm tra factual/brand/policy/schema, benchmark golden datasets |
| AIO-10 | Security & Audit | policy as code, prompt-injection containment, logs redacted, tamper-evident action receipts |
| AIO-11 | Scheduling & Incident | cron/webhook triggers, queue, backoff, DLQ, recovery, runbooks, support escalation |
| AIO-12 | Usage Economics | pre-run cost estimation, reservation, hard-stop, post-run settlement, margin, anomaly alerts |

**Ghi chú tích hợp:** một domain chỉ hoàn thành khi có UX, data model, backend, agent/task logic, QA, RBAC, audit và E2E tests. Không đánh dấu hoàn thành chỉ vì đã có trang UI hoặc prompt.

## 4. Các quy trình nghiệp vụ END-TO-END bắt buộc

Tất cả workflow có `tenant_id, brand_id, campaign_id, initiating_actor_id, trigger_id, task_id/run_id, correlation_id, request_id, idempotency_key, permission_snapshot, cost_reservation, trace_id` phù hợp, cùng bản ghi sự kiện bền vững.

| Code | Trigger | Luồng thực hiện/đầu ra | Approval / lỗi cần xử lý |
|---|---|---|---|
| WF-01 Lead-to-Client | lead/form/API | qualify -> discovery -> proposal/SOW -> commercial signoff -> onboarding | hợp đồng giá/điều khoản do người duyệt, chống trùng lead |
| WF-02 Brand Onboarding | khách đăng ký/khởi tạo brand | Brand questionnaire -> collect files -> extract -> validate -> version Brand Kit -> approve | thiếu tài liệu = chờ bổ sung, không tạo sự thật giả |
| WF-03 Audit & Research | brief nghiên cứu | lấy nguồn -> đo độ mới -> đối chiếu -> competitor/customer analysis -> QA -> report | nguồn không truy cập = ghi 'không có dữ liệu' |
| WF-04 Annual/Quarter Strategy | business objective | audit -> research -> positioning -> channels -> budget scenario -> KPI -> approval | gắn giả định, không bảo đảm tăng trưởng |
| WF-05 Product Launch/GTM | launch brief | customer/problem -> proposition -> campaign -> content -> asset -> tracking -> review | thông số sản phẩm từ tài liệu chính thức |
| WF-06 Campaign Factory | approved strategy | breakdown -> tasks -> content/creative/media -> timeline -> review -> publish plan | quản lý phụ thuộc, scope, deadline |
| WF-07 Content Calendar | content brief | pillar -> content variants -> per-channel edit -> brand QA -> preview -> approve | sửa có version, không xuất bản thiếu duyệt |
| WF-08 Creative & Video | approved creative brief | concept -> generation/edit -> copyright check -> storyboard/video -> approval | provider quota, tài sản đầu vào phải có quyền |
| WF-09 Social Publishing | approved assets + schedule | kiểm quyền channel -> preview -> publish -> verify remote ID -> archive receipt | retry có idempotency; token hết hạn chờ reconnect |
| WF-10 Community & Reputation | inbound authorized comments | classify -> draft reply -> sensitivity check -> human approve/high-confidence policy -> send | khiếu nại/khủng hoảng escalate |
| WF-11 SEO/GEO | website access | crawl authorized -> technical/content audit -> recommendations -> change proposal -> approved commit/CMS update | không tự đăng hàng loạt nội dung kém giá trị |
| WF-12 Ads Planning/Execution | campaign approval | media plan -> campaign draft -> spend ceiling -> explicit approval -> API action -> verify -> monitor | chưa được API quyền = draft/export, không giả lập thành công |
| WF-13 Landing/CRO | conversion objective | landing spec -> layout/copy -> form -> tracking -> A/B test -> analyze -> optimize | production publish phải duyệt, rollback |
| WF-14 Lifecycle/CRM | consented segment/event | segment -> journey -> content -> legal consent -> send -> deliverability/opt-out -> report | không gửi spam, không contact chưa có quyền |
| WF-15 PR/Influencer/Events | communications brief | research -> shortlist -> outreach draft -> brief/contract checklist -> logistics -> measurement | KOL/giá/thỏa thuận cần người phê duyệt |
| WF-16 Ecommerce/Trade | catalog update/promo | product truth -> channel content -> promotion plan -> availability/price check -> approved publish | giá/tồn từ source of truth |
| WF-17 Analytics Ingestion | schedule/API sync/CSV | fetch -> validation -> raw snapshot -> normalize -> reconciliation -> store | lỗi nguồn phát cảnh báo, không bịa dữ liệu |
| WF-18 Marketing Reporting | period close | compute KPI deterministic -> narrative evidence -> exceptions -> review -> PDF/HTML/export -> client portal | trace raw source, thiếu nguồn = null/not available |
| WF-19 Optimization Loop | performance anomaly | threshold -> root cause hypotheses -> recommendation -> simulation -> approval -> action -> measurement | không tự chi vượt ngân sách |
| WF-20 Lead-to-Sales | qualified opt-in lead | score -> dedup -> route CRM -> activity -> status feedback -> attribution | privacy/consent, dữ liệu chuyển giao phải đúng quyền |
| WF-21 Client Feedback & Change | edit request | record -> SOW/scope check -> impact and price/time -> change approval -> tasks -> deliver | không làm tăng phạm vi không kiểm soát |
| WF-22 Incident & Recovery | error/provider outage/security | detect -> block dangerous action -> alert -> retry/rollback -> audit -> postmortem | fail closed, không báo success giả |
| WF-23 Weekly/Monthly Operations | schedule | client update -> deadlines -> spent vs plan -> QA failures -> billing status -> exec report | số liệu kiểm chứng, lịch đúng timezone |
| WF-24 Subscription Lifecycle | billing event | subscription -> entitlement -> proration -> invoice/refund -> renewal/dunning -> graceful limit | billing idempotency, ngừng agent theo policy |

### 4.1. State machine chuẩn

`draft -> submitted -> clarified -> planned -> approved_to_execute -> queued -> running -> in_review -> approved_to_publish -> publishing -> published -> verified -> delivered -> accepted -> closed`.

Các trạng thái khác: `blocked_missing_input, blocked_permission, blocked_budget, awaiting_client, awaiting_integration_review, retry_scheduled, failed_visible, cancelled, rollback_required, expired`. Mọi chuyển trạng thái phải có actor, authorization, timestamp, reason và audit event. `approved_to_execute` khác `approved_to_publish` và khác quyền `spend`.

### 4.2. Một kịch bản end-to-end chấp nhận thương mại

Khách thuê agency đăng ký -> tạo tenant -> tạo khách hàng C và brand B -> nhập sản phẩm, Brand Kit, mục tiêu -> chọn dịch vụ tích hợp Research + Strategy + 30-day Campaign -> AI Director lên kế hoạch và dự toán AI credits -> khách duyệt kế hoạch -> các agent chuyên môn tạo competitor matrix, ICP, strategy, content plan, content drafts, visuals, campaign draft -> QA bắt lỗi và yêu cầu sửa -> khách xem diff/preview và approve -> hệ thống lên lịch đăng được phép hoặc xuất bản nháp không thể tự đăng nếu API thiếu quyền -> connector trả remote publishing ID hoặc trạng thái lỗi thật -> GA4/Ads/SC dữ liệu đồng bộ -> báo cáo số liệu có lineage -> AI Analytics phân tích giả thuyết và đề xuất tối ưu -> khách duyệt thay đổi -> issue đóng với artifact, chi phí, SLA, comment/trace. Không có bước ngầm bỏ qua.

## 5. Phân quyền, approval, hành động nhạy cảm

| Action class | Quyền mặc định | Điều kiện thực thi |
|---|---|---|
| A0 Read approved tenant data | Agent đọc trong phạm vi | user/agent permission, brand scope, purpose, trace |
| A1 Draft/report/internal edit | agent thực hiện trong workspace | schema + QA + provenance + quota |
| A2 Send to client/editor | yêu cầu review theo workflow | approved recipient, policy, rate limit |
| A3 Publish public / send outbound | duyệt per action hoặc chính sách ủy quyền rõ | content version locked, target account, scope, idempotency |
| A4 Spend/change ad budget | chủ ngân sách và ads role | per-action approval, cap, provider access, receipt, verification |
| A5 Contract/payment/deletion | người có thẩm quyền; AI chỉ soạn/kiểm tra | manual execution / controlled finance gateway, dual control với thao tác rủi ro cao |
| A6 Agent self-modify skills/policies | deny by default | review signed changes, evals and rollback |

Agent không được dùng credential của Super Admin. Secrets ở server/vault, thời hạn ngắn, scope nhỏ nhất. Web pages và uploads là untrusted data; model output không được trực tiếp điều khiển shell/SQL/API write nếu không qua policy gateway.

## 6. Hệ thống tích hợp thực tế — Connector Capability Contract

<a id="p05-connector-reference"></a>

**Từng kết nối bắt buộc khai báo**: `provider, supported_features, app_review_state, oauth_scopes, service_account_policy, per_account_owner, region, read/write modes, rate_limits, quota, expiry, refresh_flow, webhook_signature, idempotency_strategy, error_map, external_object_mapping, revocation, terms_version, health_test`.

| Nhóm tích hợp | Ví dụ / mức hỗ trợ thiết kế |
|---|---|
| Analytics | GA4 Data API, Search Console, Google Tag Manager (theo quyền), CSV/XLSX import có schema validation |
| Ads | Google Ads API, Meta Marketing API, TikTok Ads API, LinkedIn Marketing APIs — từng tính năng dựa trên tier/approval |
| Social & publishing | Facebook Pages/Instagram Business, LinkedIn Pages, TikTok Content Posting, YouTube Data API, WordPress/CMS — chỉ qua API hợp lệ |
| CRM/Lifecycle | HubSpot, Salesforce, Odoo, email marketing providers, webhook/CSV — consent và suppression lists bắt buộc |
| Website/ecommerce | Shopify, WooCommerce, WordPress, CMS headless, sitemap/robots, product feeds authorized |
| Content/DAM | Google Drive, OneDrive, S3-compatible object store, Figma/Canva approved exports nếu khả dụng |
| Communication/PM | Gmail/Outlook, Slack, Teams, Google Calendar, Jira/Asana/ClickUp/Linear via API where approved |
| AI/media | LLM providers, image/video generation providers, transcription, text-to-speech via separate provider adapters |
| Finance/payments | PSP theo địa bàn, accounting adapter, export invoice; ad spend không được tính lẫn AI cost hoặc doanh thu SaaS |

**Trạng thái connector cấp tài khoản:** `not_configured, awaiting_approval, connected_read_only, connected_read_write, degraded, token_expired, quota_limited, revoked, unavailable`. UI thể hiện chính xác capabilities; API không có quyền = không có hành động giả. Luồng chuẩn: connect -> verify -> scopes -> sandbox test -> audit -> controlled enable -> reconcile -> rotate/revoke.

**Điểm nghiên cứu thời điểm 2026:** Google Ads API access gắn Google Cloud project từ 09/2026; Meta Marketing API Access Tier yêu cầu theo cơ chế hiện hành; TikTok Direct Post yêu cầu `video.publish` được phê duyệt và người dùng cấp quyền, app chưa audit bị giới hạn quyền hiển thị. Cần đọc tài liệu mới nhất trước go-live.

## 7. Data model chuẩn tối thiểu

**SaaS:** `tenants, tenant_memberships, users, identities, subscriptions, plans, plan_entitlements, payments, invoices, refunds, usage_events, costs, provider_balances, quota_reservations, tenant_settings`.

**Company/Client:** `ai_companies, departments, agent_roles, agent_versions, agent_assignments, client_accounts, client_contacts, brands, brand_kits, products, approved_claims, policy_packs, client_consents`.

**Marketing:** `goals, strategies, campaigns, channels, content_calendars, content_items, asset_versions, media_plans, ads_accounts, ad_campaign_mappings, seo_audits, keyword_clusters, website_experiments, crm_leads, lifecycle_sequences, marketing_events, metrics_snapshots, attribution_models, reports`.

**Workflow:** `projects, tasks, task_dependencies, task_runs, run_events, tool_actions, tool_receipts, approvals, approval_policies, comments, deliverables, artifacts, artifact_versions, schedules, events_outbox, dead_letter_queue, incident_records`.

**Knowledge/Security:** `documents, document_versions, knowledge_chunks, embeddings, tool_connections, connector_scopes, secret_references, audit_events, privacy_requests, retention_policies, security_findings, consent_records, data_exports`.

**Quy tắc:** PK UUID/ULID; mọi record tenant-owned có `tenant_id`; mọi brand-owned record có `brand_id`; foreign key composite hoặc service-level integrity không cho cross-tenant join; RLS DB hoặc cơ chế tương đương; object storage prefix/bucket policies; vector namespace per brand; user and machine principals separated; time UTC stored, timezone view at tenant/brand; money stored integer minor units + currency + exchange rate basis; mọi metric có time window, source, attribution policy.

## 8. UX / Navigation hoàn chỉnh

### 8.1. Public & onboarding

`/`, `/features`, `/solutions/agency`, `/solutions/inhouse`, `/pricing`, `/security`, `/docs`, `/contact`, `/login`, `/signup`, `/onboarding`, `/invite`.

### 8.2. Tenant Workspace

`/app/home` Dashboard; `/app/ai-director` Company chat; `/app/company` company builder; `/app/departments`; `/app/agents`; `/app/agent-skills`; `/app/clients`; `/app/brands`; `/app/brand-kit`; `/app/services`; `/app/proposals`; `/app/contracts`; `/app/projects`; `/app/tasks`; `/app/calendar`; `/app/campaigns`; `/app/research`; `/app/strategy`; `/app/content-studio`; `/app/creative-studio`; `/app/assets`; `/app/social`; `/app/ads`; `/app/seo`; `/app/website-cro`; `/app/crm`; `/app/lifecycle`; `/app/pr-influencer`; `/app/analytics`; `/app/reports`; `/app/approvals`; `/app/knowledge`; `/app/connections`; `/app/budgets`; `/app/usage`; `/app/billing`; `/app/team`; `/app/audit`; `/app/settings`.

### 8.3. Client Portal & Operator

`/client/{account}/dashboard, /client/{account}/campaigns, /client/{account}/deliverables, /client/{account}/approvals, /client/{account}/reports, /client/{account}/requests`.

`/operator/tenants, /operator/plans, /operator/billing, /operator/providers, /operator/connectors, /operator/security, /operator/incidents, /operator/support, /operator/rollouts, /operator/audit`.

UI desktop + responsive mobile, i18n vi/en baseline, WCAG 2.2 AA target. Danh sách agent và office view là công cụ quản lý, KHÔNG thay thế dashboards và deliverables.

## 9. Thiết kế API & events — khung hợp đồng (không phải API đã hiện thực)

`POST /v1/tenants`, `POST /v1/tenants/{id}/members`, `POST /v1/companies`, `POST /v1/agents`, `PATCH /v1/agents/{id}`,
`POST /v1/clients`, `POST /v1/brands`, `PUT /v1/brands/{id}/kit`, `POST /v1/campaigns`, `POST /v1/projects`,
`POST /v1/tasks`, `POST /v1/tasks/{id}/plan`, `POST /v1/runs`, `POST /v1/runs/{id}/cancel`, `GET /v1/runs/{id}/events`,
`POST /v1/artifacts`, `POST /v1/approvals/{id}/decision`, `POST /v1/connections/{provider}/authorize`,
`GET /v1/connections/{id}/capabilities`, `POST /v1/publishing/requests`, `POST /v1/ads/action-requests`,
`GET /v1/analytics/metrics`, `POST /v1/reports/generate`, `GET /v1/usage`, `GET /v1/billing/invoices`,
`POST /v1/webhooks/{provider}` (signature verified), `POST /v1/privacy/export`, `POST /v1/privacy/delete`.

OpenAPI v3.1, typed schemas, idempotency key on mutating requests, correlation/trace ID, error codes with actionable recovery path, cursor pagination, conditional request/optimistic locking for revisions, server-side auth on every object.

**Event schema:** `event_id, schema_version, event_type, tenant_id, brand_id, aggregate_id, occurred_at, actor_id, origin, payload_redacted, correlation_id, causation_id, idempotency_key`; durable outbox -> queue; consumer dedup; no ambiguous "exactly once" promise for external side effects; verify remote state and reconcile.

## 10. Kiến trúc công nghệ đề xuất, cần ADR xác nhận

### Bảy lớp nghiệp vụ và điểm kiểm trên cây main #63

| Lớp | Điểm kiểm hiện hữu | Giới hạn của bằng chứng |
|---|---|---|
| SaaS Core | [FastAPI và UI tĩnh](../app/main.py), [SQLAlchemy](../app/database.py), [migrations](../migrations/) | SQLite cho dev, PostgreSQL cho kiểm quyền và khôi phục. |
| Business Knowledge | [Kho tri thức](../app/knowledge_store.py), [projection theo phạm vi](../app/c3_projection.py) | Đọc revision được phép cho đúng workspace/brand. |
| AI Workforce | [Registry adapters](../app/registry_adapters.py), [worker](../app/pool_worker.py) | Xem invocation và receipt trước khi ghi vai trò đã chạy. |
| Marketing Operations | [Studio](../app/c3_studio.py), [bàn giao Research–Strategy](../app/research_strategy.py) | Xem workflow và đầu ra cụ thể trên SHA đã thử. |
| Execution Gateway | [Gateway Workforce](../app/workforce_gateway.py), [thực thi sandbox](evaluation/sandbox-operations/README.md) | Adapter sandbox không cấp quyền ghi nền tảng thật. |
| Business Outcomes | [Visit, submission và CRM](../app/campaign_operations_crm.py), [pilot](evaluation/round62/PILOT-DECISION.md) | Đối soát fixture chưa xác lập doanh thu thực tế. |
| Continuous Learning | [Ma trận áp dụng kiến thức](research/APPLICABILITY_MATRIX.md), [nghiên cứu ghép cặp](evaluation/round63/PAIRED-STUDY.md) | Kết quả vẫn cần phản biện và quyết định áp dụng. |

Stack đọc được từ checkout gồm Python/FastAPI, SQLAlchemy, PostgreSQL, SQLite dev, JavaScript tĩnh và điều phối workflow trong repo. Những lựa chọn công nghệ bên dưới là đề xuất theo đặc tả. Mọi quyết định thay stack cần ADR riêng. [Bản đồ ADR và mã](KNOWLEDGE_MAP.md)

**UI:** React/Next.js + TypeScript, accessible design system, i18n, RBAC-aware UI nhưng quyền thực thi do backend quyết định.

**Core API:** TypeScript/NestJS hoặc Fastify (chọn theo ADR sau PoC), OpenAPI, OAuth2/OIDC, multi-tenant context. Python separate workers cho data science, generation, document processing và agent orchestration.

**Workflow orchestration:** durable workflow engine như Temporal self-host (hoặc tương đương được thử nghiệm), hàng đợi worker, retry/idempotency, human approval wait, deadline, cancellation, DLQ, scheduler.

**Agent runtime:** OpenAI Agents SDK hoặc CrewAI/LangGraph theo kiểm thử; một framework chính, không trộn nhiều framework cốt lõi nếu không có lý do. Agent role + workflow spec + tool policies là dữ liệu phiên bản hóa, không hardcode toàn bộ trong UI.

**Model routing:** Provider abstractions, per-capability model policies, structured outputs, redaction, cost reserve/settle, fallback, model evals and rollback.

**Data:** PostgreSQL + RLS, Redis cache/locks, S3-compatible blob storage + versioning, pgvector (or separately isolated vector DB), analytics warehouse optional scale-driven. OLTP không dùng làm OLAP lớn.

**Integration:** official OAuth API adapters/MCP gateway with resource-scoped authorization, token vault (KMS), webhook signatures, connector capability manifest, quotas, rate-limits, reconciliation.

**Observability:** OpenTelemetry, metrics/logs/traces, user-facing task timeline, audit + cost ledger; redact PII/secrets before telemetry.

**Deployment:** containerized staging/preprod/prod separation, IaC, CI/CD with signed images/SBOM, migrations, blue/green or rolling deploy, backup/restore tested, WAF, SSO, secret rotation, IR runbooks.

**Paperclip decision:** optional inspiration/component only. Its README advertises multi-company, but older `doc/SPEC.md` describes original single-tenant self-host target; historical critical advisories demonstrate need for independent review. Do not assume Paperclip equals a verified SaaS control plane; pilot with pinned SHA and security assessment before selecting to fork. A marketing-first custom control plane may reduce long-term coupling despite greater initial work.

## 11. Kế toán chi phí và mô hình thương mại — 3 ledger riêng

1. **SaaS revenue ledger:** customer subscription, invoice, payment, refund, tax, proration, credit, plan change.
2. **AI delivery cost ledger:** model token, image/video generation, browser/compute, connector fees, storage, labor/human review where included.
3. **Client marketing budget ledger:** customer's ad spend commitments/actuals, budgets, approval and reconciliation, agency service fees. **Không cộng ad spend thành doanh thu SaaS hoặc trừ nó như AI cost.**

Plan/entitlement: tenant, seats, brands, active clients, active agents, task concurrency, model quota/credits, image/video generation caps, retention, storage, connectors, API access, SLA/support, addons, BYOK option. Mọi plan phải có guardrails chống chi phí vượt trần; không bán 'unlimited' không có bảo vệ.

Commercial legal package: Terms, Subscription Agreement, SOW template (nếu agency mode), SLA, Privacy Policy, DPA, subprocessors, IP/asset rights, refund/cancellation, AUP, cookie/consent, incident disclosures, data export/deletion, support policy. Kiểm tra với tư vấn pháp lý tại thị trường bán.

## 12. Security & compliance

- Tenant and brand isolation at API, DB, vector, files, cache, queues, secrets, traces, costs and backups. Positive & negative tests; deny by default.
- Per-action policy gateway, sandbox egress allowlist, network and filesystem containment; no arbitrary shell from user-provided prompts or third-party pages.
- Prompt injection red teaming, skills supply-chain validation/signing, dependency/SBOM scanning, key rotation, managed secret vault.
- Sensitive actions human approval, least privilege, signed audit receipts, replay safe.
- External data import consent and purpose limitation; PII minimization, retention, deletion/export; vendor DPA and subprocessors.
- Marketing regulated claims, ad disclosures, customer opt-out, image/video rights, copyright and brand permissions; configure local policy packs.
- Follow OWASP Top 10 for Agentic Applications 2026; establish AI governance under NIST AI RMF; applicable Vietnam Personal Data Protection Law 91/2025/QH15 and Advertising Law 75/2025/QH15 if selling in Vietnam; review GDPR/EU AI obligations before EU commercialization.

## 13. Nghiệm thu General Availability (100% full-scope, không chia MVP)

**Functional traceability:** tất cả module SAA/AGY/MKT/AIO và WF-01..WF-24 có PRD ID, UI map, API contract, integration acceptance, testcase, owner, proof, release status `not_started/in_progress/in_review/verified`; mọi hạng mục trong phạm vi V1.0 phải đạt `verified` trước GA hoặc được xử lý bằng quyết định thay đổi phạm vi công khai (không lặng lẽ ẩn lỗi).

**Security zero-tolerance:** 0 sự cố cross-tenant trong thử nghiệm; 0 unauthorized publish/spend/email/delete; broken authorization and prompt-injection tests pass; secrets do not enter logs; backup restore tested.

**Marketing accuracy:** 100% numeric figures in acceptance dataset can be recomputed from raw source; no invented totals; citation required for externally sourced factual claims; unsupported claims flagged; publish only approved artifact version.

**Workflow reliability:** every task ends `verified/delivered` or a visible recoverable failure; repeated webhooks and retries do not duplicate posts, payments or budget mutations; kill/restart recovery; queue backpressure and rate-limits controlled.

**Commercial:** full signup -> plan -> payment -> entitlement -> usage -> invoice -> renew/suspend/refund -> restore/export; ledger reconciliation; positive unit economics against measured load and support effort.

**Usability:** novice customer can onboard organization/brand, connect/test a supported tool, launch service, review deliverable, approve, export/publish, inspect billing; responsive desktop/mobile; accessibility targets.

**Performance/SLO targets pending load test:** availability >=99.9% monthly objective; common interactive reads p95 < 2 seconds at specified concurrent load; RPO <=24h and RTO <=4h baseline objective (enterprise policies by tier); >99% successful scheduled jobs where upstream services are available; no unbounded queue growth. Targets are design goals, not already achieved SLAs.

**Full operation:** monitoring, alerting, audit dashboard, on-call/runbooks, incident/postmortem, live status, feature rollback, documentation, support and backup. Repeated dry-run with representative tenants and brands, provider outages, expired tokens, bill disputes and adversarial inputs.

**Acceptance sample A:** tenant A with 2 brands and tenant B: run same campaign concurrently; neither can see other's assets, audit, quota, cache, credentials or vector results.

**Acceptance sample B:** Meta OAuth revoked after content approval: publishing blocked with actionable reconnect, no false success, retry after new authorization only, one external post ID.

**Acceptance sample C:** Google Ads request over budget: server denies despite agent prompt suggesting override; approval captures prior/post spend cap, no external mutation.

**Acceptance sample D:** imported CSV inconsistent across timezone/currency: create data-quality incident, mark metrics unavailable until reconciliation, never invent sales.

**Acceptance sample E:** customer asks for unapproved health/financial advertising claims: QA flags as high risk and routes to legal/manual review.

**Acceptance sample F:** crash after provider write but before local receipt: remote reconciliation finds action ID and prevents duplicate publication/payment.

**Acceptance sample G:** brand kit updated mid-campaign: existing approved assets retain version; changed campaign requires review of affected assets before publishing.

**Acceptance sample H:** subscription suspended due to failed payment: graceful stop of paid runs; no loss of customer data; recovery on paid reinstatement according to contractual retention.

## 14. Engineering execution workstreams (KHÔNG phải các bản MVP)

### Đối chiếu roadmap P00–P12

Các mã sau đến từ bản continuity của dự án. Thứ tự là đề xuất lập kế hoạch. Mỗi dòng chỉ ra nơi lấy bằng chứng và việc cần quyết định khi muốn nâng mức.

| Pha | Phạm vi | Mốc đối chiếu và phần cần chứng minh |
|---|---|---|
| P00 | Baseline và nghiệm thu | [HANDOFF](../HANDOFF.md) và biên nhận theo SHA; tái kiểm khi đổi cây. |
| P01 | 37 hợp đồng vai trò | [Catalog](../catalog/agent_roles.json); mỗi vai trò cần receipt và nghiệm thu riêng. |
| P02 | Chất lượng Research, Strategy, Content, SEO | [Nghiên cứu WF-03](evaluation/round63/README.md) và [capability register](evaluation/DEPARTMENT-CAPABILITY-REGISTER.md); kiểm chất lượng theo nhiệm vụ. |
| P03 | Thu thập, chứng minh và dùng tri thức | [Projection](../app/c3_projection.py) và [sổ nguồn](research/SOURCE_REGISTRY.md); kiểm quyền và revision của nguồn. |
| P04 | Content, Image, Design, Video | [Content Factory](evaluation/content-factory/README.md), [Workforce Video](evaluation/workforce-video/README.md); còn cần nghiệm thu đầu ra bởi practitioner. |
| P05 | Đọc dữ liệu Marketing thật theo quyền | [Hợp đồng connector ở mục 6](#p05-connector-reference); cần chủ dữ liệu, phạm vi, môi trường và quyền cụ thể. |
| P06 | Đối soát CRM, RFQ, Sales | [Hồ sơ RFQ](evaluation/round62/README.md); doanh thu/nghiệm thu thực tế cần dữ liệu được phép. |
| P07 | Connector Execution Gateway | [Thực thi sandbox](evaluation/sandbox-operations/README.md); tác động thật cần duyệt theo adapter. |
| P08 | Tự vận hành ngày, tuần, tháng | [Worker pool](POOL-RUNBOOK.md); lịch vận hành end-to-end đủ chu kỳ còn cần bằng chứng. |
| P09 | Workflow/module còn lại | [Ma trận coverage](IMPLEMENTATION_STATUS.md); đối chiếu từng ID và dependency. |
| P10 | SaaS, billing, thương mại | Ba sổ tài chính tại mục 11; kinh tế đơn vị và quyền thu phí còn cần nghiệm thu. |
| P11 | Security, hạ tầng, giám sát, backup/recovery | [Security gates](SECURITY_AND_GA_BLOCKERS.md); dùng biên nhận restore và diễn tập môi trường đích. |
| P12 | Nghiệm thu và phát hành toàn V1 | Mục 13 và [tình trạng giấy phép](../LICENSE-STATUS.md); quyết định release hiện ở [HANDOFF](../HANDOFF.md). |

| Workstream | Công việc | Mối phụ thuộc | Sản phẩm cuối |
|---|---|---|---|
| WS-A | Domain & UX architecture | PRD, RACI, policies | schema, design system, user journeys |
| WS-B | SaaS commerce/tenancy | WS-A | SAA-01..09, entitlements |
| WS-C | AI runtime/control | WS-A/B interface contracts | AIO-01..12, secure agent execution |
| WS-D | Agency business | WS-A/B | AGY-01..08, client portal |
| WS-E | Marketing suite | WS-A/C/D | MKT-01..20, full workflows |
| WS-F | Channel integrations | consent/security/connector contracts | official API adapters and capability tests |
| WS-G | Data quality & reporting | source connector, metrics schema | deterministic analytics, reports, lineage |
| WS-H | Security & ops | all workstreams | penetration tests, DR, observability, legal |
| WS-I | Integrated QA & release | all workstreams | traceability 100%, GA release gate |

Các nhánh công việc có thể triển khai song song; **một sản phẩm V1.0 duy nhất** mới được gắn nhãn sản phẩm thương mại hoàn chỉnh. Không dùng từ 'hoàn thành' cho màn hình chỉ có dữ liệu giả.

## 15. Project controls & deliverables for development

- Architecture Decision Records (ADR-001 foundation; ADR-002 orchestration; ADR-003 tenant isolation; ADR-004 billing; ADR-005 model gateway; ADR-006 connectors; ADR-007 runtime security).
- ERD & DB migrations; OpenAPI schemas; RBAC matrix; event/state transition table; workflow source-of-truth; UI sitemap and design system.
- Agent catalog + versioned instructions + tools policy; marketing service templates with input/output schema; QA golden datasets; data policy packs.
- Connector certification matrix, capability checklist, OAuth app review tracker, provider status, rollback procedures.
- Automated unit/integration/E2E/permission/performance/security/eval suites; observability SLO dashboards and DR restore evidence.
- Commercial: legal templates, onboarding, plan configuration, payment/invoice integrations, support handbook, operator manual, customer tutorials.
- Product telemetry: activated brands, accepted work units, first-pass approvals, failure/exception rate, median time-to-approved, per-customer gross margin, churn/retention.

## 16. Research and source register (official/current as of 23/11/2026)

- WFA State of AI in Marketing 2026: https://wfanet.org/knowledge/item/2026/09/30/96-of-major-brands-now-use-ai-in-marketing-wfa-research-finds
- WFA From AI Tools to AI Agents: https://wfanet.org/knowledge/item/2026/11/17/from-ai-tools-to-ai-agents-what-marketers-need-to-know
- WFA Media Operating Models: https://wfanet.org/knowledge/item/2026/11/17/no-best-media-operating-model-as-global-advertisers-split-across-four-distinct-approaches
- Google Ads API access (developer token sunset 2026): https://developers.google.com/google-ads/api/docs/api-policy/access-levels
- Meta Marketing API tier 2026: https://developers.meta.com/blog/updates-to-ads-management-standard-access-feature/
- TikTok official Content Posting API: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- LinkedIn official Marketing API access: https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access
- Google Search Console API limits: https://developers.google.com/webmaster-tools/limits
- GA4 Data API quotas: https://developers.google.com/analytics/devguides/reporting/data/v1/quotas
- GA4 Measurement Protocol: https://developers.google.com/analytics/devguides/collection/protocol/ga4
- Paperclip repo: https://github.com/PaperclipAI/paperclip
- Paperclip security advisories: https://github.com/paperclipai/paperclip/security/advisories
- Paperclip original SPEC (historical single-tenant target): https://github.com/paperclipai/paperclip/blob/master/doc/SPEC.md
- Agents SDK: https://github.com/openai/openai-agents-python
- CrewAI: https://github.com/crewAIInc/crewAI
- LangGraph: https://github.com/langchain-ai/langgraph
- OWASP Agentic Top 10: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Vietnam Personal Data Law 91/2025/QH15: https://vanban.chinhphu.vn/?classid=1&docid=214590&pageid=27160
- Vietnam Advertising Law amendment 75/2025/QH15: https://vanban.chinhphu.vn/?classid=1&docid=214561&pageid=27160
- Community evidence (not representative): https://www.reddit.com/r/marketingagency/comments/1rwx8iv/marketing_agencies_whats_the_most_annoying_part/ , https://www.reddit.com/r/agency/comments/1tvdf0o/my_2_cents_on_where_a_system_makes_sense/

## 17. Decision Log

Đọc mỗi mục theo nguồn, người có quyền, ngày, phạm vi và phiên bản. CONFIRMED = xác nhận được phát biểu hoặc quan sát; PROPOSED = có phương án, đang chờ quyết định; ACCEPTED = có người có thẩm quyền chấp thuận trong phạm vi ghi nhận; IMPLEMENTED = có hiện thực trên cây chỉ định; VERIFIED = có kiểm chứng gắn với cây và kết quả; SUPERSEDED = đã chỉ được quyết định hoặc phiên bản thay thế; UNKNOWN = thiếu căn cứ. Các nhãn mô tả loại bằng chứng, không tự chuyển tiếp. D-014 ghi hoạt động tại lúc biên soạn đặc tả ngày 23/11. Đối chiếu hiện trạng tại [HANDOFF](../HANDOFF.md) và thẩm quyền tại [AGENTS](../AGENTS.md).

- **D-009 (23/11/2026):** Supersede prior split between generic AI Company vs marketing package. One product: AI Marketing Company; shared Agency and In-house operating modes.
- **D-010 (23/11/2026):** Require one complete V1.0 GA release, not sequential marketing MVPs. Internal technical workstreams permissible; full feature coverage and QA required before claiming completion.
- **D-011 (23/11/2026):** Product includes entire Marketing professional suite + client operations + SaaS commerce + governed AI workforce + supported connectors with honest capability reporting.
- **D-012 (23/11/2026):** Prioritize external API policies, tenant isolation, side-effect authorizations and verifiable business output over agent-role theatre.
- **D-013 (23/11/2026):** Paperclip remains a candidate/reference, NOT a production-approved SaaS base until license/security/architecture/economics review.
- **D-014 (23/11/2026):** No repository creation, code changes, external account actions or production deployment has been performed in producing this specification.

**END — FULL PRODUCT SPEC V1.0.**
