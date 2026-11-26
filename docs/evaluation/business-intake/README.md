# AMC-R51-01 · Phiếu tiếp nhận theo kế hoạch

Phạm vi là trang thử nội bộ, dữ liệu tổng hợp và hai hành trình RFQ/lịch hẹn. Người nhận yêu cầu ở Sales hoặc Service cần thấy đúng thông tin mà nội dung Marketing đã đề nghị người mua cung cấp.

## Nguồn và quyết định thiết kế

Ngày 26/11/2026, đối chiếu tài liệu chính thức của dự án JSON Schema về thuộc tính khai báo, thuộc tính bắt buộc và giới hạn thuộc tính bổ sung. Áp dụng những nguyên tắc này vào schema nội bộ bằng Pydantic và bộ kiểm tra phía máy chủ. Tài liệu nguồn chỉ mô tả phương pháp xác thực đầu vào. Nghĩa của từng trường và điều kiện thương mại đến từ brief và fact đã duyệt của AMC. [Understanding JSON Schema · Object](https://json-schema.org/understanding-json-schema/reference/object)

Hai brief nghiên cứu tổng hợp nằm trong `tests/evaluation/department/briefs-v1.json`. Ca kiểm tra bơm nằm trong `tests/campaign_planner_fixtures.py`. Đây là bằng chứng kỹ thuật trong sandbox. Mức độ chấp nhận của khách hàng, hiệu quả kinh doanh và chi phí lao động đều chưa đo.

| Hành trình | Dữ liệu được yêu cầu | Quyết định nghiệp vụ |
| --- | --- | --- |
| Khe Gọn | Số hộp nguyên, địa bàn, ngày cần hàng | Nhận liên hệ dưới MOQ. Marketing có thể giao một nhân viên Sales tư vấn khi khách đã đồng ý. Sau khi cập nhật số lượng, hệ thống kiểm tra lại MOQ. Đủ điều kiện thì điều phối phân công xử lý báo giá. [Quyền, chỉ số và rollback](CONSULTATION.md) |
| Luồng Rõ | Địa điểm, ca nhận hàng cần quan sát | Chuyển cả hai lựa chọn đến Service. Thời gian được xác nhận ở quyết định đặt lịch riêng. Số lượng và ngày hẹn để trống nếu brief chưa yêu cầu. |
| Kiểm tra bơm | Số máy, địa điểm, thời gian dự kiến | Gắn đơn vị `machine` với lựa chọn. Giữ nguyên phần giá, thuế, MOQ và phạm vi trong các nhóm nội dung đã ký. |

## Luồng dữ liệu và quyền

1. API tạo đề xuất từ các manifest hợp lệ. `app/business_intake.py` chỉ nhận danh mục trường có kiểu, nhãn theo locale, quy tắc bắt buộc, enum hoặc giới hạn số, đơn vị và đích ánh xạ. Yêu cầu có tên trường đã biết trong brief được đọc theo danh sách đóng. Nếu brief không chỉ định danh sách hỗ trợ, UI hiển thị lựa chọn mặc định theo hành trình để người phụ trách duyệt. Không đưa chỉ dẫn tự do từ brief ra HTML.
2. Trên API đề xuất kế hoạch, `intake_fields` có dạng `[{"id":"site","required":true},{"id":"receiving_shift","required":true},{"id":"preferred_time","required":false}]`. Phải duy trì những trường bắt buộc từ brief. Kết quả đề xuất và màn hình duyệt cho biết danh mục, đơn vị, mục đích, revision và digest. Sửa cấu trúc cần đề xuất và duyệt revision mới.
3. Digest của kế hoạch bao gồm toàn bộ hợp đồng, manifest đã chọn, sản phẩm, revision và digest KPI nếu có. Gói HTML nhận hợp đồng này, qua bước ký độc lập theo digest gói và giữ nguyên bytes đã lưu. Các trường và điều kiện áp dụng không quyết định quyền của người gọi. API tiếp tục kiểm tra tenant, client, brand, campaign, người dùng, tài liệu, QA revision, digest và quyền reviewer trước khi ghi.
4. Iframe có origin riêng và chỉ gửi lựa chọn qua bridge tới cha đã xác thực. API yêu cầu visit đúng gói, digest đúng revision, consent theo mục đích và đúng kiểu dữ liệu. Sử dụng lại cùng request ID và cùng payload trả biên nhận cũ. Yêu cầu khác payload bị từ chối. Consent này chỉ áp dụng cho yêu cầu tổng hợp đang gửi.
5. CRM lưu câu trả lời, trường, ánh xạ, consent và nguồn gói đã ký cùng biên nhận. Role desk hiển thị theo quyền chiến dịch hiện hữu. API sandbox trả `intake_measurement` cho scope và plan được chọn, bao gồm số lượt mở trang đúng contract, hồ sơ hợp lệ, yêu cầu thủ công tách riêng, yêu cầu báo giá đủ điều kiện hoặc lịch đã xác nhận. Cửa sổ của số đếm này là vòng đời plan. `report.primary_measurement` tiếp tục tính KPI lịch hẹn theo đúng cửa sổ được duyệt. Số yêu cầu hợp lệ, số đủ MOQ và số đơn hàng được ghi riêng.

Đọc chỉ số theo nguồn và cửa sổ. Một liên hệ thủ công hợp quyền vẫn xuất hiện ở báo cáo CRM và có thể đóng góp vào cohort lịch hẹn theo định nghĩa KPI đã duyệt. Liên hệ đó không tăng lượt gửi form trong `intake_measurement`. Trường tùy chọn bỏ trống vẫn có thể tạo yêu cầu hợp lệ và được giao tư vấn khi khách đồng ý. Phân công xử lý báo giá và giao dịch còn phụ thuộc đủ thông tin cùng điều kiện thương mại. Nếu có nhiều mức MOQ chưa xác định được điều kiện áp dụng, hồ sơ chờ đối chiếu và chưa được chuyển bước. KPI theo tháng hoặc theo một cửa sổ khác cần có định nghĩa và dữ liệu phù hợp riêng. Hai bộ nhãn và từ vựng được hỗ trợ là tiếng Việt và tiếng Anh. Một field nghiệp vụ ngoài danh mục hoặc ngôn ngữ khác cần bổ sung hợp đồng cùng ca nghiệm thu trước khi tiếp nhận.

Bộ đọc danh sách chỉ nhận cú pháp CTA đã nêu trong test. Chẳng hạn, “Đặt lịch khảo sát, ghi địa điểm và mã dây chuyền” yêu cầu một field ngoài danh mục. Publisher của kế hoạch báo lỗi để cập nhật brief. Nội dung ghi chú chung cho biên tập vẫn dùng được và không tự tạo trường nhập liệu. Với cách diễn đạt tự do chưa được nhận diện, người phụ trách cần kiểm tra rõ danh mục hiển thị trước bước duyệt. Các bản copy đã duyệt từ phiên bản cũ dùng lại quy tắc đọc lịch sử.

## Chuyển phiên bản giữa các máy

Chạy migration publisher `python migrations/apply.py` với cấu hình phát triển của repository trước khi chạy API mới. Core vẫn ở v26. Publisher kiểm tra và cài trigger `business_intake_writer` theo cùng quy trình additive của campaign desk. Khởi động cụm API với `docker compose up --build` theo hướng dẫn README của repository. Với SQLite file, khởi động ứng dụng mới trên file hiện hữu để cài trigger. Giữ bản sao dữ liệu theo quy trình restore đã có.

Trigger kiểm tra hợp đồng của gói trang theo proposal cùng scope và kiểm tra giao thức của phiên/lịch/lead thuộc plan có contract. Khi hai phiên bản API cùng chạy, bản cũ vẫn có thể phục vụ plan v1. Một writer cũ tạo gói v1 cho plan đã có contract hoặc ghi sự kiện theo giao thức cũ lên plan đó sẽ bị database từ chối. Cập nhật tiến trình đó và thử lại với gói hiện hành. Các bản duyệt, file giao khách và lịch sử ghi trước nâng cấp tiếp tục đọc từ bản lưu bất biến. Không cần backfill nội dung.

## Bằng chứng cục bộ đã đối chiếu

Source ứng dụng `5097ef607d44a0a573ba48985437c63fba135441`. Test harness ghi thêm witness ở commit bằng chứng. Có 3/3 ca API SQLite xuất file và receipt, 3/3 ca Chromium hoàn tất ở 1280/820/390, cùng 8/8 ca trong lượt PostgreSQL và contract unit (3 tích hợp PG, 5 kiểm tra contract). Hai ca RED trên #54 dừng đúng tại contract còn thiếu. Mỗi ảnh dưới đây là vùng form đã mở trong Studio. API xuất bằng chứng và trình duyệt chạy hai lần dựng fixture độc lập, nên plan digest giữa hai lượt khác nhau. [Danh mục ca, browser, SHA và thời gian](evidence/verification.json)

| Ca | File và biên nhận API | Ảnh form Chromium |
| --- | --- | --- |
| Khe Gọn | [Trang](evidence/index-tray/landing.html), [receipt](evidence/index-tray/receipts.json) | [1280](evidence/index-tray/intake-1280.png), [820](evidence/index-tray/intake-820.png), [390](evidence/index-tray/intake-390.png) |
| Luồng Rõ | [Trang](evidence/receipt-map/landing.html), [receipt](evidence/receipt-map/receipts.json) | [1280](evidence/receipt-map/intake-1280.png), [820](evidence/receipt-map/intake-820.png), [390](evidence/receipt-map/intake-390.png) |
| Kiểm tra bơm | [Trang](evidence/pump-service/landing.html), [receipt](evidence/pump-service/receipts.json) | [1280](evidence/pump-service/intake-1280.png), [820](evidence/pump-service/intake-820.png), [390](evidence/pump-service/intake-390.png) |

## Tái chạy nghiệm thu

- `python -m pytest -q tests/test_content_pack_outputs.py tests/test_production_studios.py tests/test_service_landing_edit.py` chạy các ca SQLite và các ca PG khi bật môi trường PostgreSQL của CI.
- Cấu hình PG theo job API/PostgreSQL trong `.github/workflows/ci.yml` rồi chạy `python -m pytest -q tests/test_production_studios.py -k "restricted_production or predecessor_can"`. Cần lịch sử Git có commit #54 `eff86cda2f99dd10244dc8127451e941bb546a3c`. Harness mở TestClient của source cũ trong tiến trình Python riêng, dùng tài khoản và database test cục bộ của ca. Nó thực hiện API thật của bản trước.
- `python -m pytest -q tests/browser_production_studios.py -k "index-tray or receipt-map"` nghiệm thu Chromium. Dùng `AMC_PRODUCTION_SCREENS` để chọn thư mục ảnh desktop/tablet/mobile. Dùng `AMC_PRODUCTION_EVIDENCE` để xuất package, HTML và sự kiện tổng hợp. Chạy từng case vào thư mục riêng khi cần giữ các gói cùng loại hành trình.
- Đặt `AMC_INTAKE_EVIDENCE` rồi chạy `python -m pytest -q tests/test_production_studios.py -k "index-tray or receipt-map or pump-service"` để xuất hợp đồng, phiếu, điều kiện thương mại, trường trong copy, đối soát role desk và số đo cùng một plan cho từng case. Mỗi thư mục có cả HTML thực tế và SHA-256 từ production package.
- Để đối chiếu RED của hai bộ copy, dùng bản #54 và thêm hai assertion trong `test_department_pack_for_approved_study_case` truy cập `plan["intake_contract"]` và `pack["intake_contract_digest"]`. Hai ca trước thay đổi dừng ở `KeyError: intake_contract`. Kết quả thực thi sau sửa cần gắn với bản checkout hoặc CI SHA cụ thể.

Giới hạn hiện tại gồm các lựa chọn tổng hợp và ô số nguyên trong khoảng được công bố trên form. Không thu dữ liệu liên hệ thật, không tự cấp quyền mở chiến dịch và không phát sinh lệnh thanh toán. Nghiệm thu thương mại vẫn NO-GO.
