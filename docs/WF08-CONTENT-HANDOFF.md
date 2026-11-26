# Giao nội dung cho người dựng storyboard

Đội nội dung agency có thể chạy `WF-08/video-storyboard@2` trên một brief tổng hợp tiếng Việt, kênh `vertical-social` và hình minh họa tự dựng. Trong sổ thực thi, Director phân hai công việc nối tiếp. Vai trò `ai-copywriter-content-strategist` chuẩn bị nội dung theo kênh, sau đó vai trò storyboard nhận đúng bản có mã SHA-256 đã ghi ở checkpoint Content. Cả ba lượt dùng adapter tất định và ngân sách dịch vụ bằng 0.

## Giao việc và đọc bản nháp

1. Publish `catalog/video-storyboard-v2.json` bằng lệnh registry hiện hành, rồi kích hoạt các skill `director`, `content`, `storyboard` cho đúng campaign. Manifest và yêu cầu chạy phải cùng chỉ định phiên bản `@2`. API vẫn nhận `StoryboardIntent` hiện hữu.
2. Người giao việc ghi mục đích, người mua, sản phẩm, hành động, phong cách, yêu cầu và tiêu chí nghiệm thu. Ghim nguồn cho sản phẩm, điều kiện thương mại và hướng dẫn thương hiệu. Câu mục đích phải thống nhất với objective được duyệt của campaign.
3. Trong báo cáo run, đọc `checkpoints[1].output.sections.content_handoff`. Strategist bàn giao đối tượng, câu hỏi cần kiểm chứng với người mua, giả thuyết có sẵn trong manifest, hướng triển khai, hook, các dòng copy cùng nguồn, CTA và chỉ dẫn cho người dựng. Giả thuyết về người mua chỉ phục vụ ekip nội bộ.
4. `checkpoints[2].output.sections.storyboard` chứa kịch bản, chỉ dẫn, phụ đề, digest của handoff và bảng đối chiếu `brief_fulfillment.rows`. Mỗi dòng giữ nguyên yêu cầu, trạng thái và cách đối chiếu. `met` có nghĩa bản hiện tại đạt phép thử được nêu. `clarify` cần người giao việc làm rõ câu chữ hoặc bổ sung dữ kiện. `unsupported` ghi nhận giới hạn sản xuất đã biết. Bất kỳ mục bắt buộc nào còn mở đều chặn duyệt.
5. Với phản hồi về bản nháp, dùng đường biên tập storyboard trên đúng revision và digest. QA đối chiếu bản đã sửa. Nếu cần thay mục đích, quyền hoặc dữ kiện nguồn, nộp brief mới gắn manifest mới; checkpoint cũ lưu nguyên.

## Phạm vi hiểu brief hiện tại

Mục đích được kiểm tra với đúng tên sản phẩm đã ghim. Với RFQ, dùng “Nhận yêu cầu báo giá {sản phẩm}” hoặc “Giúp người mua đối chiếu điều kiện báo giá {sản phẩm}”. Hướng thứ hai cần có điều kiện báo giá đã duyệt. Với appointment, dùng “Nhận đề nghị đặt lịch {sản phẩm}” hoặc “Giúp người mua chuẩn bị đề nghị đặt lịch {sản phẩm}”. Với choose_session, dùng “Thu nhận lựa chọn buổi {sản phẩm}” hoặc “Giúp người học chọn buổi {sản phẩm}”. Các mục đích ngoài phạm vi này được giữ lại để làm rõ.

Các câu sau dùng được trong cả requirements và acceptance_criteria.

| Yêu cầu đã hỗ trợ | Bằng chứng cần xem trên bản hiện tại |
| --- | --- |
| Soạn storyboard có hình minh họa. | Quyền minh họa tổng hợp và chỉ dẫn hình cho từng cảnh. |
| Minh họa dữ kiện sản phẩm trước lời mời hành động. | Cảnh chứa dữ kiện đã ghim hoàn tất trước cảnh CTA. |
| Giải thích điều kiện báo giá trước lời mời hành động. | Có điều kiện báo giá đã ghim và xuất hiện trước CTA. |
| Đối chiếu điều kiện thương mại theo đúng nguồn. | Giá, điều kiện và nguồn ở các thẻ tương ứng; thiếu giá ghi vào ghi chú nội bộ. |
| Có phụ đề tiếng Việt khớp lời thoại. | Nội dung từng thẻ và WebVTT khớp bản thoại hiện tại. |

Chọn `plain`, `concise`, `formal` hoặc `friendly` để định hình câu mở. Phần dữ kiện giữ câu chữ đã duyệt. Yêu cầu ghi âm, video có âm thanh và cảnh quay người thật được ghi là ngoài khả năng sản xuất. Một câu ghép thêm điều kiện chưa hiểu được chuyển sang `clarify` dù một phần câu trùng mẫu.

## Tái hiện trên máy khác

Chạy `python -m pytest -q tests/test_storyboard_brief.py` trong môi trường acceptance PostgreSQL của repo. Đặt `AMC_BRIEF_EVIDENCE` trỏ vào một thư mục đầu ra mới để xuất brief, bản copy của Content, storyboard gốc và biên nhận QA riêng cho từng ca. Phép thử RFQ so sánh một khay chia linh kiện với brief mới cho thẻ so màu nhà in, thêm một ca bắt buộc ghi âm và một so sánh thay đổi riêng brief trên cùng sản phẩm.

WF-08@1 tiếp tục phục vụ việc tái hiện kết quả nội bộ cũ. Phiên bản @2 mới ghi các bước Content và đối chiếu brief nêu trên. Các bài thử xác nhận quyền, dữ kiện, sự bàn giao và tiêu chí có thể kiểm được. Tỷ lệ chuyển đổi, mức độ thuyết phục của copy, thời gian tiết kiệm cho agency và độ chính xác khi diễn giải mục tiêu tự do vẫn cần người làm Marketing đánh giá.
