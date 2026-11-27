# Vòng #61 · Sales có thể quyết định việc gì từ một yêu cầu báo giá?

**Đề xuất cho Product Owner:** dành lát cắt coding kế tiếp cho **một phiếu đối soát RFQ chỉ đọc**, trên một inquiry tổng hợp, ở một thời điểm xác định. Sales cần biết hồ sơ đã đủ để xử lý chưa, dữ kiện nào còn thiếu, ai có quyền xác nhận và chứng từ nào cho thấy đã báo giá. Khe Gọn hiện nối được 1 visit → 1 submission → 1 inquiry trong sandbox, với 0 RFQ đủ điều kiện và 0 đơn. Phiếu này cho phép Sales kiểm tra lý do trước khi AMC đầu tư vào tối ưu creative hoặc đưa một chỉ số lên dashboard.

## 1. Main sau merge #60

| Mốc | Giá trị |
|---|---|
| Base trước merge | `4140563a89539acd19f1a7d5a16662c8dec5f6af` |
| Head được duyệt | `edbca9483f59a20f8c3d1f54123a92e353cc3426` |
| Trial | `7a506789ca4183f59d9e6e0d2b9486a86d692879` |
| Merge trên main | `83894ffefa0dbc720ae3d887e2f90e53f4b23ae0` |
| Git tree của head, trial và merge | `1c40c678b0556cfa512b0a5f59c4eef457c60ef6` |

CI của merge đã hoàn tất **3/3 job bắt buộc**, **684 passed, 2 skipped**, **22 đường nâng lên v26** và **restore khớp 34 bảng**. [JUnit sau merge, bản lưu trong Git](main-junit.zip)

Biên nhận ghi kết quả thực tế của workflow **push trên main**, hai parent, JUnit, SHA-256, đường nâng cấp và restore. Hồ sơ #61 được viết sau merge trên một nhánh tài liệu riêng. Người tiếp quản so `git rev-parse 'HEAD^{tree}'` với tree trong bảng khi kiểm mã #60; checkout có thêm hồ sơ #61 mang tree tài liệu khác. [Main certification](MAIN-60.json) · [Actions trên merge](https://github.com/datnv41001/ai-company/actions/runs/45931055472) · [Bản merge](https://github.com/datnv41001/ai-company/commit/83894ffefa0dbc720ae3d887e2f90e53f4b23ae0)

## 2. Quyết định từ review

Reviewer đóng AMC-R60-01, đóng AMC-R60-02 trong phạm vi Chromium đã thử và chấp nhận R59-01 đến R59-05 trong lát cắt đã chứng minh. AMC-R60-03 vẫn mở ở cổng production. Baseline schema v26 và WF-08 @1/@2, cả bằng chứng lỗi trên bản cũ, tiếp tục dùng cho hồi quy. [Mức độ, owner, regression và rollback](ENGINEERING.md)

## 3–4. Bốn luồng và kết quả nghiên cứu

| Luồng | Kết quả có thể dùng và giới hạn |
|---|---|
| A · Kỹ thuật | Đã kiểm chứng merge và tính toàn vẹn hai ZIP. Thiết kế đo render tách chờ khóa, giữ khóa và thời gian người dùng phải đợi; có đối chứng tenant bên cạnh, lỗi trước commit và replay sau commit. Chưa có ngân sách chạy tải. [Kế hoạch đo](ENGINEERING.md) |
| B · AI và kiến thức nghiệp vụ | Lần theo gate C3, Qwen, O-09 và R52–R60. Ở cohort O-09 triển vọng trước đây, đầy đủ contract đúng 7/24 với Qwen, 8/24 với mỗi control. Hướng thử là thay một điều kiện nguồn và chấm cả lựa chọn lẫn căn cứ, trên cohort mới được giữ kín. Chỉ chạy lại fixture công khai để xác nhận đường đọc; chưa có kết quả generalization mới. [Kết quả âm, lab và thiết kế benchmark](INTELLIGENCE.md) |
| C · Marketing và Sales | Đã đối chiếu chín nhóm năng lực với register V1. CRM có trạng thái vận hành hiện hành; chỉ số RFQ chính thức cần có decision có thẩm quyền, cutoff, đơn vị attribution và mẫu số assignment. Khe Gọn giữ `primary_measurement=null`. [Hợp đồng đề xuất, so sánh chín nhóm và ca nghiệm thu](MARKETING.md) |
| D · Người dùng và kinh tế | Hai nghiên cứu thực địa cho căn cứ thiết kế để đọc thời gian cùng chất lượng, tách loại nhiệm vụ và kinh nghiệm người làm. Đã chuẩn bị checklist nhân sự, rủi ro lộ nhánh C/D, receipt trên revision 1 và chi phí đầy đủ theo protocol gốc. Tám việc là thiết kế thăm dò; hiện 0 assignment chính thức, 0 quyết định tiếp nhận thực. [Readiness, nguồn và điều kiện mở pilot](PRACTITIONER.md) |

## 5–6. Chọn lát cắt đủ nhỏ

| Phương án | Dependency | Effort sơ bộ và rủi ro | Giá trị kiểm được |
|---|---|---|---|
| **A. Phiếu đối soát một RFQ** | Sales Ops chốt policy, owner, phân biệt đủ dữ kiện với xác nhận; có journal và fixture đã ký | 2–4 ngày công kỹ thuật sau khi duyệt phạm vi. Rủi ro chính là diễn giải trạng thái mới nhất thành lịch sử | Sales tự chỉ đúng nguồn và bước xử lý. Marketing biết trường nào cần bổ sung để tránh trả lại. |
| B. Research/ICP theo lý do inquiry thiếu hoặc bị trả | Có lý do đã đối soát, quyền dùng nguồn, người nhận xác nhận lại phân khúc | 2–4 ngày công kỹ thuật cho bản tổng hợp sandbox. Một vài inquiry dễ dẫn tới kết luận về cả phân khúc | Research giao giả thuyết theo nguồn và câu hỏi phỏng vấn có thể bác bỏ. |
| C. Benchmark handoff O-09 ngoài runtime | Custodian giữ cohort chưa lộ, reviewer ngữ nghĩa, giả thuyết mới so với hai rule và Qwen cũ | Chuẩn bị và chấm 12 cặp VI/EN; công sức/chi phí tính theo người chấm và điều kiện giữ kín, chưa được định giá. Rủi ro học thuộc fixture hoặc luôn từ chối | Phân biệt trường hợp hỏi khách, chuyển chủ chính sách và chuyển đúng Sales/Service. |

Ưu tiên A vì evidence đến được inquiry nhưng Sales vẫn thiếu lời giải thích tái lập theo thời điểm. Lát cắt kết thúc ở bản xuất chỉ đọc cho một inquiry; quyền ghi quyết định, KPI chính thức, traffic, điều phối pilot và thay renderer nằm ở các quyết định sau. B và C có thể chuẩn bị bằng tổng hợp tài liệu. Charter vẫn là 49 module, 37 vai trò logic, 24 workflow mẹ, kiến trúc bảy lớp và roadmap P00–P12.

## 7. Nghiệm thu cho PR coding được đề xuất

- **Kỹ thuật.** Cùng inquiry, tại hai cutoff trước/sau khi sửa lượng, trả về đúng revision, lý do, unit, MOQ và policy/source digest tại từng mốc. Gửi lặp có một hiệu ứng. Thiếu thẩm quyền, nguồn đến muộn, hủy, consent bị thu hồi hoặc thiếu liên kết đều hiện rõ. Hai khách cùng agency và cùng tên campaign vẫn chỉ đọc được hồ sơ có quyền. Chạy hồi quy measurement, scope PostgreSQL và so sánh snapshot cũ. [Ca kiểm và điều kiện xảy ra](MARKETING.md)
- **Nghiệp vụ.** Sau khi có quyền UAT, Sales Ops đọc hai hồ sơ tổng hợp có đối chứng, tự xác định bước tiếp theo, dữ kiện còn thiếu và chứng từ trên đúng phiên bản. Marketing lead xác định được ai phải sửa form hoặc nguồn. Ghi thời gian tra, số lần phải hỏi và lý do chấp nhận/trả; một bản xuất đúng schema chỉ hoàn thành phần kỹ thuật.

## 8. Quyết định cần đúng chủ sở hữu

| Ai quyết định | Việc cần quyết |
|---|---|
| Product Owner | Có ưu tiên phiếu RFQ chỉ đọc trước Research/ICP không? Có chọn một inquiry sandbox làm ranh giới PR kế tiếp không? |
| Sales Operations và chủ offer | Ai được xác nhận đủ chuẩn; bằng chứng và ngày hiệu lực của SKU/đơn vị/MOQ, consent và điều kiện bán; cách sửa/hủy quyết định hoặc ghi rõ MOQ không áp dụng. |
| Chủ KPI | Sau bước đối soát, có mở thiết kế cohort hay không; nếu có, chốt cửa sổ, đơn vị phân bổ, ngưỡng mất liên kết và xử lý sự kiện muộn **trước** T0. 21+7 đang là đề xuất. |
| Custodian, chủ ngân sách và người tham gia | Điều kiện tổ chức, giữ mù, consent, quyền giữ khóa và vật liệu, trần thời gian/chi phí. Infrastructure cần phê duyệt tài nguyên riêng cho phép đo renderer. |

## 9. Giới hạn và tiếp quản

Tài liệu, đối soát source, phép replay đã công bố và hai gói lịch sử có thể kiểm ngay. Độ hữu ích với practitioner, hiệu quả tăng chuyển đổi và full cost per business-accepted work unit còn chưa đo; chi phí trên việc được nhận là `null`. Production và Commercial GA giữ **NO-GO**.

**Câu hỏi dành cho Independent Reviewer:** với một yêu cầu đủ SKU, đơn vị và MOQ nhưng thiếu receipt Sales xác nhận, phiếu có đủ để Sales biết cần quyết gì, đồng thời ngăn dashboard ghi nhầm thành RFQ đã được chấp thuận hoặc doanh thu không?
