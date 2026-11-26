# Nghiệm thu bản sửa RFQ và hai gói sản xuất Marketing

## 1. AMC-R57-01

Main trước sửa chấp nhận đơn vị diện tích của catalog. Trong head review #57, một ký tự thừa khiến cả tạo RFQ lẫn bổ sung hồ sơ với 12.375 m² và commercial details hợp lệ cùng trả 409. Khôi phục đúng chuỗi UTF-8 ở một dòng trong hợp đồng CRM, giữ các đơn vị còn lại và cập nhật fingerprint của runtime. GREEN có 11 kiểm thử trên SQLite và PostgreSQL. Reviewer kỹ thuật độc lập chạy lại RED và GREEN trên SQLite, gồm kiểm revision và những lần ghi bị từ chối. [Hướng dẫn, XML ban đầu và kết quả sửa](R57-MATERIAL-UNITS.md)

## 2. Phiên bản và thẩm quyền

Maintainer `datnv41001` đã merge #57 tại `26578088519d99f4aed5be9c516ac247f3d4735e`. Hai parent khớp base và head đã kiểm. Tree `744f35a73ddf069e7de2c0c34cc7d9de4226ee0f` trùng trial `8a2a6796c06828d0d4ff7b897a41bfe50c88b1bb`. CI trước merge đạt 9/9 job bắt buộc, 622 đạt và 2 skip ở cả ba JUnit. [PR #57](https://github.com/datnv41001/ai-company/pull/57) · [Push head](https://github.com/datnv41001/ai-company/actions/runs/45777417341) · [PR head và integration](https://github.com/datnv41001/ai-company/actions/runs/45777424779) · [CI trên chính main](https://github.com/datnv41001/ai-company/actions/runs/45780019694).

Việc phát triển sau merge nằm ở PR riêng để Product Owner phản biện. Nội dung dưới đây thuộc nhánh tiếp theo. V1 giữ phạm vi 49 module, 37 vai trò và 24 workflow. Production và Commercial GA vẫn **NO-GO**.

## 3. Nghiên cứu đã thực hiện

Đọc tài liệu Odoo 19.0 về đơn vị trên chứng từ và nguồn parser llama.cpp đúng phiên bản; hai nguồn Google Help và tài liệu developer về chuyển đổi offline; hai hướng dẫn TikTok về test creative và storytelling. Đối chiếu báo cáo BetterIdeas, bài LinkedIn của người làm nghề và một thảo luận agency trên Reddit. Hướng dẫn Google nêu thay đổi từ 15/06/2026 với triển khai offline conversion mới. Thiết kế hiện tại giữ kết quả trong sandbox. YouTube chỉ trả metadata/mô tả, Facebook yêu cầu đăng nhập. [Sổ nguồn có phạm vi đọc và giới hạn](../../research/SOURCE_REGISTRY.md) · [Thiết kế measurement và kiểm thử offline](../department-study/OFFLINE-CONVERSION.md)

## 4. Bốn luồng đã bàn giao

| Luồng | Đầu ra và đối tượng sử dụng | Dependency và giới hạn |
| --- | --- | --- |
| Engineering & Reliability | Duy trì RFQ, CompleteRFQ, hợp đồng tri thức và lock trên đúng phiên bản. | #57 được xử lý riêng. Hai brief sau đó dùng chung Studio và QA; không đổi schema vì thử nghiệm. |
| AI Intelligence & Business Knowledge | Người điều phối có trace từ lời khách, nguồn đã ký, giá trị hiện hành, policy, người được quyền tới câu hỏi hoặc chuyển nội bộ. | Fixture song ngữ và parser được kiểm offline. Chưa đo khái quát ngoài fixture hoặc tuyển practitioner. |
| Marketing Production & Execution | Creative lead nhận hai bộ campaign với tài sản đúng brief, timeline, ảnh, landing, hai hook và KPI. | Dựa vào giá, đơn vị, scope và quyền ảnh của từng revision. Có thể diễn tập nội bộ. Media thật cần ngân sách và quyền riêng. |
| Business Qualification & Economics | Điều phối viên có thư mời, consent, mã riêng và quy trình A/B/C/D để đo giá trị. | Chưa gửi thư. Số người tham gia, số việc được doanh nghiệp chấp nhận đều là 0. |

## 5. Đầu ra để mở và dùng

- **Khe Gọn, B2B.** Marketing bàn giao cách quay thao tác tháo vách đúng mẫu, giá tham khảo 380.000 đồng/hộp đã gồm thuế và MOQ 5 hộp. Sales nhận yêu cầu có số hộp, địa bàn, thời điểm cần hàng. [11 hạng mục chiến dịch](../campaign-production-review/index-tray.md) · [Storyboard, 25 giây](../campaign-production-review/index-tray/storyboard.png) · [Landing tổng hợp](../campaign-production-review/index-tray/landing.html)
- **Luồng Rõ, dịch vụ.** Người dựng có sa bàn và sơ đồ luồng nhận hàng. Giá tham khảo 760.000 đồng/lượt đã gồm thuế, tối thiểu một lượt. CTA v2 gửi đề nghị để người phụ trách đối chiếu lịch. [11 hạng mục chiến dịch](../campaign-production-review/receipt-map.md) · [Storyboard, 27 giây](../campaign-production-review/receipt-map/storyboard.png) · [Landing tổng hợp](../campaign-production-review/receipt-map/landing.html)

Mỗi hồ sơ nối research với ICP và positioning, journey, kế hoạch và KPI, lịch/nội dung theo kênh, creative brief và ảnh, script/storyboard, landing/form, media plan, chăm sóc lead và đối soát. Tài sản cũ khác SKU hoặc sai MOQ được ghi lại ở phần so sánh. Ảnh Studio là thiết kế mẫu; storyboard mới là sơ đồ tiền kỳ. Chưa có footage quay tại doanh nghiệp. [Nguồn gốc và cách chạy lại](../campaign-production-review/README.md)

## 6. Chất lượng trước và sau

Reviewer AI đọc bốn treatment đã ẩn phương pháp, chấm theo bảy nghĩa vụ. B2B đi từ 1/7 ở đối chứng lên 7/7 ở bản biên tập v1; dịch vụ từ 0/7 lên 7/7. Cùng lúc, reviewer chỉ ra rubric bỏ sót chữ **giá tham khảo** ở cả hai bản. V2 đã khôi phục điều kiện đó, ngắt dòng cho phụ đề và ghi rõ CTA gửi đề nghị. Điểm 7/7 thuộc v1. V2 có kiểm thử dữ liệu, thời lượng và ràng buộc phụ đề; chưa có chấm mù nghiệp vụ trên v2. Giữ cả kết quả có lợi và phần phản biện ở [hồ sơ chấm](../campaign-production-review/QUALITY.md).

## 7. Phần năng lực đã tiến bộ

Runtime đã chạy qua hai brief, QA theo bản, ảnh và landing có thể kiểm, giao dịch nhận form và cấp quyền người nhận. Nhóm sản xuất bổ sung công việc biên tập dựa trên nguồn, chuyển kịch bản thành cue có thời lượng, storyboard, captions dùng được và hai hook chỉ thay đoạn đầu. Người biên tập là Codex. Biên nhận không chứng minh các vai trò video, media buyer hay creative director đã trở thành worker tự vận hành. [Ai làm, ai duyệt, binding còn thiếu](../campaign-production-review/SKILLS.md) · [Kiến thức, SOP, công cụ và chi phí theo chín nhóm nghiệp vụ](../department-study/advisory/TASK-ROUTING.md)

## 8. Điểm yếu AI và phép thử tiếp theo

Trên dữ liệu cũ, Qwen chọn đúng loại quyết định ở 14/24, đạt toàn bộ hợp đồng ở 7/24, có 13/24 đầu ra vi phạm. Quy tắc hiện hữu và bộ bổ sung đều đạt 8/24. Qwen đạt 7/8 ask, 0/8 ready, 0/8 clarify_policy dùng được. Trong tám ca policy, sáu đúng nhãn thô. Chỉ 3/5 câu hỏi Qwen phát hiện thêm đạt tất cả tiêu chí ở cả hai người đọc AI. Chưa thay baseline hoặc đưa Qwen vào runtime.

Trong phép thử mới, đã chạy 12 trace Việt–Anh, chín ca kiểm điều kiện từ chối, và phân loại đúng 14 fixture GBNF bằng parser ghim (sáu nhận, tám từ chối). Hai ví dụ đúng cú pháp vẫn sai về nghiệp vụ. Không có lượt inference mới. Nếu muốn so phương pháp bằng model, phải khóa cohort mới và điều kiện dừng rồi xin quyền riêng. [Protocol và nguồn tái lập](../department-study/advisory/TASK-HANDOFF.md)

## 9. Kinh tế và practitioner

North Star là Business-accepted Marketing Work Units. Phiếu AI và receipt máy chạy đang ở mức kỹ thuật. Số việc doanh nghiệp thực tế chấp thuận là 0. Phí dịch vụ model và chi media mới trong vòng này bằng 0; điện, công của người làm nghề, conversion lift và chi phí đầy đủ trên việc khách chấp nhận chưa đo. Ghi cả công sửa, QA, lỗi nặng, lần thử thất bại và thời gian chờ khi có consent. [Thư mời có thể điền để gửi riêng](../department-study/PILOT-ABCD/INVITATION.md) · [Cách chuẩn bị và chốt phiếu](../department-study/PILOT-ABCD/OFFICIAL.md)

## 10. Quyết định tiếp theo cho reviewer

Ưu tiên trước mắt là để người dựng độc lập đọc storyboard và phụ đề v2 mà không cần người soạn giải thích, sau đó để Sales/Service xác nhận bản giao đúng điều kiện thực. Kiểm xem người xem có phân biệt giá một hộp với giá một khay và phân biệt lời đề nghị khảo sát với lịch đã xác nhận. Đối chiếu CTA của ảnh/landing Studio cũ với CTA biên tập mới trước khi cấp quyền dùng tài sản. Nếu hiểu nhầm lặp lại, sửa tại nguồn contract/template trên một revision có hồi quy, rồi chấm lại. Người sở hữu ngân sách quyết định riêng mọi thử nghiệm phát sinh phí. [Bảng cơ hội và tiêu chí](../../research/PRODUCT_OPPORTUNITIES.md)
