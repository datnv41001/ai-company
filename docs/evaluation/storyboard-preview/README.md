# Dựng thử video từ storyboard WF-08

Gói này dành cho người dựng muốn xem chữ và nhịp cảnh trên điện thoại trước khi quay. Mở `preview.webm` bằng trình duyệt hỗ trợ VP8 hoặc trình phát cục bộ. Video dọc 9:16, im tiếng, có phụ đề ghi trực tiếp lên hình. Track `captions.vtt` giữ nguyên văn bản và timecode của role để dùng trong phần mềm dựng. File `decoded-shots.png` là ảnh trích từ video đã mã hóa.

| Brief và cách đọc | Video từ bản QA | Ảnh trích theo timecode | Đầu ra và quyết định QA |
| --- | --- | --- | --- |
| Khe Gọn · xem thao tác, giá một hộp và lượng mua tối thiểu | [Mở video](index-tray/preview.webm) | [Các cảnh](index-tray/decoded-shots.png) | [Bản gốc](../wf08-storyboard/index-tray/raw.json) · [Sau biên tập](../wf08-storyboard/index-tray/reviewed.json) · [Biên nhận](../wf08-storyboard/index-tray/receipt.json) |
| Luồng Rõ · xem sản phẩm bàn giao và CTA gửi đề nghị | [Mở video](receipt-map/preview.webm) | [Các cảnh](receipt-map/decoded-shots.png) | [Bản gốc](../wf08-storyboard/receipt-map/raw.json) · [Sau biên tập](../wf08-storyboard/receipt-map/reviewed.json) · [Biên nhận](../wf08-storyboard/receipt-map/receipt.json) |
| Phách Mở · brief mới về học nhạc của người lớn, giá chưa duyệt | [Mở video](rhythm-class/preview.webm) | [Các cảnh](rhythm-class/decoded-shots.png) | [Bản gốc](../wf08-storyboard/rhythm-class/raw.json) · [Sau biên tập](../wf08-storyboard/rhythm-class/reviewed.json) · [Biên nhận](../wf08-storyboard/rhythm-class/receipt.json) |

Renderer lấy tên brand, sản phẩm, quyền, thời lượng, chế độ minh họa, caption và CTA từ đúng đầu ra WF-08. Người dựng chọn một hướng minh họa hình học cho từng brief. Chuyển động là các keyframe một giây phù hợp cho animatic đọc khi tắt âm. Chưa có voice-over, ảnh thật hoặc nhạc thương mại. [Lý do chọn concept và cách phân biệt thử nghiệm một biến](CREATIVE-DIRECTIONS.md)

## Kết quả đọc hình

Chromium 158.0.8127.88 giải mã hai bản 32 giây và bản giáo dục 18 giây. Người đọc kỹ thuật AI xem đủ 13 điểm đầu cảnh và kiểm thêm chuyển động trong cảnh. Biên nhận giải mã so riêng các pixel vùng hình đầu và cuối cảnh nhấc vách, nhấn phách và chọn buổi. Mỗi video đi từ revision 2 đã QA; phụ đề và video kiểm được bằng digest của bản xuất.

Lượt đọc đầu phát hiện thiếu dấu câu giữa claim và điều kiện, và một điều kiện về số lượng hàng xuất hiện trong brief dịch vụ. Đã sửa tại bộ tạo storyboard và nguồn điều kiện dịch vụ. Ở lượt phản biện sau, người đọc vẫn chưa thấy thao tác cụ thể trong hình và gặp một ghi chú giá nội bộ trên video âm nhạc. Bản dựng cập nhật thể hiện:

- **Khe Gọn.** So song song cùng một khay trước và sau khi nhấc vách khỏi đế. Renderer chỉ chọn hình này khi cảnh trỏ đúng fact tháo vách và điều kiện mẫu tiêu chuẩn. Chữ hiển thị giá tham khảo 380.000 VND/hộp, gồm thuế, MOQ 5 hộp.
- **Luồng Rõ.** Phóng tờ sơ đồ bàn giao ở cảnh chứng minh. Sau offer 760.000 VND/lượt, cảnh điều kiện chuyển từ phong bì tới người nhận “Chờ xác nhận”, rồi mới đến CTA gửi đề nghị. Hình này yêu cầu điều kiện lịch nằm trong khai báo đã duyệt.
- **Phách Mở.** Hai dấu mạnh/nhẹ có chú giải và đổi nhấn. Đây là ví dụ minh họa do AMC tự vẽ. Cảnh cuối có thẻ lựa chọn buổi học. Trạng thái giá chưa duyệt nằm trong ghi chú biên tập riêng của storyboard; video chỉ giữ ba cảnh hook, nội dung và chọn buổi.

Tính hữu ích khi người dựng cầm brief mới và khả năng người mua hiểu CTA vẫn cần người hành nghề nghiệm thu. Hiện sơ đồ và các điều kiện chuyên biệt chỉ phủ một số ý nghĩa đã kiểm. Một thương hiệu mới cần có quyền hình, claim và điều kiện đúng ngữ cảnh để bổ sung hướng dựng.

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
