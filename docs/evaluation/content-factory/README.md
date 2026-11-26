# Bàn giao Content Factory theo kế hoạch

**ENG-G02** mở bốn gói Social, Performance, Creative và Editorial trong Marketing Studio khi kế hoạch đang hoạt động có manifest chính đã được đưa vào hàng đợi. Lựa chọn manifest dùng landing nếu có, sau đó đến strategy. Mỗi chiến dịch giao một bộ trên đúng bản làm việc của run đó. [Nghiệp vụ WF-06, WF-07 và WF-08](../../PRODUCT_SPEC_V1.md)

## Luồng dùng thử và tiếp quản

1. Dùng dữ liệu tổng hợp trên local. Làm theo mục Docker ở [hướng dẫn Campaign Engine](../campaign-engine/README.md). Chuẩn bị hồ sơ, bằng chứng và brief rồi duyệt kế hoạch, chạy brief đã giao.
2. Owner hoặc admin mở bản làm việc trong **Duyệt và bàn giao → Soạn và bàn giao cho khách → Biên tập tài liệu Marketing**. Chọn **Soạn bộ nội dung theo kế hoạch**, đối chiếu kênh, phiên bản và digest, xem từng trường rồi lưu. Editor có thể sửa sau lần chuẩn bị đầu.
3. Social biên tập câu mở, trụ cột và CTA. Media đối chiếu đối tượng, từ khóa, mẫu lời quảng cáo, cách chia media thử nghiệm và đơn vị đo chuyển đổi. Design xem concept, bố cục ảnh, kịch bản video và trạng thái quyền. Campaign Manager biên tập thứ tự nội dung, đối chiếu mốc và người nhận việc. Studio dựng bản xem lời quảng cáo và đặc tả sản xuất trực tiếp từ trường đang sửa.
4. Gửi bản đã lưu cho người duyệt độc lập. Người duyệt kiểm tra bằng chứng mỗi trường và ký từng nhóm theo revision và digest. Sửa bản làm việc tạo revision mới, hủy hiệu lực chữ ký cũ. Sau khi QA duyệt toàn bộ, chủ thể có quyền chia sẻ snapshot với đúng khách. Người mua được quyền quyết định có thể duyệt snapshot trong cổng khách.
5. Nhân sự mở điều hành chiến dịch, đối chiếu bản giao với gói công việc và ghi nhận nghiệm thu sandbox. Mỗi gói dùng đúng kế hoạch, biên nhận queue, chữ ký nhóm và quyết định khách. Thử ghi nhận trùng bị chặn. Snapshot khách đã nhận vẫn đọc lại được khi bản làm việc thay đổi.

## Hai ca nghiệm thu sử dụng dữ liệu tổng hợp

| Ca | Đầu ra và căn cứ | Tình huống phản biện |
| --- | --- | --- |
| Vật liệu tiêu âm bán theo hộp cho nhà thầu | [Lời chào giá, nội dung từng kênh, QA trường và biên nhận](rfq.json) | Phải giữ điều kiện sử dụng và yêu cầu đủ thông tin để báo giá. |
| Dịch vụ kiểm tra bơm theo máy cho quản đốc | [CTA đặt lịch, cách đo lịch đã xác nhận và bộ tài sản](appointment.json) | Lịch hủy/vắng được tách riêng. Đơn yêu cầu chưa xác nhận chưa thành booking. |

Các mẫu này được xuất từ API SQLite với hai bộ đầu vào độc lập. Fixture SQLite tạo bản ghi worker hoàn thành và liên kết queue. Test PostgreSQL dùng queue, worker và publisher giới hạn quyền của dự án. Những bản ghi ký/duyệt thuộc các tài khoản fixture. Độ hiệu quả quảng cáo, quyền sử dụng tư liệu thực tế và phản hồi chuyên gia thực địa cần có phép đo hoặc người kiểm tra riêng. Creative giao concept và đặc tả ảnh/video. File media cuối cùng cần nguồn và giấy phép thực tế trước khi mở chức năng sản xuất media. Commercial GA vẫn NO-GO.

| Kích thước | Quảng cáo | Brief Creative |
| --- | --- | --- |
| Desktop 1280px | [Sáng](channels/ad-1280.png) · [Tối](channels/ad-1280-dark.png) | [Sáng](channels/creative-1280.png) · [Tối](channels/creative-1280-dark.png) |
| Tablet 820px | [Sáng](channels/ad-820.png) · [Tối](channels/ad-820-dark.png) | [Sáng](channels/creative-820.png) · [Tối](channels/creative-820-dark.png) |
| Mobile 390px | [Sáng](channels/ad-390.png) · [Tối](channels/ad-390-dark.png) | [Sáng](channels/creative-390.png) · [Tối](channels/creative-390-dark.png) |

[Chromium, kích thước vùng nhìn và thời gian điều hướng bằng bàn phím](channels/sessions.json). Phép đo gồm điều hướng bốn nhóm trong phiên local. CI lưu ảnh riêng trong browser artifact của commit.

## Nguồn nghiên cứu và phạm vi áp dụng

Ngày 26/11/2026, tài liệu chính thức Google Ads API mô tả headline và description là các thành phần riêng của responsive search ads, có thể được phối hợp và đo theo tổ hợp. AMC áp dụng nguyên tắc tách các trường và kiểm tra bản xem thử qua cùng revision. Bản đề xuất là bản biên tập và kế hoạch thử nghiệm. Khi bổ sung connector, cần kiểm chứng số lượng, chiều dài, URL và quyền cho từng định dạng. Nguồn có độ tin cậy cao đối với cấu trúc Google Ads; hiệu quả kinh doanh phụ thuộc phép thử tại thị trường mục tiêu. [Google Ads API, responsive search ads](https://developers.google.com/google-ads/api/docs/responsive-search-ads/overview)

## Hợp đồng và chạy lại

- Backend tại `app/campaign_channels.py`, `app/c3_studio_routes.py`, `app/c3_customer_assets.py`. Các nhóm dùng chung evidence, approval, lịch sử và portal. `GET .../engine/plans/{plan_id}/production` trả digest ký của bản làm việc, revision, plan digest và queue receipt cho từng tài sản. Digest nội dung trong biên nhận bàn giao phục vụ đối soát snapshot.
- `customer-marketing-assets/2` gắn digest ký với document, revision, manifest, plan, nhóm và trường. Ràng buộc CTA, điều kiện thương mại, mốc, kênh, giới hạn media và tình trạng quyền được xác minh trước ký. Phép đo và phần chia ngân sách là đề xuất, chưa có chi tiền hoặc kết quả media.
- App schema core v25; C3 module v5. Dừng writer cũ, sao lưu, chạy migration của release và khởi động writer mới. Migration khóa cùng bốn bảng và đổi hàm guard nguyên tử; phiên `c3/4` cũ bị chặn ghi. Với SQLite file, kết nối mới đăng ký hàm v5 và cài trigger trong giao dịch. Đường rollback dùng bản sao trước cutover cùng binary tương ứng theo [runbook](../../../HANDOFF.md).
- SQLite và PostgreSQL: `python -m pytest -q tests/test_channel_editions.py tests/test_edition_sqlite_cutover.py`. Chạy đúng môi trường PostgreSQL test đã được tạo theo CI để mở trường hợp restricted. Chromium: `python -m pytest -q tests/browser_channel_edition.py` sau `python -m playwright install chromium`. Đặt `AMC_STUDIO_EVIDENCE` để chọn thư mục xuất ảnh và `AMC_CHANNEL_EVIDENCE` để xuất JSON từ fixture.
