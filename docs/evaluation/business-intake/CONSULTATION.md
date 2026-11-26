# Tư vấn yêu cầu dưới MOQ và đối soát báo giá

Để kiểm đường nâng cùng schema, chạy `python tests/check_consultation_cutover.py --container amc-test-pg` trong môi trường PostgreSQL loopback của job API. Phép thử dùng publisher và API thật của #55 để lập kế hoạch và ghi journal, sao lưu database cũ, chạy publisher mới hai lần, so từng hàng journal rồi mở bản restore bằng API cũ. Trên Windows thiếu bộ lệnh pg_dump/pg_restore, tùy chọn `--physical-copy` tạo bản sao database PostgreSQL khi các kết nối writer đã đóng. Lượt thử cục bộ đầu tiên dừng trước nâng cấp do thiếu binary pg_dump. Bản Linux CI sử dụng định dạng archive với pg_dump và pg_restore thực.

## AMC-R55-01 · Người phụ trách tư vấn

Trên PR #55 ở `c5c63295`, form nhận ba hộp khi điều kiện bán là năm hộp. Marketing đọc được hồ sơ. Bước phân công Sales chỉ nhận trạng thái `qualified`, và Sales chỉ nhìn thấy hồ sơ đã được giao. Vì vậy biên nhận cũ chứng minh việc tiếp nhận để tư vấn, còn việc giao cho người tư vấn là khoảng trống.

Trong **Chiến dịch → Bàn giao nghiệp vụ**, người có grant điều phối Marketing hoặc chủ kinh doanh chọn yêu cầu có sự đồng ý phản hồi báo giá rồi chọn **Giao tư vấn**. Máy chủ kiểm tra grant Sales của người nhận, tenant, campaign, nguồn hồ sơ và revision. Trên bàn Sales của mình, người nhận ghi chú hoặc cập nhật các thông tin khách cung cấp. Phiếu đã gửi, nguồn trang, hợp đồng intake và consent giữ nguyên để đối chiếu với hồ sơ hiện tại. Ghi nhận tại đây mô phỏng công việc Sales trong sandbox.

| Bước | Người thực hiện | Kết quả |
|---|---|---|
| Khách gửi đủ trường form | Phiên thử của gói landing đã ký | Dưới MOQ vào `received`, có revision và receipt. |
| Giao tư vấn | Điều phối có grant và người nhận Sales có grant hiện hành | `consulting`. Sales được giao thấy hồ sơ. Đổi người phụ trách chuyển quyền đọc lại receipt của hồ sơ sang phạm vi hiện hành của từng người. |
| Ghi nhận tư vấn | Sales được giao | Ghi actor, ghi chú, dữ liệu thay đổi và revision. Thiếu thông tin hoặc vẫn dưới MOQ thì tiếp tục tư vấn. |
| Đủ điều kiện sau tư vấn | Máy chủ tính lại điều kiện từ hồ sơ thương mại và MOQ đã ghim | `awaiting_assignment`. Người tư vấn có thể đọc kết quả và gửi lại đúng biên nhận đã thành công. Cả API cũ và mới đều chặn quyết định thương mại cho đến khi điều phối giao xử lý báo giá. Giao cho người khác sẽ thu hồi quyền đọc hồ sơ và replay của người tư vấn cũ. |
| Phân công thương mại → tiếp nhận → báo giá → đơn | Điều phối, sau đó Sales được giao | Mỗi bước có trạng thái tiền nhiệm, revision và receipt riêng. Doanh thu sandbox chỉ ghi nhận khi người được quyền xác nhận số tiền. |

Lựa chọn này tái sử dụng phạm vi đã ký, hộp thư có phân công, cơ chế CAS và journal hiện có. Mở thẳng bước `assign` thương mại cho hồ sơ dưới MOQ sẽ cho phép đi qua `accept` để phát hành báo giá. Client gọi API tổ chức cũ vẫn có thể xử lý các ca thương mại hợp lệ. Tư vấn phải đi qua Role Desk của người nhận.

## AMC-R55-02 · Nghĩa của chỉ số

`intake_measurement.version=intake-funnel/2` là phần bổ sung tương thích trong API sandbox. Chọn đúng plan và contract digest. `landing_visits` đếm phiên hợp lệ. `valid_submissions` đếm hồ sơ từ form hợp lệ và có nguồn khớp. Với hành trình RFQ, mỗi lượt gửi tạo một `inquiry`. `manual_requests` ghi riêng liên hệ nhập tay.

| Trường trên hành trình RFQ | Cách đếm và thời gian |
|---|---|
| `inquiries`, `qualified_rfqs` | Hồ sơ form và số hồ sơ từng đủ điều kiện báo giá trên vòng đời plan. Một hồ sơ đã đạt điều kiện chỉ được tính một lần. Khóa API cũ `qualified_quotes` là alias cho `qualified_rfqs`. |
| `sales_accepted`, `quotes_issued`, `orders` | Hồ sơ từng có quyết định tiếp nhận của Sales, từng phát hành báo giá, từng ghi đơn. Hủy sau đó vẫn giữ dấu mốc lịch sử. |
| `current_states` | Số hồ sơ theo trạng thái mới nhất, gồm cả từ chối và hủy. Tổng bằng số inquiries. |
| `confirmed_revenue_vnd` | Doanh thu sandbox đã xác nhận hiện còn hiệu lực, trừ hoàn tiền, loại đơn đã hủy. Có thể giảm sau khi số đơn lịch sử đã tăng. |

Khoảng thời gian của bảng là vòng đời phiên bản kế hoạch đã chọn. KPI lịch hẹn có cửa sổ cohort đã duyệt nằm riêng trong `report.primary_measurement`. Báo cáo CRM toàn chiến dịch vẫn bao gồm liên hệ nhập tay và các kế hoạch khác. Bộ đo này chưa phản ánh doanh thu hoặc tư vấn thực tế.

## Chạy lại, tương thích và phục hồi

1. Checkout head của PR và dùng clone có lịch sử đến `c5c63295`. Cấu hình PostgreSQL test theo job API của CI. Chạy publisher `python migrations/apply.py` trước khi phục vụ lưu lượng. Core v26 giữ nguyên. Publisher cài phiên bản 2 của hàm Role Desk đã ký; runtime mới kiểm tra phiên bản này khi khởi động.
2. Chạy `python -m pytest -q tests/test_production_studios.py -k "index-tray or (restricted_production and False)"`. Đặt `AMC_CONSULTATION_EVIDENCE` vào thư mục artifacts để lưu hai biên bản tổng hợp. Ca PG chạy cả API thật của head tiền nhiệm, hai người dùng, hai tab cạnh tranh một revision, thu hồi grant và phân công lại.
3. Chạy `python -m pytest -q tests/browser_role_desk.py -k assigned_sales` với Chromium. `AMC_DESK_SCREENSHOTS` chọn nơi lưu ảnh và thời gian phản hồi. [Ca trình duyệt](../../../tests/browser_role_desk.py) · [Ca chuyển bước và đối soát](../../../tests/consultation_fixtures.py)
4. Khi rollback, dừng writer, giữ journal và backup; thống kê cả `consulting` và `awaiting_assignment`. API cũ đọc được hồ sơ đã giao. Runtime mới có thể hoàn tất tư vấn và phân công thương mại trước khi rút, hoặc giữ nguyên hai trạng thái đó để tiếp tục khi bật lại runtime tương thích. Xác minh bản khôi phục và receipt trên DB riêng trước khi đổi writer. [Quy trình rollback và đối soát](../sandbox-operations/CUTOVER.md)

Chi phí thử nghiệm gồm thời gian CPU và công kiểm tra cục bộ, chưa đo chi phí lao động thực tế. Số tư vấn viên nghiệp vụ tham gia bằng 0. Phản biện dành cho reviewer là kiểm tra thời điểm người tư vấn mất quyền khi hồ sơ được chuyển sang người bán khác, rồi đối chiếu từng biến động doanh thu sau hoàn tiền và hủy với lần đầu ghi nhận đơn.

## Điểm kiểm tra trong source của bản sửa

- R55-01 áp dụng từ [hợp đồng tư vấn, dòng 159](https://github.com/datnv41001/ai-company/blob/d95c5cd3f0e73c357c870d86774c40e31a4ac05d/app/campaign_operations_contracts.py#L159), [chuyển trạng thái CRM, dòng 82](https://github.com/datnv41001/ai-company/blob/d95c5cd3f0e73c357c870d86774c40e31a4ac05d/app/campaign_operations_crm.py#L82) và [quyền Role Desk, dòng 216](https://github.com/datnv41001/ai-company/blob/d95c5cd3f0e73c357c870d86774c40e31a4ac05d/app/campaign_role_desk.py#L216).
- R55-02 đối chiếu chữ ký nguồn form và toàn bộ số đếm theo cùng plan tại [funnel, dòng 102](https://github.com/datnv41001/ai-company/blob/d95c5cd3f0e73c357c870d86774c40e31a4ac05d/app/business_intake.py#L102). Số báo giá tăng khi Sales ghi nhận bước `quote` trong sandbox.

## Kết quả từ bản sửa d95c5cd

Nhóm kiểm tra API/native có 15 ca đạt, Chromium có một ca đạt và kiểm tra riêng cho quyền tư vấn khi thiếu consent hoặc thiếu grant có một ca đạt. [Tên từng ca, thời gian và SHA-256](consultation/runs.json)

Hai lượt chạy độc lập tạo cùng kết quả nghiệp vụ. Hai lần gửi form hợp lệ sinh hai hồ sơ. Hồ sơ đầu đủ điều kiện sau tư vấn, Sales tiếp nhận, phát hành báo giá và ghi đơn. Xác nhận 5.000 VND, hoàn 1.000 VND và hủy đơn lần lượt cho doanh thu hiện hành 5.000, 4.000 rồi 0 VND. Hồ sơ thứ hai từ chối tăng số lượng và dừng ở trạng thái từ chối. Tổng cuối kỳ có một báo giá lịch sử và một đơn lịch sử. [SQLite](consultation/sqlite.json) · [PostgreSQL với role runtime](consultation/postgres.json)

Trong Chromium, người điều phối giao hồ sơ 3 hộp bằng giao diện. Người tư vấn cập nhật 5 hộp và xác nhận bằng bàn phím. Bàn điều hành hiển thị 1 RFQ đủ điều kiện và 0 báo giá. Ba kích thước đã kiểm tra focus và reflow. Lượt cục bộ này mất 297 ms từ thao tác ghi đến khi thấy trạng thái chờ giao Sales. Thời gian chỉ phản ánh máy thử. [Kết quả trình duyệt](consultation/observations.json)

| Chiều rộng viewport | Giao diện sáng | Giao diện tối |
|---|---|---|
| 390 px | [Ảnh](consultation/sales-390-light.png) | [Ảnh](consultation/sales-390-dark.png) |
| 820 px | [Ảnh](consultation/sales-820-light.png) | [Ảnh](consultation/sales-820-dark.png) |
| 1280 px | [Ảnh](consultation/sales-1280-light.png) | [Ảnh](consultation/sales-1280-dark.png) |

## Khách rút yêu cầu trong lúc chờ giao Sales

Khi khách đổi ý sau tư vấn và RFQ đang ở “Đủ điều kiện, chờ giao Sales”, điều phối Marketing hoặc người phụ trách kinh doanh mở hồ sơ của chiến dịch, chọn **Hủy**, nhập lý do khách cung cấp và ghi nhận. Hồ sơ hiển thị “Đã hủy” cùng lý do, sổ giao dịch lưu người ghi và revision. Phiếu khách đã gửi giữ nguyên. Nếu khách muốn đặt yêu cầu khác, tiếp nhận một biểu mẫu mới theo nhu cầu và sự đồng ý mới.

RFQ đã đủ điều kiện vẫn được tính trong số từng đạt điều kiện. Việc rút trước phân công không phát sinh lượt Sales nhận, báo giá, đơn hàng hoặc doanh thu. Một tab đang mở ở revision cũ phải tải lại nếu đồng thời có người giao Sales hoặc hủy. Nhân viên vừa tư vấn và khách xem dữ liệu không có quyền ghi việc hủy ở giai đoạn này.
