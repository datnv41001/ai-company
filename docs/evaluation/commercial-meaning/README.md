# Biên tập câu thương mại và sản xuất nội dung theo kế hoạch

Người vận hành Marketing có thể mở bộ nháp trong Command Center khi có kế hoạch đã duyệt và đang hiệu lực. API đọc lại phạm vi, nguồn và digest kế hoạch. Hai mẫu social, trang web, câu trả lời tìm kiếm, lịch theo ngày, brief Creative và ad groups dùng cùng dữ kiện. Tổng ngân sách đề xuất bằng đúng trần kế hoạch, kể cả số tiền lẻ. Studio hiện cảnh báo số lượng, độ dài hoặc trùng biến thể. Bản quảng cáo quá giới hạn cần Media chỉnh trước khi xuất. [Quy cách đã đối chiếu](../../research/DEPARTMENT-PRODUCTION.md)

Studio gắn nhận định với đúng đoạn ký tự và nguồn đã ghim. Khi một nguồn giá bán phù hợp, bộ kiểm có thể phát hiện lời hứa hoàn tiền hoặc trả ngược tiền cho người mua. Hai quy tắc hẹp khác kiểm phạm vi vách ngăn và việc biến giả thuyết thành khảo sát đã hoàn thành. Chi tiết nguồn giữ nguyên giá, tiền tệ, đơn vị, thuế, MOQ, điều kiện, SKU, khu vực và kênh. Giá hoặc quan hệ ngữ nghĩa chưa đủ căn cứ vẫn qua QA. Bản được duyệt trước đây có lịch sử riêng. Bộ ca song ngữ chỉ kiểm các cấu trúc nêu trên. [JUnit lần đầu](red.xml) · [JUnit sau sửa](green.xml)

### Chạy lại trên máy khác

1. Khởi tạo môi trường dev theo README của repo. Dùng PostgreSQL tổng hợp và đường dẫn test trong job API của CI. Chạy `python -m pytest -q tests/test_semantic_commercial.py tests/test_campaign_planner.py tests/test_channel_editions.py tests/test_content_pack_outputs.py`. Trong cấu hình chỉ có SQLite, pytest ghi skip cho parametrization yêu cầu PostgreSQL.
2. Đặt `AMC_CONTENT_PACK_EVIDENCE` đến thư mục tạm dành riêng rồi chạy bộ kiểm trên để xuất JSON của hai brief nghiên cứu. So plan digest, manifest, điều kiện, CTA, phân bổ và trạng thái external receipt. ID giao dịch ở lần chạy khác sẽ khác. [Bộ đầu ra](outputs)
3. Theo setup Playwright trong CI và chạy `python -m pytest -q tests/browser_channel_edition.py`. Biến `AMC_STUDIO_EVIDENCE` chỉ thư mục ảnh. Kiểm bàn phím, chữ, phân bổ và cuộn ngang trên 1280, 820 và 390 px ở light/dark. [Ảnh thật và số đo trình duyệt](screens/channels)
4. Để quay lại phiên bản phần hiển thị, dùng checkout đã kiểm tra cùng runtime lock và phiên bản database tương thích. Artifacts đã giao và receipt không cần sửa. Quy trình khôi phục database phụ thuộc phiên bản journal của main. [Runbook chuyển và phục hồi journal](../sandbox-operations/CUTOVER.md)

Chưa có người hành nghề chấm hai bộ nháp. Công sửa, thời gian tiết kiệm, chi phí trên bản được chấp nhận và hiệu quả quảng cáo chưa đo. Việc tạo các bộ nháp và các đối chiếu này dùng bộ soạn deterministic cục bộ. Mẫu tham khảo thị trường có nguồn công khai; tên đối thủ cụ thể của khách cần căn cứ theo brief. [Gói pilot đã chuẩn bị](../department-study/PILOT.md)

Reviewer có thể thử một lời hứa thương mại mới trong cùng đoạn với câu có căn cứ, chỉnh phần đứng trước câu bị đánh dấu, thay thế kế hoạch và đăng nhập bằng khách khác trong cùng agency. Đối chiếu văn bản còn lại, actor, revision, kết quả sign/share và receipt trên chính commit đưa ra review.
