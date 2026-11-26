# Biên tập storyboard và thiết kế thử một hook

Người làm Marketing dùng `POST /api/tenants/{tenant_id}/workforce/runs/{run_id}/storyboard-edition` trên bản WF-08 đang có. Lấy `expected_qa_revision` và `expected_content_digest` từ tài liệu đã tải. Mỗi lần lưu thành công tạo revision mới. Khi gặp HTTP 412, tải lại bản hiện hành trước khi chỉnh. Endpoint sửa nháp tổng quát hướng người dùng về trình sửa này để các quyết định, dữ kiện và phạm vi thương hiệu được kiểm tra cùng nhau.

## Sửa bản giao người dựng

Đường sửa mặc định dùng `mode: "editorial"`. Client cũ tiếp tục gửi riêng `hook_variant`. Có thể chọn câu mở trực tiếp, theo người xem, câu hỏi gắn tên sản phẩm, hoặc câu hỏi quan sát. Với WF-08/2, `style_alternate` chọn một câu khác trong chính phong cách đã ký. Hệ thống đối chiếu phong cách và tiêu chí của brief lúc QA.

- `shot_edits[].shot` là số cảnh từ 1 trên bản đang xem. `proof_lead` chọn lời dẫn trung tính cho cả voice và caption của thẻ dữ kiện. `narration` thay lời dẫn nói riêng. `caption` cho phép đặt lại ngắt dòng khi giữ đủ từng từ. Mỗi thẻ tối đa hai dòng, 39 ký tự mỗi dòng, 15 ký tự/giây cho cả voice và caption.
- `framing` chọn cận cảnh, toàn cảnh, giữ hình hoặc trả về chỉ dẫn gốc. `editor_note` ghi công việc nội bộ cho người dựng. Ghi chú nằm trong bản được QA và ngoài VTT.
- `shot_order` phải chứa đủ số cảnh đúng một lần. Có thể di chuyển nguyên nhóm thẻ bằng chứng và qualifier giữa các vị trí bằng chứng. Các thẻ thương mại, điều kiện và CTA giữ đúng vị trí. `durations` ghi số giây cho từng cảnh theo thứ tự cuối cùng, với tổng bằng thời lượng đã giao.
- Giá, thuế, đơn vị, MOQ, claim, qualifier, CTA, quyền ảnh và nguồn do backend lấy từ manifest có hiệu lực. Người có quyền duyệt phải độc lập với người sửa. QA đối chiếu bản giao với biên nhận edition, nguồn và hợp đồng thực thi trước khi quyết định.

Ví dụ thay chỉ dẫn ảnh và bàn giao công việc trên cảnh 2. Thay hai trường `expected_*` bằng dữ liệu thật của tài liệu.

```json
{
  "expected_qa_revision": 2,
  "expected_content_digest": "<sha256>",
  "mode": "editorial",
  "shot_edits": [{"shot": 2, "framing": "detail"}],
  "editor_note": "Giữ khung để người xem đọc hết điều kiện trước CTA."
}
```

## Thử riêng câu mở

Gửi `mode: "controlled_hook"` và `hook_variant` trên chính revision nền. Server thay câu mở, lời và caption của thẻ mở, rồi tạo VTT từ các cue. Giữ nguyên toàn bộ thời điểm bắt đầu/kết thúc của từng thẻ, các cảnh sau, visual, CTA, quyền, offer, nguồn và chỉ dẫn. Server từ chối khi câu quá dài, nội dung mở không đổi hoặc có chỉnh sửa thứ hai. Với thay đổi nhiều biến, dùng chế độ biên tập. `receipt.comparison.changed_variables` ghi những phần thực sự khác ở hai bản.

Mặc định hai nhánh cùng ghi `offline_no_landing` và `offline_no_delivery`. Đây là thiết kế thử nghiệm nội bộ chưa gán người xem. Để giữ một gói minh họa và trang đích đã duyệt, gửi thêm:

```json
{"distribution": {"landing_did": "<document UUID>", "landing_pid": "<package UUID>", "distribution_id": "<approved distribution UUID>"}}
```

Server kiểm tra lại quyền, revision, QA và digest của gói theo đúng client, brand và campaign. Biên nhận giữ đích đến và điều kiện phân phối đã xác minh **tại thời điểm chốt bản nền**. Bản sửa tạo revision mới và qua QA riêng. Khi dùng bản sửa để tạo gói phân phối tiếp theo, phải gắn và duyệt lại đúng revision ở Studio. Các trường traffic, chi và kết quả chỉ mô tả lượt thử ngoại tuyến này.

## Chạy lại và đọc bằng chứng

Chạy trong môi trường PostgreSQL test của dự án với database đã migrate, tài khoản runtime RLS và registry lock tương ứng checkout. Đặt `AMC_STORYBOARD_EDITION_EVIDENCE` đến thư mục output dành cho lần chạy này. Dữ liệu thử là tổng hợp. Các UUID và digest mới gắn với phiên chạy lại.

```sh
python -m pytest -q tests/test_storyboard_editions.py tests/test_video_storyboard.py
```

Tệp `rhythm-class-offline-comparison.json` lưu storyboard gốc, hai revision thay hook, một revision biên tập, phạm vi nguồn, hai bộ hash so sánh và các biên nhận QA độc lập từ PostgreSQL. Đối chiếu `baseline_content_digest`, `baseline_board_digest`, revision và `qa_receipts` bằng bản đã chỉnh trước khi so điều kiện hai nhánh. Trường `outcome` chờ phép đo trên phân phối được phép. Phép thử này chưa đo phản ứng của khách, thời gian của người dựng hoặc hiệu quả chuyển đổi.
