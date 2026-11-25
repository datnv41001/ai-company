# AMC — Product Mission & Commercial North Star

**Sứ mệnh của AI Marketing Company là vận hành một phòng Marketing bằng AI có thể đảm nhiệm tối đa những công việc số hóa được, từ mục tiêu kinh doanh đến kết quả đã đối soát.** Người có thẩm quyền của doanh nghiệp giữ trách nhiệm về ngân sách, pháp lý và rủi ro kinh doanh. Tài liệu này là chuẩn để chọn tính năng và nghiệm thu giá trị. Đặc tả V1 xác định phạm vi sản phẩm và các cổng GA xác định điều kiện phát hành. [Đặc tả V1](PRODUCT_SPEC_V1.md) · [Điều kiện GA](SECURITY_AND_GA_BLOCKERS.md)

## Khách hàng mua công việc Marketing được hoàn thành

Chỉ số trung tâm của AMC là **Business-accepted Marketing Work Units** trong kỳ. Đếm một lần cho mỗi đơn vị công việc được người có thẩm quyền chấp nhận hoặc hoàn tất theo tiêu chí đã được phê duyệt trước. Gắn kết quả với brief, phiên bản tài sản, căn cứ nghiệm thu và chi phí toàn hành trình. Khi so sánh, giữ riêng loại việc, độ khó và khối lượng. Một lần chạy model, một lần sửa hay một phiếu đồng thuận của AI tự nó chưa tạo ra một đơn vị công việc được chấp nhận.

| Khách hàng | Công việc họ giao cho AMC | Dấu hiệu giá trị cần đo |
| --- | --- | --- |
| Cá nhân, người bán online | Chọn sản phẩm ưu tiên, làm nội dung và hình ảnh bán hàng, lập lịch quảng bá | Số tài sản dùng được và số giờ người bán bỏ ra cho mỗi tài sản |
| Doanh nghiệp vừa và nhỏ | Nghiên cứu khách hàng, lập chiến dịch, nuôi dưỡng và bàn giao lead cho Sales | Thời gian từ brief tới bản duyệt, tỷ lệ lead được Sales tiếp nhận |
| Doanh nghiệp lớn | Điều phối nhiều thương hiệu, thị trường, phòng ban và cấp duyệt | Thời gian phê duyệt, khả năng truy vết nguồn và đối soát kết quả từng thương hiệu |
| Marketing Agency | Quản lý phạm vi dịch vụ, sản xuất, QA và báo cáo cho nhiều khách | Số khách phục vụ được với cùng nguồn lực và chất lượng, chi phí trên công việc đã nghiệm thu |

Solo và quy mô doanh nghiệp mô tả nhu cầu sử dụng. In-house và Agency tiếp tục là hai mô hình quản trị của V1. Các mục tiêu kinh tế gồm giảm thời gian và chi phí, tăng năng suất, giữ tri thức khi thay người và cải thiện lead, chuyển đổi, doanh thu khi có dữ liệu chứng minh.

## Một phòng Marketing phối hợp công việc như thế nào

AI CMO và AI Director chuyển mục tiêu kinh doanh thành ưu tiên, kế hoạch, người chịu trách nhiệm, ngân sách đề xuất và tiêu chí dừng. Các bộ phận cùng sử dụng **Business Knowledge & Enterprise Memory** theo quyền của tenant, khách hàng và thương hiệu. Bảng sau mô tả năng lực đích và đầu ra chuyển cho bộ phận kế tiếp. Trạng thái thực thi của từng workflow được xác định bằng biên nhận trên phiên bản đã kiểm thử.

| Nhóm nghiệp vụ | Đầu vào → công việc → đầu ra bàn giao |
| --- | --- |
| Marketing Leadership, Campaign Management, Agency Operations | Mục tiêu, hợp đồng, năng lực và ngân sách → ưu tiên cơ hội, phân việc → kế hoạch chiến dịch, lịch, chủ sở hữu và giới hạn chi phí |
| Market Intelligence, Customer Research & ICP | Dữ liệu thị trường và khách hàng được phép sử dụng → xác định phân khúc, nhu cầu, hành vi mua → hồ sơ khách hàng mục tiêu, bằng chứng, giả thuyết và câu hỏi còn mở |
| Marketing Strategy, Brand Management | Kết quả nghiên cứu, lợi thế sản phẩm và quy chuẩn thương hiệu → chọn định vị, kênh, thông điệp → brief sáng tạo và kế hoạch thử nghiệm |
| Content Marketing, Creative Design & Video Production, Social Media Marketing | Brief đã duyệt → lập trụ cột nội dung, lịch biên tập, soạn bài, banner, kịch bản và storyboard → bộ tài sản theo kênh, kèm phiên bản và quyền sử dụng. Việc sản xuất video phụ thuộc công cụ đã tích hợp và kiểm chứng |
| SEO & GEO, Website/Landing Page & CRO, E-commerce Marketing | Nhu cầu tìm kiếm, danh mục và điều kiện bán → thiết kế trang, nội dung khám phá sản phẩm và hành động mua → tài sản có thể kiểm tra cùng sự kiện chuyển đổi cần đo |
| Performance Marketing, Marketing Automation | Mục tiêu, phương án media, hạn mức và consent → thiết kế thử nghiệm, chuẩn bị tác vụ → đề nghị phân bổ ngân sách hoặc lệnh thực thi có phê duyệt và biên nhận |
| CRM, Lead Generation & Customer Lifecycle, Marketing Analytics | Lead, sự kiện, chi phí, đơn hàng → phân loại, bàn giao Sales, theo dõi vòng đời và đối soát → kết quả có nguồn, khoảng trống dữ liệu và đề nghị tối ưu |
| Marketing QA, Business Knowledge & Enterprise Memory | Tài sản, chứng cứ, quyết định, kết quả → kiểm tra tuyên bố và quyền, lưu lịch sử → bản giao được duyệt và bài học có người xác nhận để dùng ở chiến dịch sau |

### Một chu trình mẫu

Doanh nghiệp muốn tăng doanh số gạch ốp lát tại Hà Nội trong ba tháng, với ngân sách dự kiến 50 triệu đồng mỗi tháng. Đây là brief minh họa. Con số trong brief là ràng buộc để lập kế hoạch.

1. **Business Goal → Business Knowledge.** CMO hỏi doanh số nền, mục tiêu tăng, nhóm sản phẩm, tồn kho, địa bàn và biên lợi nhuận. Director ghi phần còn thiếu và ghim đúng phiên bản bảng giá, đơn vị bán, thuế, vận chuyển.
2. **Research → Strategy → Planning.** Phân biệt nhu cầu của nhà thầu và chủ nhà. Chọn phân khúc, lý do chọn kênh, giả thuyết cần thử và tiêu chí một yêu cầu báo giá đủ điều kiện. Giao brief, mốc duyệt và đề xuất chi phí cho từng bộ phận.
3. **Production → QA → Authorized Execution.** Tạo trang yêu cầu báo giá, bài viết, hình ảnh hoặc kịch bản theo năng lực sẵn có. Editor và QA đối chiếu giá, phạm vi áp dụng, quyền tài sản và đúng revision. Lệnh xuất bản hoặc chi tiền cần đúng người duyệt, tài khoản, hạn mức và biên nhận thực thi.
4. **CRM → Measurement.** Bàn giao yêu cầu có diện tích và khu vực cho Sales. Đối soát chi phí → lead → báo giá → đơn hàng → doanh thu theo kỳ. Ghi nhận trùng lặp, đơn hủy và nguồn chưa nối được trước khi diễn giải hiệu quả.
5. **Optimization → Learning.** Nếu lead tăng nhưng ít đơn, kiểm tra chất lượng lead, tồn kho và thời gian phản hồi trước khi đề nghị tăng ngân sách. Lưu giả thuyết, kết quả và quyết định của người phụ trách vào playbook có phiên bản.

Mức tự động hóa đi từ **hỗ trợ chuyên viên**, **tạo bản chờ duyệt**, **thực thi trong quyền đã cấp**, đến **chủ động phát hiện cơ hội và đề xuất cải tiến**. Mỗi bước chỉ dùng đúng dữ liệu, công cụ, quyền và ngân sách đã cho phép. Khi thiếu nguồn, khả năng thực thi hoặc quyền, AMC nêu cụ thể phần thiếu và lưu công việc để người có thẩm quyền tiếp tục.

## Từ kiến thức đến năng lực có thể nghiệm thu

Với từng module, workflow hoặc agent, hồ sơ thiết kế phải xác định được **vấn đề, người đang làm, phần AMC đảm nhiệm, dữ liệu đầu vào, công cụ, đầu ra và người nhận**. Chủ nghiệp vụ giải thích phương pháp phù hợp ngành và thị trường, cách kiểm chứng dữ kiện, thước đo chất lượng, thời gian và chi phí. Ví dụ, đội nội dung có thể bàn giao trang yêu cầu báo giá sau khi QA duyệt. Để chứng minh trang giúp Sales giảm việc, cần đo số yêu cầu đi vào CRM có đủ thông tin để báo giá và thời gian Sales phải nhập lại.

Nghiên cứu tài liệu chính thức, chuyên gia, case study và phần nội dung thực sự truy xuất được của video chuyên ngành. Ghi nguồn, phạm vi áp dụng và giới hạn. Chuyển kiến thức thành Marketing Skill có phiên bản, playbook, workflow theo ngành, rubric, hợp đồng chứng cứ, ca nghiệm thu và tri thức vận hành. Chọn model theo kết quả từng loại việc và chi phí trên bản được chấp nhận. AIRC-500 hỗ trợ phản biện kỹ thuật và nghiệp vụ. Chỉ ghi nhận reviewer tham gia khi có bằng chứng thực thi. [Kho nguồn và tri thức](research/SOURCE_REGISTRY.md) · [Ma trận áp dụng](research/APPLICABILITY_MATRIX.md) · [AIRC-500](../engineering/airc500/README.md)

Trải nghiệm đích gồm AI Command Center, AI Director, AI Workforce, Business Intelligence, Campaign Center, Creative Studio, Marketing Studio, Knowledge Center và Executive Analytics. Mỗi màn hình giúp người dùng ra một quyết định hoặc hoàn thành một tác vụ. Giữ hệ thiết kế xanh rừng và lime, sáng/tối, điều hướng bàn phím và khả năng đọc trên desktop, tablet, mobile. Dữ liệu hiển thị phải phản ánh đúng phạm vi quyền và khả năng vận hành thực tế. [AMC Design System](AMC-DESIGN-SYSTEM.md)

## Chứng minh giá trị kinh tế

Dùng cùng kỳ, cùng loại việc, khối lượng và mức chất lượng để lập đường cơ sở. Đơn vị dưới đây là triệu đồng/tháng. Gọi chi phí nhân sự bình quân đã tính đủ là **L**, số người hiện tại là **N**, số giữ lại để vận hành và kiểm duyệt là **R**. Nếu hai nhóm có cơ cấu lương khác nhau, dùng tổng chi phí thực tế của từng nhóm.

| Đại lượng | Cách tính |
| --- | --- |
| Chi phí trước **B** | N × L + công cụ và vận hành hiện tại |
| Chi phí sau **A** | R × L + phí AMC/AI + công cụ và vận hành còn lại |
| Chênh lệch tháng | B − A. Giá trị âm biểu thị chi phí tăng |
| Tỷ lệ tiết kiệm | (B − A) / B × 100%. Khi B bằng 0, ghi “không xác định” |
| Chênh lệch năm | 12 × (B − A), với giả định khối lượng và chi phí ổn định |
| Chi phí trên công việc được chấp nhận | Tổng chi phí nhân sự, biên tập, QA, model, công cụ và vận hành phân bổ cho toàn bộ các lần thử / số đơn vị công việc được chấp nhận. Khi chưa có bản được chấp nhận, ghi số chi phí đã phát sinh và để trống tỷ số |

**Ví dụ giả định.** Bốn người với chi phí 15 triệu/người và 8 triệu vận hành cho B = 68. Giữ hai người cùng mức chi phí, giả định 10 triệu cho AMC/AI và 6 triệu vận hành còn lại cho A = 46. Chênh lệch là 22 triệu/tháng, khoảng 32,4%, hay 264 triệu/năm. Khi lập phương án đầu tư, tách thêm chi phí chuyển đổi, đào tạo và media spend. Ví dụ này không xác định giá bán AMC, hiệu quả đã đo hoặc số nhân sự doanh nghiệp có thể cắt giảm.

## Commercial Qualification

Mỗi năng lực cần bằng chứng về kỹ thuật, bảo mật, logic nghiệp vụ, chuyên môn Marketing, UX, hiệu suất, chi phí vận hành và giá trị kinh doanh. Ghi SHA, phiên bản nguồn/model, loại dữ liệu, người hoặc AI đã chấm, mẫu số được giao và số hoàn thành. Giữ cả lần thất bại, chi phí sửa và lần chạy hồi quy. Đánh giá chuyên môn cần chuyên viên có thẩm quyền và đối chứng phù hợp. [Giao thức pilot chuyên viên](evaluation/C3-PRACTITIONER-KIT.md)

| Mục tiêu nghiệm thu ban đầu | Bằng chứng phải có |
| --- | --- |
| 100% dữ kiện có cấu trúc đúng | So từng trường với nguồn đã duyệt, kể cả đơn vị, thuế và điều kiện. Báo riêng trường thiếu căn cứ, brief không sinh được bản và mẫu số được giao |
| 0 lỗi nghiêm trọng về phân quyền hoặc tuyên bố thiếu căn cứ | Kiểm tra cách ly khách cùng agency, tenant và brand, thu hồi quyền và đúng revision. Đánh giá mức nghiêm trọng của cả tuyên bố mới trong phần sáng tạo |
| ≥95% nhận định cần chứng cứ có nguồn hỗ trợ | Đếm trên toàn bộ nhận định cần nguồn. Người chấm đối chiếu nội dung nguồn với chính nhận định và điều kiện áp dụng |
| ≥80% bản giao đạt chuyên môn ngay lần đầu | Chuyên viên chấm bản đầu theo rubric đã khóa. Báo số đạt trên toàn bộ nhiệm vụ được giao, số thiếu bản và tỷ lệ trong số bản thực sự được chấm |
| ≥30% giảm tổng thời gian thực hiện | Đo từ nhận brief tới nghiệm thu cho công việc tương đương, gồm làm rõ, sửa dữ liệu, sản xuất, biên tập và QA. Báo riêng ca chưa hoàn tất và thời gian lao động so với thời gian chờ máy |
| Chi phí trên mỗi công việc được chấp nhận có giá trị kinh tế | So với đường cơ sở của khách hàng, ghi đủ chi phí các lần thử, chất lượng và khối lượng duy trì. Ghi riêng kết quả lead, đơn hàng hoặc doanh thu khi đã có dữ liệu đối soát |

**Tại ngày 25/11/2026, Commercial GA vẫn NO-GO.** PR #37 đã đóng điều kiện tích hợp của C3. Trong lần đánh giá trên main, AI chấm 0/10 bản mẫu có thể dùng ngay. Ở nghiên cứu tiếp theo của draft PR #38, AI chấm 0/8 bản Qwen và 2/8 bản tất định dùng ngay trên tám cặp có đủ đầu ra trong mười brief mới. Hai mẫu đo khác nhau. Chưa có số liệu từ chuyên viên để kết luận khả năng thay thế lao động hoặc mức sẵn sàng chi trả. [Kết quả C3 trên main](evaluation/C3-QUALITY-RESULTS.md) · [CI sau merge #37](https://github.com/datnv41001/ai-company/actions/runs/45580265243) · [Nghiên cứu và giới hạn ở #38](https://github.com/datnv41001/ai-company/blob/eb64af438f0a418ed5c951b20387e1d5bf7d982f/docs/evaluation/c3-product-v2/RESULTS.md)

Ưu tiên tiếp tục là nâng chất lượng Marketing Studio, WF-03 và WF-13, đồng thời mở rộng các năng lực khác theo phụ thuộc của roadmap. Giữ nguyên bằng chứng nghiệm thu cũ khi so sánh phiên bản. Mỗi lần bàn giao phải chỉ rõ **ai được giảm việc gì, đầu ra dùng được đến đâu, còn tốn bao nhiêu công sửa, và bằng chứng nào đủ để khách hàng cân nhắc trả tiền**. Khi thiếu phép đo, ghi “chưa đo” cùng phép thử tiếp theo.
