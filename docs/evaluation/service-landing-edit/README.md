# Biên tập trang đặt lịch kiểm tra bơm Lam

Trong trang đã bàn giao, “Phiếu kiểm tra ghi tình trạng máy.” xuất hiện ở cả phần quyền lợi và điều kiện. Bản biên tập giữ câu này ở quyền lợi. Phần điều kiện bắt đầu bằng “Áp dụng cho máy tại xưởng.”, tiếp theo là giá tham khảo 270.000 VND/máy đã gồm thuế, mức tối thiểu một máy và điều kiện xác nhận số lượng. Người phụ trách dịch vụ có thể kiểm lại bản công bố và thử chọn lịch trong Studio. [HTML trước](before.html) · [HTML sau](after.html) · [Biên nhận API](receipts.json)

## Bàn giao nghiệp vụ và kỹ thuật

| Mục | Thông tin tiếp quản |
| --- | --- |
| 1. Người sử dụng | Biên tập viên Marketing sửa câu lặp. Người QA có chuyên môn đối chiếu điều kiện với nguồn. Bộ phận dịch vụ dùng trang để thử tiếp nhận yêu cầu đặt lịch. |
| 2. Nền | Nhánh cha của thay đổi là `feature/evidence-bound-content-and-media` tại `95aed621381c782114b18521d2b2d58eb17a7828`. Ca sử dụng brief và nguồn tổng hợp của xưởng bơm Lam. |
| 3. Vấn đề tái hiện | Khi bỏ câu mô tả khỏi điều kiện, QA cấu trúc cũ ghi `missing_declaration` dù nguyên câu mô tả và giới hạn đã có tại quyền lợi. |
| 4. Thay đổi nghiệp vụ | Với landing đặt lịch, mô tả đã duyệt được giữ nguyên vẹn tại trường quyền lợi. Phần điều kiện được phép giữ riêng trọn dòng giới hạn của mô tả. Biên tập viên chủ động chọn thay đổi trên bản đang làm. |
| 5. Ràng buộc | Kiểm tra đúng loại mô tả, hành động đặt lịch, nguyên văn quyền lợi và toàn bộ qualifier. Các dòng giá, thuế, đơn vị, số lượng, khả dụng, thanh toán và bảo hành tiếp tục được kiểm nguyên khối. Dữ liệu thử có thêm ca bỏ từng giới hạn SKU, khu vực và tại xưởng. |
| 6. Cách thao tác | Vào **Marketing Studio → Nội dung trang**, chỉnh **Điều kiện thương mại**, lưu và gửi QA. Reviewer có qualification phù hợp mở hai đoạn đang chờ, đối chiếu với cùng nguồn của dịch vụ và xác nhận đúng bản trước khi ký các nhóm và toàn tài liệu. |
| 7. Giao cho sản xuất | Mở **Landing Studio**, dựng HTML từ digest kế hoạch và digest các nhóm copy/SEO vừa ký. Người thứ hai kiểm file và duyệt đúng digest của package. |
| 8. Phiên bản và quyền | Lần thử dùng hai tài khoản nhân sự tổng hợp độc lập ở khâu dựng và QA file. Studio revision 2 và 3 tạo package v1 và v2. QA của revision trước bị từ chối trên bản sửa. Dựng trước khi tái QA và tự duyệt file cũng bị từ chối. |
| 9. Chất lượng quan sát | Số lần xuất hiện câu phiếu kiểm tra giảm từ hai xuống một. So byte toàn trang xác nhận phần sửa duy nhất là câu mô tả trong khối điều kiện. Hai bản có cùng CTA, SEO, mã biểu mẫu và script. |
| 10. Form và tiếp nhận | Cả hai package đã duyệt ghi được một session và một yêu cầu appointment tổng hợp với một máy, cơ sở A và thời gian một tuần. JSON lưu ID biên nhận của từng bản. Các lượt thử chỉ đo khả năng tạo yêu cầu. |
| 11. Lịch sử | File v1 của lần tái lập khớp SHA-256 của [file đã bàn giao](../real-production/appointment/landing/receipt.json). Sau khi duyệt v2, API vẫn trả đúng byte v1 và portal trả nguyên văn cùng digest của snapshot cũ. UUID của lần tái lập thuộc tenant tổng hợp mới. |
| 12. Nhận diện build | Schema core 26, module Business v3, C3 v5. Hai fingerprint cho CPython 3.12.14 và 3.12.16 giữ cùng danh sách 11 adapter đã được khóa trên nền. Kiểm tra trạng thái bằng lệnh bên dưới trước khi chạy API và worker. |
| 13. Phục hồi | Hai package lưu file theo ID. Khi cần đối chiếu, mở lại v1 theo ID trong hồ sơ. Nếu quay lại build nền, dừng writer, giữ DB và bundle evidence sau sửa, dùng API và worker cùng build rồi kiểm snapshot lịch sử. Biên tập theo quy tắc cũ cần phục hồi nguyên văn cả dòng khai báo trong một revision mới và QA lại trước khi tạo giao dịch tiếp. |
| 14. Giá trị và giới hạn | Đây là một ca kỹ thuật trên nguồn tổng hợp. Chưa đo phút biên tập, thời gian QA, giá vốn trên đơn vị được chấp nhận hoặc tỷ lệ người làm nghề chấp nhận. Số người thực hành tham gia bằng 0. Chi phí đầy đủ trong receipt để trống. |
| 15. Phép thử kế tiếp | Giao hai bản được xáo thứ tự cho nhân sự dịch vụ và Marketing có chuyên môn. Yêu cầu họ tìm phạm vi, giá, người nhận yêu cầu và gửi thử form. Thu số lần trả về, phút chỉnh/duyệt và quyết định dùng bản nào trước khi kết luận về hiệu quả thương mại. |

## Chạy lại trên máy khác

Cài phụ thuộc phát triển của repo. Chạy trong môi trường kiểm thử đã cấu hình theo HANDOFF và CI. Để ghi bằng chứng từ lần chạy mới, đặt `AMC_SERVICE_EDIT_EVIDENCE` thành thư mục riêng. File HTML, SHA-256 và nội dung biên tập tái lập được. ID sự kiện, digest package và thời gian render phụ thuộc phiên chạy.

```sh
python -m pip install -r requirements-dev.txt
python -c "from migrations.runtime_bundle import reviewed_runtime,runtime_fingerprint; print(runtime_fingerprint(), reviewed_runtime())"
python -m pytest -q tests/test_service_landing_edit.py tests/test_c3_content_gate.py tests/test_production_evidence_bundle.py tests/test_adapter_fingerprint.py
python -m playwright install chromium
python -m pytest -q tests/browser_service_landing_edit.py
```

Ca replay sử dụng SQLite với liên kết worker tổng hợp và các API xác thực cho thao tác sửa, QA, chia sẻ, dựng, tải file và tạo lịch. Bộ `tests/test_production_studios.py` chạy thêm các ca PostgreSQL quyền giới hạn theo cấu hình CI. Ca Chromium mở hai file đã lưu ở 390, 820 và 1280 px, thử số lượng 0 và 1, kiểm CTA, số lượng, cơ sở, lịch và hành vi khi mở offline. Đặt `AMC_SERVICE_EDIT_SCREENS` để lưu ảnh. [Ảnh Chromium](screens/)

**Thử thách dành cho reviewer.** Bỏ riêng điều kiện tại xưởng hoặc dòng thuế, thay một qualifier trong quyền lợi, rồi thử ký hoặc dựng lại bằng revision cũ. Tải file theo ID cũ và đối chiếu digest với biên nhận trước khi xác nhận. [Ca nghiệm thu](../../../tests/test_service_landing_edit.py)
