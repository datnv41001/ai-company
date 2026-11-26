# AMC-R57-01 · Khôi phục RFQ vật liệu bán theo mét vuông

Điều phối viên cần ghi đúng diện tích và điều kiện sử dụng, giao nhận mà khách cung cấp cho Sales. Trên `main` sau #56, Git lưu đơn vị ở dòng 11 của `app/campaign_operations_crm.py` dưới dạng UTF-8 `6d c2 b2`. Trên head được review `73c1c04e7db6501979696c63b72d948171d957cb`, blob có `6d c3 82 c2 b2`. Cả hai blob vẫn giải mã UTF-8 thành công. `RFQ.unit` dùng kiểu `Unit` của Knowledge, còn `CompleteRFQ` dùng đơn vị trên journal. Cả hai đi qua cùng bước kiểm phạm vi chi tiết thương mại.

## Tái hiện trên bản được review

Test tạo campaign, sản phẩm có đơn vị được duyệt, manifest, kế hoạch và phê duyệt qua API. Ca trực tiếp gửi RFQ `12.375 m²` cùng `application` và `delivery_access`. Ca còn lại mở RFQ thiếu thông tin rồi gửi `complete_rfq` với revision 1 và cùng dữ liệu thương mại. Hai lệnh được thực thi trước khi so kết quả để một lỗi không che mất lỗi còn lại.

Trên SQLite cả hai lệnh trả HTTP 409 với lý do “The selected commercial detail contract does not apply to this selling unit”. Ca kiểm tập đơn vị cũng thất bại. Hai đối chứng thập phân tonne và kg đạt. Môi trường Windows trong lần thiết lập đầu không đọc được bản Pillow cũ. Người vận hành dùng bản Pillow cùng phiên bản đã có quyền đọc và chạy lại trước khi sửa source. [JUnit của lượt RED và GREEN](R57-MATERIAL-UNITS.zip)

Để tái hiện, tạo checkout tạm của head cũ, chép nguyên [file test](../../../tests/test_rfq_material_units.py) từ nhánh sửa vào `tests/`, cài dependency theo README rồi chạy từ gốc checkout:

```sh
python -m pytest -q tests/test_rfq_material_units.py -k 'knowledge_contract or (375 and sqlite)'
```

## Đối chiếu sau sửa

Trên Windows, Python 3.12 và PostgreSQL loopback với tài khoản ứng dụng hạn chế, cả 11/11 ca đạt trong 75,01 giây, gồm một kiểm tra tập đơn vị, năm giao dịch SQLite và năm giao dịch PostgreSQL. Kiểm tra Ruff trên app, tests, scripts và migrations đạt. Quét lại diff sau sửa theo cùng tiêu chí không phát hiện dòng text thêm nào khớp các mẫu hỏng đã xét.

Chỉ sửa một literal trong nhóm đơn vị vật liệu. Hai fingerprint runtime mới mang nguyên các adapter đã duyệt của fingerprint Windows/Linux tương ứng. Các fingerprint lịch sử vẫn có thể đọc. Schema lõi v26 và journal ops/2 giữ hợp đồng cũ. Đơn vị hỏng đã bị API từ chối trước khi lưu, nên người dùng có thể gửi lại yêu cầu bị từ chối với đơn vị được duyệt.

Chạy `python -m pytest -q tests/test_rfq_material_units.py` ở gốc repo. Có một ca kiểm hợp đồng và năm đơn vị trên mỗi backend. Ca `piece` và `box` kiểm tra cả từ chối số lượng lẻ. Ca `m²`, `tonne` và `kg` giữ đủ ba chữ số thập phân. Mỗi ca cần hai HTTP 200, một RFQ mới ở revision 1 và một RFQ bổ sung ở revision 2. Đọc lại journal phải khớp số lượng, đơn vị, consent, địa bàn, ngày cần hàng và cả hai chi tiết thương mại. Đơn vị giải mã sai phải trả HTTP 422 và không tạo thêm hồ sơ. Chạy bằng profile PostgreSQL test của repo để thực hiện cả hai backend. [Thiết lập dev và PostgreSQL](../../../HANDOFF.md)

Rà soát toàn bộ phần dòng thêm bằng `git diff --unified=0` giữa main `bbb0b9c4` và reviewed head. 6.027 dòng trong 44 file text được giải mã UTF-8 strict rồi kiểm ký tự thay thế, dấu hiệu hỏng Latin-1/Windows-1252 quanh dấu mũ và ký tự tiếng Việt. Phát hiện duy nhất là dòng 11 của nhóm vật liệu. Đã đối chiếu thêm mã nhóm vật liệu trên UI và kiểu `Unit` của Knowledge. Cách rà theo mẫu chỉ phát hiện các dạng đã xét. [Bộ test hồi quy](../../../tests/test_rfq_material_units.py) · [Kiểu dữ liệu](../../../app/knowledge_contracts.py) · [Tạo và bổ sung RFQ](../../../app/campaign_operations_crm.py)

Phạm vi nghiệm thu là giao dịch tổng hợp qua API. Chi phí vận hành và tỉ lệ doanh nghiệp chấp nhận RFQ theo diện tích chưa đo. Nếu cần quay lui bản phát hành nội bộ, giữ journal và dùng bản có byte đơn vị hợp lệ cùng runtime lock tương ứng. Người phản biện có thể đối chiếu revision trước và sau khi bổ sung và kiểm số lượng hồ sơ sau lần gửi đơn vị sai.
