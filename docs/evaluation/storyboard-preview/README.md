# Dựng thử video từ storyboard WF-08

Gói này dành cho người dựng muốn xem chữ và nhịp cảnh trên điện thoại trước khi quay. Mở `preview.webm` bằng trình duyệt hỗ trợ VP8 hoặc trình phát cục bộ. Video dọc 9:16, im tiếng, có phụ đề ghi trực tiếp lên hình. Track `captions.vtt` giữ nguyên văn bản và timecode của role để dùng trong phần mềm dựng. File `decoded-shots.png` là ảnh trích từ video đã mã hóa.

Renderer lấy tên brand, sản phẩm, quyền, thời lượng, chế độ minh họa, caption và CTA từ đúng đầu ra WF-08. Người dựng chọn một hướng minh họa hình học cho từng brief. Chuyển động là các keyframe một giây phù hợp cho animatic đọc khi tắt âm. Chưa có voice-over, ảnh thật hoặc nhạc thương mại. [Lý do chọn concept và cách phân biệt thử nghiệm một biến](CREATIVE-DIRECTIONS.md)

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
