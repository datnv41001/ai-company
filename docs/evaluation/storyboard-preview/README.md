# Dựng thử video từ storyboard WF-08

Gói này dành cho người dựng muốn xem chữ và nhịp cảnh trên điện thoại trước khi quay. Mở `preview.webm` bằng trình duyệt hỗ trợ VP8 hoặc trình phát cục bộ. Video dọc 9:16, im tiếng, có phụ đề ghi trực tiếp lên hình. Track `captions.vtt` giữ nguyên văn bản và timecode của role để dùng trong phần mềm dựng. File `decoded-shots.png` là ảnh trích từ video đã mã hóa.

| Brief và cách đọc | Video từ bản QA | Ảnh trích theo timecode | Đầu ra và quyết định QA |
| --- | --- | --- | --- |
| Khe Gọn · xem thao tác, giá một hộp và lượng mua tối thiểu | [Mở video](index-tray/preview.webm) | [Các cảnh](index-tray/decoded-shots.png) | [Bản gốc](../wf08-storyboard/index-tray/raw.json) · [Sau biên tập](../wf08-storyboard/index-tray/reviewed.json) · [Biên nhận](../wf08-storyboard/index-tray/receipt.json) |
| Luồng Rõ · xem sản phẩm bàn giao và CTA gửi đề nghị | [Mở video](receipt-map/preview.webm) | [Các cảnh](receipt-map/decoded-shots.png) | [Bản gốc](../wf08-storyboard/receipt-map/raw.json) · [Sau biên tập](../wf08-storyboard/receipt-map/reviewed.json) · [Biên nhận](../wf08-storyboard/receipt-map/receipt.json) |
| Phách Mở · brief mới về học nhạc của người lớn, giá chưa duyệt | [Mở video](rhythm-class/preview.webm) | [Các cảnh](rhythm-class/decoded-shots.png) | [Bản gốc](../wf08-storyboard/rhythm-class/raw.json) · [Sau biên tập](../wf08-storyboard/rhythm-class/reviewed.json) · [Biên nhận](../wf08-storyboard/rhythm-class/receipt.json) |

Renderer lấy tên brand, sản phẩm, quyền, thời lượng, chế độ minh họa, caption và CTA từ đúng đầu ra WF-08. Người dựng chọn một hướng minh họa hình học cho từng brief. Chuyển động là các keyframe một giây phù hợp cho animatic đọc khi tắt âm. Chưa có voice-over, ảnh thật hoặc nhạc thương mại. [Lý do chọn concept và cách phân biệt thử nghiệm một biến](CREATIVE-DIRECTIONS.md)

## Kết quả đọc hình

Chromium 158.0.8127.88 đã giải mã đủ 32 giây cho từng video. Người đọc kỹ thuật AI xem các khung trích ở cả 14 điểm đầu cảnh. Lượt đầu cho thấy câu claim và điều kiện bị dính nhau khi đọc thành tiếng. Riêng Luồng Rõ còn mang câu xác nhận số lượng vốn dùng cho hàng hóa. Hai điểm được trả về nguồn: bộ tạo storyboard phân cách câu với qualifier, còn brief dịch vụ ghim điều kiện người phụ trách xác nhận lịch sau khi nhận đề nghị. Ba video phía trên được dựng lại bằng **revision 2 đã QA của ba run mới**. Phụ đề, khung trích và video đều có digest; kiểm thử đối chiếu `reviewed.json` với chính biên nhận dựng.

Ở lần đọc cuối, Khe Gọn ghi giá tham khảo 380.000 VND/hộp, đã gồm thuế và MOQ 5 hộp. Luồng Rõ tách 760.000 VND/lượt khỏi việc xác nhận lịch, rồi kết bằng “Gửi đề nghị khảo sát”. Phách Mở hiển thị “Chưa có giá được duyệt.” và kết bằng “Chọn buổi”. Hook dựa vào tên nhóm người xem còn chung, bố cục thẻ chữ chiếm phần lớn hình. Người dựng cần xác nhận cách mở đầu và nhịp đọc trên thiết bị thật trước khi đầu tư quay; chưa có phép đo hiệu quả với khách hàng.

## Chạy trên máy khác

Từ gốc checkout có môi trường dev của AMC, dùng đường dẫn tới bản JSON đã lấy từ lượt chạy. Mỗi lần dựng ghi vào thư mục mới.

```sh
python -m scripts.render_storyboard_preview path/to/reviewed.json out/preview --style route
python tests/evaluation/department/decode_storyboard_preview.py out/preview
python -m pytest -q tests/test_storyboard_preview.py
```

Chọn `parts` cho thao tác linh kiện, `route` cho sơ đồ bàn giao hoặc `rhythm` cho ví dụ nhịp. Người biên tập chọn ngôn ngữ hình dựa vào brief và quyền hình; các lựa chọn này được ghi trong `render.json`. Lệnh kiểm giải mã dùng Playwright với Chromium của môi trường kiểm thử browser AMC. Có thể thêm `--chromium <đường-dẫn-executable>` để dùng Chrome cài sẵn. Renderer dùng font Be Vietnam Pro đã đóng gói và bộ mã hóa VP8/WebM của Creative Studio. Toàn bộ xử lý diễn ra tại máy.

**Kiểm bản giao.** So SHA-256 của file JSON với `source_sha256` trong `render.json`, và SHA-256 của video với `video_sha256` trong `decoder.json`. Đọc phụ đề khi tắt âm, đối chiếu đơn vị, phạm vi, CTA và hành động sau submit với nguồn được duyệt. Bản dọc dùng vùng chữ x=42–453, y=105–734 trên khung 540×960. Renderer đo từng glyph và trả lỗi khi copy tràn vùng; trình giải mã kiểm kích thước, thời lượng, tất cả điểm cắt và vùng viền. Vùng đệm là preset nội bộ để tránh che chữ. Từng placement thật cần xem lại tại thời điểm phân phối.

Phí model/media của việc dựng preview bằng 0. Công biên tập, độ dễ sử dụng đối với người hành nghề, quyền phát hành ngoài và hiệu quả quảng cáo chưa đo. Quay lui bằng cách mở đúng revision cũ cùng receipt, rồi dựng mọi thay đổi vào thư mục mới.
