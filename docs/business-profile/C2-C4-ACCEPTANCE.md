# C2 trải nghiệm và C4 nghiệm thu Marketing

## Từ bốn thông tin tới brief đầu tiên

1. **Thiết lập nhanh** dùng tên doanh nghiệp, sản phẩm/dịch vụ chính, nhóm khách dự kiến và mục tiêu. Lưu nháp từng bước, quay lại đúng bản đã lưu. Cho phép Solo/In-house tạo draft brief nghiên cứu khi thương hiệu chưa có nguồn. Output ghi rõ câu hỏi và giả thuyết. Nếu cần public price/efficacy claim, UI chỉ ra dữ kiện và người có thể duyệt còn thiếu.
2. **Bổ sung khi có nhu cầu** nhận URL website, catalogue, tài liệu, guideline hoặc dữ liệu sẵn có qua kênh được cấp quyền. Product/variant/offer có thể được bổ sung dần; landing công khai cần đủ nguồn theo scope và mục đích.
3. **Trích xuất có hỗ trợ** trình bày câu do AI đề xuất cạnh đoạn trích, địa bàn và thời hạn. Mỗi đề xuất tạo draft có provenance. Thiếu qualifier, ngày hết hạn hoặc SKU để pending, không tự thành fact.
4. **Xác nhận và dùng** owner/approver kiểm claim quan trọng, chọn bản có hiệu lực, xem preview, xác nhận run. Trên trang QA/share hiển thị trạng thái mới nhất của nguồn liên quan và hành động sửa. Mất response sau save thì dùng lại request ID; revision conflict mở so sánh bản server và nháp cá nhân.

| Persona | Màn hình cần dùng | Điều quan sát trên desktop 1280 và mobile 390 |
|---|---|---|
| Solo / In-house | Setup 4 trường → draft brief → bổ sung nguồn khi cần | Focus, nhãn rõ, lưu nửa chừng/refresh, chỗ thiếu giá hiển thị unknown. |
| Business | Nhóm sản phẩm/variant → offer theo vùng → xem nguồn và người duyệt | Phân biệt draft/approved, giá theo số lượng, giá đã hết hạn; khôi phục bản nháp của editor sau 409. |
| Agency | Chọn khách + brand → campaign → evidence viewer | Tên brand/SKU/thị trường hiển thị cạnh trích đoạn; switch khách đóng context cũ. Portal chỉ thấy nội dung được share hiện hành. |

## Năm bộ ca C4 tổng hợp

[Bộ ca và expected outcomes](acceptance-cases.json) có clean control và các biến thể sai cho từng persona. Đây là dữ liệu do engineering soạn để kiểm contract. Số đơn hàng, giá và mục tiêu là giá trị fixture.

| Persona | Căn cứ cần khóa | Biến thể cần reject |
|---|---|---|
| Người bán hàng trực tuyến | Áo mưa size L, VND, khu vực giao | Khác size hoặc giữ số nhưng đổi currency |
| Vật liệu xây dựng B2B | Tấm lợp 0.5 mm, từ 200 tấm, bảo hành và địa chỉ giao | Hạ MOQ, bỏ điều kiện, khai bảo hành trọn đời hoặc giao mọi địa điểm |
| Dịch vụ tại chỗ | Gói có khung hẹn và phục vụ một địa bàn | Đổi quốc gia, bỏ qualifier địa bàn hoặc chuyển vùng phục vụ |
| Agency nhiều khách | Sổ A5 của đúng client + brand + campaign, source revision 3 | Chuyển sang khách khác, dùng claim sang SKU khác cùng brand, dùng revision 2 |
| In-house | Ưu đãi theo email cho sinh viên, tiền USD, hạn UTC | Hết hạn ở biên, đưa sang landing, giữ sản phẩm nhưng đảo observed/approved price |

**Mục tiêu và kết quả.** Business objective là kết quả doanh nghiệp hướng tới. Marketing objective mô tả thay đổi về nhu cầu/lead. Campaign KPI định lượng mục tiêu chiến dịch. Operational KPI theo dõi chất lượng/throughput. Efficiency KPI ghi tỷ lệ chi phí/thời gian trên kết quả. Với mỗi KPI lưu `baseline` kèm kind `unknown` hoặc `historical`, một target riêng, nhiều observation có đơn vị/mẫu số và window thực tế, measurement method, owner cùng nguồn. Hypothesis là loại record riêng để thẩm định; observed result và historical baseline đòi nguồn có revision. Chỉ so actual với target khi cùng định nghĩa/mẫu số và kỳ tương thích; mẫu số 0/không biết được ghi N/A. [Fixture năm tầng KPI](synthetic-snapshot.json)

## Kế hoạch đo sau C2/C3

Làm cùng brief trên luồng nhập lại và luồng profile đã pin, đảo thứ tự giữa người tham gia để giảm học thuộc. Ghi persona, phiên bản, điều kiện đầu vào và trình độ; tách số liệu tổng hợp, AI mô phỏng và nhãn độc lập của người dùng. Dữ liệu thật chỉ thu khi có ủy quyền. Mỗi persona có control hợp lệ lẫn lỗi, cùng rubric và scope. Không suy rộng từ một fixture.

| Chỉ số | Định nghĩa có thể tái lập | Trạng thái C0 |
|---|---|---|
| Thời gian chuẩn bị brief | Thời gian hoạt động từ mở brief đến draft dùng được, loại thời gian chờ reviewer và ghi riêng elapsed | Chưa đo ở người dùng |
| Số lần nhập lại | Số field/giá trị đã có trong hồ sơ nhưng buộc nhập lại trong cùng campaign | Chưa đo |
| Claim & qualifier đúng | Cặp asset × claim có scope, nguồn và qualifier đúng / tổng cặp đã kiểm; báo lỗi thiếu và thừa riêng | Chỉ có expected synthetic |
| First-pass acceptance | Bản đầu được QA domain chấp nhận / tổng bản đầu có thẩm định | Chưa đo |
| Thời gian sửa của con người | Phút active sửa từ finding tới bản chấp nhận, phân theo nguyên nhân | Chưa đo |
| Tái lập | Cùng snapshot, policy và inputs tái tạo đúng source handles/digest; đo khác biệt generation riêng theo seed | Chỉ kiểm hợp đồng fixture C0 |
| Cost per accepted output | Chi phí xử lý đối soát / số output được chấp nhận; báo token, phí provider và thời gian máy riêng | Chưa có output thực để tính |

QA nghiệp vụ cùng Product Owner ghi số ca, phân bố lĩnh vực, annotations và bất đồng. Kết quả dữ liệu tổng hợp đạt chưa đủ để đóng gate phát hành thương mại.
