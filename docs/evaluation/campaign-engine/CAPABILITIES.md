# Năng lực phòng Marketing và điều kiện nghiệm thu

Mốc đối chiếu là main `837ec9fc`, ngày 26/11/2026. Mỗi dòng mô tả phần đã có thể giao cho AMC và bằng chứng tương ứng. Cột kỹ thuật xác định phạm vi đã kiểm trên dữ liệu tổng hợp. Cả 19 dòng cùng có ba trạng thái: **chuyên môn chưa được chuyên viên độc lập nghiệm thu, thực thi ra nền tảng bên ngoài chưa mở, thương mại NO-GO**. Quyết định QA và tiếp nhận trong portal nội bộ có sổ biên nhận riêng. Dữ liệu fixture chưa tạo ra một đơn vị công việc được doanh nghiệp thực tiếp nhận. [Sứ mệnh](../../PRODUCT_MISSION.md) · [Đặc tả](../../PRODUCT_SPEC_V1.md) · [Hợp nhất](INTEGRATIONS.md)

| Bộ phận | Chức năng hiện có và thực thi tự động | Nghiệm thu kỹ thuật trong sandbox | Việc người dùng còn làm và phép thử kế tiếp |
|---|---|---|---|
| Lãnh đạo Marketing | Director phân công hai vai trò cho từng workflow đã kích hoạt | Có DAG, request và checkpoint | Chủ doanh nghiệp chốt ưu tiên đa chiến dịch và tiêu chí dừng |
| Điều phối chiến dịch | Ghép manifest, chia gói việc, sinh lịch theo thời hạn | Có phiên bản kế hoạch, trạng thái và biên nhận xếp việc | Điều phối viên xử lý xung đột mục tiêu và năng lực sản xuất |
| Vận hành agency | Tách tenant, client, brand, quyết định chia sẻ và hồ sơ chi phí | Có test RLS giữa khách cùng agency và restore | Quản trị viên cấp quyền, đối soát phí thực và hợp đồng dịch vụ |
| Nghiên cứu thị trường | WF-03 đọc dữ kiện được chọn, lập bản đề xuất | Có run và nguồn ghim, chưa thu thập dữ liệu thị trường độc lập | Chuyên viên kiểm thời điểm, địa bàn và tính đại diện |
| Nghiên cứu khách hàng và ICP | Lưu nhóm mua, giả thuyết và yêu cầu còn thiếu | Kiểm phạm vi của ICP trong manifest | Phỏng vấn khách, tìm bằng chứng bác bỏ giả thuyết |
| Chiến lược Marketing | Soạn định vị và kế hoạch đo cho mục tiêu được giao | Studio có trường chiến lược, revision và QA | Kiểm khác biệt thực chất, phương án thay thế và tính khả thi |
| Quản trị thương hiệu | Áp dụng guideline theo brand và phiên bản | Truy nguyên nguồn, kiểm thay guideline và thu hồi | Chủ thương hiệu duyệt giọng điệu, quyền dùng và ngoại lệ |
| Nội dung | WF-13 sinh bản trang đích, CTA và gợi ý biên tập | Kiểm nguồn, chỉnh sửa, QA đúng revision | Editor sửa copy, kiểm sức thuyết phục và thời gian tới bản dùng được |
| Thiết kế và video | Soạn brief hướng dẫn thiết kế bằng quy tắc | Có văn bản và digest | Cần người sản xuất, kiểm bản quyền và đánh giá file ảnh/video |
| Mạng xã hội | Soạn đoạn nội dung từ bối cảnh chiến dịch | Có draft trên kế hoạch | Biên tập định dạng, duyệt, đối soát quyền từng kênh |
| SEO và GEO | WF-13 tạo tiêu đề và mô tả gắn landing | Có đầu ra và chữ ký cho nhóm SEO | Kiểm search intent, khả năng lập chỉ mục và kết quả tìm kiếm |
| Website, landing và CRO | Studio tạo bản nội dung trang gắn hành động mua | QA, chia sẻ và phản hồi trên snapshot | Thiết kế và triển khai trang thật, chạy thử nghiệm có đối chứng |
| Thương mại điện tử | Ghim SKU, giá, đơn vị, thuế và điều kiện khi có nguồn | Fixture nhiều đơn vị, kiểm claim và qualifier | Chủ sản phẩm xác nhận tồn, thanh toán và tình trạng đơn thật |
| Quảng cáo hiệu suất | Soạn copy và trần media đề xuất | Có draft, kế hoạch và số tiền mô phỏng | Người lập media chia nhóm, xét giả thuyết, thiết kế phép thử, phê ngân sách |
| Tự động hóa Marketing | Ghi lịch có QA và thực thi thủ công trong sandbox | Có lịch, quyền và biên nhận lệnh | Theo dõi retry, hết hạn và hủy; tích hợp nền tảng cần một gate riêng |
| CRM, tạo lead và vòng đời | Bàn giao RFQ, Sales quyết định các bước sau | Kiểm nguồn, bàn giao, từ chối, hủy và hoàn tiền trên fixture | Sales liên hệ theo consent, xác nhận kết quả dịch vụ thực |
| Phân tích Marketing | Tính funnel và đối soát doanh thu theo biên nhận | Tách doanh thu có nguồn, thiếu nguồn và điều chỉnh | Analyst đối chiếu với sổ giao dịch và chi phí thực tế |
| QA Marketing | Kiểm claim, nguồn và revision; lưu quyết định độc lập | Kiểm A→B→A, chia sẻ, thu hồi quyền và lịch sử | QA nghiệp vụ đọc bằng chứng, quyết định tính đúng, phù hợp và quyền sử dụng |
| Tri thức doanh nghiệp | Ghim nguồn, policy, guideline, mục tiêu vào manifest | Kiểm dependency, scope, thời hạn, sự kiện bất biến | Người quản trị sửa dữ liệu nguồn, phê duyệt và đo tác dụng khi tái sử dụng |

## Đối chiếu chất lượng và chi phí

Ở integration #44, 3 lượt Workforce thực hiện 9 lần gọi, dùng 5.185 token đầu vào và 864 token đầu ra. Trong 34 trường được xem, bộ soạn theo quy tắc thay 22 đề xuất của model, tạo riêng 8 trường, có 3 trường trùng và giữ 1 giá trị riêng của model. Phạm vi này chưa đo thời gian tiết kiệm, tỷ lệ chuyên viên dùng được ngay hoặc giá trị kinh tế. Pilot phải giữ mẫu số công việc được giao, nhật ký lần đầu, kết quả của các lần thất bại, công sửa, QA, chi phí tính toán và biên nhận bản cuối. Khi chưa có công việc được doanh nghiệp tiếp nhận, chi phí trên một công việc được tiếp nhận chưa xác định. [Biên nhận integration #44](https://github.com/datnv41001/ai-company/actions/runs/45621868849)

Các nhánh G01, Content Factory, sandbox vận hành và đánh giá model là các hạng mục đang review. Chỉ cập nhật từng dòng sau khi đối chiếu commit tích hợp, kết quả thử đúng đầu ra và quyết định nghiệm thu tương ứng. AIRC-500 có thể kiểm chứng bằng chứng kỹ thuật; pilot nghiệp vụ cần người hoạt động đúng vai trò.
