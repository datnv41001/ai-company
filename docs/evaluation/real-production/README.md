# Creative Production và Landing Production

Marketing operator dùng nội dung đã được duyệt để dựng asset, reviewer kiểm file cụ thể, người phụ trách Sales hoặc dịch vụ nhận yêu cầu thử từ landing. Các bản làm việc Marketing Studio vẫn là nơi sửa headline, giá trị, lợi ích, điều kiện, CTA và SEO. Phạm vi release này là môi trường nội bộ với fixture tổng hợp.

## Chạy và nghiệm thu trên máy khác

1. Dùng Docker Compose và tài khoản thử theo [HANDOFF](../../../HANDOFF.md). Image xây lại từ `requirements.txt` cài Pillow 13.0.0. Font Be Vietnam Pro SemiBold, giấy phép OFL và SHA nguồn nằm trong [hồ sơ nguồn](FONT-SOURCE.md).
2. Duyệt kế hoạch có brief landing thuộc hành trình RFQ hoặc appointment. Chạy brief, mở bản làm việc qua Marketing Studio, chuẩn bị bộ kênh, sửa các trường, gửi QA từng nhóm rồi QA toàn bản. Hai Studio sản xuất xuất hiện trong **Nội dung trang** và **Brief thiết kế** của bộ theo kế hoạch.
3. Với Creative, chọn màu, hình học tổng hợp và bố cục. Có thể chọn ba màu riêng theo hướng dẫn brand. Renderer kiểm tương phản chữ và CTA, giới hạn kích thước và dừng nếu chữ vượt vùng an toàn. Dựng master, mở các tỉ lệ, đối chiếu font và quyền nguồn. Tải bản mẫu dọc, ngang, vuông, nguồn, master, video và phụ đề từ **Tải file và đối chiếu SHA-256**.
4. Với Landing, dựng trang từ copy và SEO có chữ ký. Xem trên desktop/mobile, kiểm headline, giá trị, lợi ích, đầy đủ điều kiện, CTA, metadata và biểu mẫu. Khi cần sửa nội dung, sửa nhóm copy/SEO gốc trên Studio, lưu, QA rồi dựng phiên bản mới. File HTML lưu riêng có thể mở offline để xem.
5. Một owner/admin khác đối chiếu file rồi ghi nhận quyết định trên digest của package. Muốn ghi nhận lượt xem thử, chọn **Bắt đầu phiên thử** trong Landing Studio. Khách thử chọn số lượng, địa điểm giả lập và thời gian từ danh sách. API ghi session và RFQ hoặc appointment vào đúng campaign. Form sai bị chặn, lần gửi lặp dùng lại receipt. Bộ nhập này chỉ nhận enum và số; mọi trường tự do, tên, email, điện thoại đều ngoài hợp đồng.

| Ca tổng hợp | Creative master | Ảnh | Video | Trang đích và phép đo |
| --- | --- | --- | --- | --- |
| Yêu cầu báo giá vật liệu | [Master](rfq/creative/master.json), [quyền, SHA và QA](rfq/creative/receipt.json) | [Ngang](rfq/creative/landscape.png), [dọc](rfq/creative/portrait.png), [vuông](rfq/creative/square.png) | [WebM](rfq/creative/preview.webm), [VTT](rfq/creative/captions.vtt) | [HTML](rfq/landing/landing.html), [hai biên nhận sandbox](rfq/landing/sandbox-events.json) |
| Hẹn dịch vụ tại xưởng | [Master](appointment/creative/master.json), [quyền, SHA và QA](appointment/creative/receipt.json) | [Ngang](appointment/creative/landscape.png), [dọc](appointment/creative/portrait.png), [vuông](appointment/creative/square.png) | [WebM](appointment/creative/preview.webm), [VTT](appointment/creative/captions.vtt) | [HTML](appointment/landing/landing.html), [hai biên nhận sandbox](appointment/landing/sandbox-events.json) |

[Screenshots Chromium của RFQ](screens/rfq/) và [screenshots Chromium của appointment](screens/appointment/) bao gồm 1280, 820, 390 px, light/dark, trạng thái form thử ở mobile và `sessions.json`. Browser giải mã file VP8 thực tế, đọc metadata SEO, chặn số lượng sai, gửi form hợp lệ qua web và đối chiếu biên nhận hiển thị.

## Hình thành file và giới hạn

Báo cáo ghi dung lượng và thời gian từng lần dựng, việc giải mã video và phạm vi kiểm tra model ảnh local. [Nghiệm thu kỹ thuật](QUALIFICATION.md)

- Master phiên bản `amc.creative-master/1` lưu headline, CTA, brief, digest hướng dẫn brand, lựa chọn màu/bố cục, nét hình, vùng an toàn, nguồn, typeface và thời gian từng cảnh. Nguồn là hình học tự dựng bằng Pillow. Hai bố cục, ba tỉ lệ và một font đã đóng gói. Màu được người có quyền chọn và reviewer xác nhận cho package. Với tư liệu khách hàng, cần license, vùng, thời hạn và đánh giá quyền trước khi mở tính năng nhập file.
- Renderer tạo ba ảnh PNG thật. Video sáu giây là ba cảnh tĩnh với nội dung/CTA, caption và mốc hai giây. Các cảnh mã hóa VP8 intra-frame trong WebM; browser có thể phát offline, có track phụ đề VTT. Không lồng tiếng, quay phim, dựng footage thật hay gọi model sinh ảnh/video. Không thay ảnh tổng hợp bằng hình sản phẩm thực tế.
- Bộ trang `amc.sandbox-landing/1` dùng chính copy và SEO đã QA. HTML tự chứa, noindex, CSP chặn kết nối mạng và gửi form ra ngoài. Iframe cách ly chỉ chuyển ba lựa chọn tổng hợp cho trang quản trị đã xác thực. Chỉ Studio ghi sự kiện. Thông tin nguồn truy cập kênh quảng cáo chưa biết được giữ là chưa có attribution. Không suy ra doanh thu hay tỷ lệ dịch vụ hoàn thành từ lượt gửi thử.
- Package giới hạn 2 MB, kích thước xuất cố định, không nhận URL, media upload hay tài liệu khách. Dữ liệu file được giữ trong receipt bất biến cùng loại file, số byte, SHA-256, manifest, digest của kế hoạch, revision tài liệu và biên nhận từng nhóm. Tìm phiên bản chỉ đọc metadata, liệt kê tối đa 50 mục mới; file cũ truy xuất được theo ID trong cùng phạm vi quyền. File đã dựng được lưu để đọc lại ngay cả khi runtime dựng hình thay đổi.
- Sửa nội dung, thay revision, thu hồi nguồn hoặc hạ quyền người duyệt làm mất điều kiện tạo/chạy mới. QA file yêu cầu người thứ hai có quyền đang hiệu lực. Biên nhận cũ và file lịch sử giữ nguyên. Các bản ghi B/C dùng journal riêng của Knowledge; chỉ session, RFQ và appointment dùng journal sandbox hiện hành. Khi rollback dừng writer mới và dùng binary + bản sao tương thích trong runbook chính.
- Editor vẫn sửa bản nguồn trong Marketing Studio. Package sản xuất và file chỉ tải được trong Studio với quyền đọc Knowledge restricted của owner/admin. Portal khách tiếp tục hiển thị snapshot văn bản đã được chia sẻ. Chia sẻ binary cho khách cần hợp đồng riêng gắn quyền đúng người nhận, thời hạn và digest của file.
- Advertising Planner có thể gọi `approved_landing_destination(store, user, plan)` để tìm đích nội bộ. Kết quả gồm `deliverable_id`, `package_id`, `package_digest`, `studio_revision`, `file_digest` và `download_url` (file envelope có xác thực). Chỉ trả đích khi commission, phạm vi, nguồn, chữ ký Studio và QA file còn hợp lệ. Hàm chỉ truy vấn; lần thực hiện tác vụ vẫn kiểm tra lại quyền.
- `measurement.render_ms` là thời gian dựng/xác định digest trên máy phát sinh receipt. `bytes` là tổng dung lượng file. Chưa đo chi phí hoàn chỉnh, thời gian tác nghiệp của chuyên gia hay chất lượng thương mại. Commercial GA vẫn NO-GO.

## Chạy kiểm thử và tái lập bằng chứng

Chép `master.json` sang thư mục làm việc, chỉnh bố cục hoặc caption, rồi chạy `python -m app.production_creative path/to/master.json path/to/new-output`. Thư mục đích phải mới để giữ bằng chứng trước đó. Công cụ dựng PNG, video và VTT local. Các file biên tập offline cần một quyết định QA mới trước khi sử dụng. Đối chiếu đúng phiên bản Pillow, FreeType, WebP và font khi so byte với receipt từ máy khác.

`python -m pytest -q tests/test_production_studios.py` chạy bộ API. Dùng cấu hình PostgreSQL quyền giới hạn như CI để chạy ca restricted. `python -m pytest -q tests/browser_production_studios.py` sau khi cài Playwright và Chromium thực hiện hai hành trình qua trình duyệt. `AMC_PRODUCTION_EVIDENCE` chọn thư mục xuất file và JSON; `AMC_PRODUCTION_SCREENS` chọn thư mục ảnh.

Reviewer có thể thử sửa giá trị sau QA, thay master sau quyết định, nhập palette thiếu tương phản, điền số lượng sai, sử dụng người khác hoặc campaign khác để ghi nhận lượt đã mở, và gửi hai lần sau mất phản hồi. Đối chiếu digest file tải về với receipt và kiểm tra bản giao cũ còn đọc đúng byte.
