# Sổ năng lực phòng Marketing

**Sau #58, trên nhánh WF-08.** Creative lead có thể giao lát cắt Video/Storyboard cho Workforce với một adapter cục bộ tất định. Giới hạn qua thử nghiệm gồm brief tiếng Việt, tư liệu minh họa tổng hợp, giá/điều kiện theo nguồn, QA theo revision. Làm phim từ footage thật, năng lực mô hình suy rộng, nghiệm thu bởi người dựng và thực thi media còn mở. [Hợp đồng, đầu ra trước/sau QA và receipt](workforce-video/README.md)

**Sau review #57.** Hai brief Khe Gọn và Luồng Rõ có đường Studio → QA → landing → tiếp nhận sandbox kiểm lại trên đúng dữ kiện. Bản dựng creative, lời thoại hai hook và phụ đề là đầu ra biên tập bổ sung. Phần đối chiếu nguồn và policy O-09 ở lab, chưa là một worker sản xuất. Năng lực chuyên môn được phân loại theo đầu ra tạo được, ai làm và ai có quyền chấp thuận. Chủ doanh nghiệp chưa chấp nhận đơn vị công việc nào. [Hai gói và nguồn gốc](campaign-production-review/README.md) · [Mapping vai trò](campaign-production-review/SKILLS.md) · [Routing chín nhóm việc](department-study/advisory/TASK-ROUTING.md)

Sau khi merge #56, WF-14 và WF-20 có bằng chứng sandbox về điều kiện hồ sơ và quyền tư vấn, WF-18 có đối soát theo giai đoạn. Handoff khi khách đổi ý, pilot theo vai trò và ba phương pháp làm rõ yêu cầu được kiểm tra trên nhánh tiếp theo. Chỉ nâng mức cho từng workflow khi có đầu ra và quyết định tương ứng của người dùng. [Biên nhận main](department-review/MAIN-56.json) · [Phép thử trên cohort mới và giới hạn](department-review/MARKET-HANDOFF.md)

Phạm vi tham chiếu là [19 năng lực trong Product Mission](../PRODUCT_MISSION.md), [24 workflow của V1](../PRODUCT_SPEC_V1.md) và [bằng chứng kỹ thuật trước vòng này](campaign-engine/CAPABILITIES.md). Mỗi dòng nêu phần công việc và mức cao nhất có bằng chứng cho phần đó. “Đặc tả” nghĩa là có mô tả workflow; phần đầu ra nghiệp vụ bên cạnh còn phải triển khai hoặc kiểm định. “Hợp đồng” là hành vi có cấu trúc dữ liệu hoặc quy tắc thực thi. “Kiểm thử” là có nghiệm thu kỹ thuật cho phạm vi ghi trong dòng. “Đầu ra” là đã tạo tài liệu hoặc tệp thực. “Sandbox” là đã thực hiện một giao dịch có thể truy nguyên trong môi trường tổng hợp.

Nghiệm thu chuyên môn của người hành nghề, quyền thực thi ra nền tảng bên ngoài và mức sẵn sàng thương mại là ba cột trạng thái áp dụng cho **từng dòng**: chưa có quyết định nghiệm thu, chưa được phép, **NO-GO**. Đối với chức năng nội bộ như lưu phiên bản hoặc kiểm tra quyền, thực thi bên ngoài không áp dụng. Kết quả của AIRC-500 có sổ riêng. Đối chiếu bản đã nghiệm thu và từng thay đổi đang review bằng commit, phiên bản và biên nhận.

| Năng lực Mission | Công việc đã có bằng chứng | Mức và phần còn thiếu |
|---|---|---|
| Lãnh đạo Marketing | Director chia việc theo workflow được kích hoạt | Kiểm thử DAG, thiếu quyết định danh mục đa chiến dịch được chủ doanh nghiệp chấp nhận |
| Điều phối chiến dịch | Ghép manifest, phân công, hạn chót, duyệt kế hoạch | Sandbox có queue receipt; còn phải đo chi phí/hạn giao thực |
| Vận hành agency | Cô lập khách, phân quyền, chia sẻ và kho chi phí | Kiểm thử RLS, restore và thu hồi; thiếu đối soát hóa đơn thực |
| Nghiên cứu thị trường | Bản quan sát từ tài liệu công khai có ngày và phạm vi | Đầu ra tham khảo quy trình; thiếu tập đối thủ đã xác minh của doanh nghiệp |
| Nghiên cứu khách hàng/ICP | Ghim người mua, giai đoạn mua, giả thuyết và câu hỏi | Đầu ra theo brief; thiếu phỏng vấn xác minh |
| Chiến lược Marketing | Chọn đối tượng, đề xuất kênh, phép thử và bước tiếp theo | Đầu ra WF-03; thiếu bằng chứng forecast hoặc hiệu quả |
| Quản trị thương hiệu | Ghim guideline, phạm vi, revision và điều cấm | Kiểm thử thay đổi nguồn; thiếu đánh giá giọng thương hiệu |
| Content Marketing | Bộ bài theo nền tảng, web, search, CTA và lịch có chủ sở hữu | Đầu ra theo kế hoạch; chờ biên tập viên chấp nhận |
| Thiết kế và video | Nhánh Creative chạy renderer tổng hợp, master và preview | Đầu ra PNG/WebM trong nhánh sản xuất; cần đối chiếu biên nhận render và quyền trên bản merge |
| Social Media Marketing | Copy LinkedIn/Facebook và duyệt bản kênh | Đầu ra, lệnh sandbox; chưa có receipt đăng thật hoặc quản trị cộng đồng |
| SEO/GEO | Tiêu đề, mô tả, câu hỏi và câu trả lời theo nguồn | Đầu ra; thiếu crawl site, chỉ số tìm kiếm và audit GEO |
| Website, landing và CRO | Trang sandbox từ bản có QA và gửi form RFQ/đặt lịch ở nhánh Landing | Sandbox; còn trải nghiệm người mua thật và thử nghiệm CRO |
| E-commerce Marketing | SKU, đơn vị bán, tax, MOQ và điều kiện | Kiểm thử; thiếu feed sàn, tồn kho, đơn hàng thật |
| Performance Marketing | Nhóm quảng cáo, biến thể, giới hạn định dạng và phân bổ trần | Đầu ra đề xuất; thiếu duyệt chính sách, URL công khai, receipt và đối soát provider |
| Marketing Automation | Lệnh theo nhóm, lịch, dispatcher, lịch sử và retry | Sandbox; thiếu adapter thực và vận hành có SLA |
| CRM, Lead Generation và Lifecycle | RFQ, lịch hẹn, đồng ý liên hệ và chuyển giao | Sandbox; còn tích hợp CRM doanh nghiệp, consent đồng bộ và nurture |
| Marketing Analytics | Đối soát biên nhận, chi phí, xử lý thiếu nguồn | Sandbox; hợp đồng KPI mới phải đối chiếu revision và snapshot của nhánh Q01 |
| Marketing QA | Kiểm fact, câu đã sửa, hash/revision, reviewer và snapshot | Kiểm thử; trường hợp ngôn ngữ mơ hồ và tính thuyết phục cần người có chuyên môn |
| Business Knowledge và Enterprise Memory | Nguồn, revision, manifest và ghi lịch sử bất biến | Kiểm thử; chưa đo tác động của tái sử dụng tri thức |

| Workflow | Mức có bằng chứng và phạm vi | Gate nghiệp vụ tiếp theo |
|---|---|---|
| WF-01 Lead-to-Client | Hợp đồng tiếp nhận lead trong sandbox | Proposal/SOW và chốt hợp đồng |
| WF-02 Brand Onboarding | Kiểm thử hồ sơ, guideline, claim và revocation | Chủ thương hiệu xác nhận bàn giao |
| WF-03 Audit & Research | Đầu ra chiến lược có manifest | Chuyên viên kiểm độ đại diện và độ mới |
| WF-04 Annual/Quarter Strategy | Đặc tả; chiến lược từng campaign đã có nháp | Kế hoạch quý, forecast, phụ thuộc danh mục |
| WF-05 Product Launch/GTM | Đặc tả | Phê duyệt battlecard và kế hoạch launch hoàn chỉnh |
| WF-06 Campaign Factory | Sandbox kế hoạch, điều phối, biên nhận và bàn giao | Chi phí và thời gian trên campaign được nhận |
| WF-07 Content Calendar | Đầu ra lịch theo mốc phê duyệt, nhóm và việc | Đối soát các mốc với công suất thật |
| WF-08 Creative & Video | Studio giữ renderer và QA; nhánh sau #58 bổ sung nhiệm vụ storyboard chạy trên worker, đầu ra có timeline, VTT và nguồn. [Phạm vi và bản chạy](workforce-video/README.md) | Công việc tất định cho tiền kỳ nội bộ. Còn thiếu footage thật có quyền và nghiệm thu của người dựng. |
| WF-09 Social Publishing | Đầu ra copy và mô phỏng hành động có receipt | Chờ quyền adapter và remote ID |
| WF-10 Community & Reputation | Đặc tả | Moderation, nhạy cảm và escalation |
| WF-11 SEO/GEO | Đầu ra metadata và nội dung search | Crawl có quyền và đo hiệu quả |
| WF-12 Ads Planning/Execution | Đầu ra kế hoạch, phân bổ, lệnh sandbox | QA Media và adapter chi tiêu có quyền |
| WF-13 Landing/CRO | Sandbox landing/form trên nhánh sản xuất | Phê duyệt triển khai, thử nghiệm chuyển đổi thật |
| WF-14 Lifecycle/CRM | Sandbox bàn giao theo consent | Chuỗi chăm sóc, opt-out và deliverability |
| WF-15 PR/Influencer/Events | Đặc tả | Shortlist, quyền liên hệ, hợp đồng và đo |
| WF-16 Ecommerce/Trade | Hợp đồng sản phẩm/điều kiện theo kênh | Feed, đối soát tồn và merchandising |
| WF-17 Analytics Ingestion | Sandbox receipt có nguồn và cách ly | Ingest provider, dedup và xử lý trễ |
| WF-18 Marketing Reporting | Đầu ra báo cáo từ trạng thái và chi phí đã ghi nhận | Đối soát với chứng từ bên nhận |
| WF-19 Optimization Loop | Sandbox đề xuất từ báo cáo có duyệt | Chứng minh thay đổi đem lại lợi ích |
| WF-20 Lead-to-Sales | Sandbox RFQ/lịch hẹn và phản hồi | Bên Sales đánh giá hồ sơ đủ xử lý |
| WF-21 Client Feedback & Change | Sandbox quyết định khách và snapshot độc lập | Kiểm thay đổi phạm vi hợp đồng/giá |
| WF-22 Incident & Recovery | Kiểm thử rollback, archive, retry và thu hồi | Diễn tập vận hành SLA với người tiếp quản |
| WF-23 Weekly/Monthly Operations | Đầu ra từng campaign và lịch phòng ban | Báo cáo liên kỳ nhiều khách và đối soát billing |
| WF-24 Subscription Lifecycle | Đặc tả; sổ chi phí nội bộ có kiểm thử | Payment, entitlement, proration, refund và dunning |

### Tìm lại bằng chứng theo công việc

- Leadership, Agency và Campaign Management (WF-02, 04, 06, 19, 22, 23) đối chiếu mốc giao việc, giới hạn ủy quyền, bản kế hoạch và biên nhận ở [commission](campaign-engine/commission) và [khôi phục journal](sandbox-operations/CUTOVER.md).
- Nghiên cứu, ICP, Strategy, Brand, QA và Knowledge (WF-02, 03, 05, 21) đối chiếu [nghiên cứu công khai](../research/DEPARTMENT-PRODUCTION.md), [hồ sơ lần đầu và tiêu chí](department-study/RESULTS.md) và [ca lỗi theo câu](commercial-meaning/README.md).
- Content, Social, SEO và Performance (WF-07, 09, 11, 12) có [hai bộ nội dung cùng phân bổ](commercial-meaning/outputs) và [giao diện đang chạy](commercial-meaning/screens/channels). Creative, Website và CRO (WF-08, 13) có [tệp thực, quyền, fingerprint và thử form](real-production/QUALIFICATION.md).
- Automation, Service, CRM và Analytics (WF-01, 14, 17, 18, 20) đối chiếu [điều phối bốn nhóm](sandbox-operations/channel-dispatch.json), [bàn giao theo vai trò](campaign-role-desk) và [KPI/holdout](kpi-integrity/RESULTS.md).
- E-commerce (WF-16) chỉ có phần dữ kiện và điều kiện đã ghim. WF-10, 15 và 24 chờ các gate trong bảng. [Bảng gốc 24 workflow](../PRODUCT_SPEC_V1.md)

Người tiếp quản mở [pilot đã đóng gói](department-study/PILOT.md), khóa brief và thứ tự mẫu trước khi gửi đúng ba vai trò. Hai brief tổng hợp dùng chung rubric cho bản thủ công, deterministic và model-assisted. Ghi thời gian làm rõ, sản xuất, sửa, QA, quyết định của Sales, từ chối, chi phí đầy đủ và tham chiếu phiên bản mỗi vai đã chấm. Chưa nhận phiếu người tham gia.
