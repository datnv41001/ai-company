# ADR · Giao việc Marketing theo phạm vi đã duyệt

## Quyết định

AMC dùng hai chế độ workspace đã có là `inhouse` và `agency`. Solo và Business dùng `inhouse`. Người dùng Solo đi từ mục đích công việc đến bản nháp ngay trong workspace gốc. Business dùng cùng đường tạo nhiệm vụ, sau đó người có thẩm quyền khác kiểm tra bản giao. Agency tiếp nhận yêu cầu qua tài khoản khách có quyền đối với đúng client, thương hiệu và chiến dịch.

| Người dùng | Đường vào | Bản giao và quyền duyệt |
| --- | --- | --- |
| Solo | Trong hồ sơ thương hiệu, mở brief đã ghim sản phẩm, nhóm khách hàng và mục tiêu. Chọn **Chuẩn bị Marketing từ brief này → Giao nhiệm vụ cho AI Director**. | Chủ workspace được mở và biên tập bản nháp. Có thể dừng tại đây. |
| Business | Nhân viên có quyền biên tập giao nhiệm vụ cho AI trong chiến dịch nội bộ. Quản trị viên bật release tại chiến dịch. | Cần người duyệt độc lập với người giao nhiệm vụ và người sửa cuối cùng. Bản nháp nội bộ chỉ dùng trong workspace. |
| Agency | Nhân viên gửi brief tới người nhận đã có grant theo phạm vi. Khách mở **Yêu cầu cho AI Director** và xác nhận phần được phép dùng. | Nhân viên kiểm tra căn cứ, xếp việc. QA và bàn giao kiểm lại quyền, bằng chứng và phiên bản. |

## Ba lớp đầu vào

Business Knowledge cung cấp sản phẩm, thị trường, KPI, sự kiện đã duyệt và điều kiện áp dụng. Brand Guidelines ghim một revision công khai đã duyệt với chỉ dẫn, giọng văn và các cụm từ cấm. Task Brief ghim bản tóm tắt tác giả đã xác nhận gồm mục đích, đầu ra, sản phẩm, nhóm khách, địa bàn, ngôn ngữ, kênh, yêu cầu, cụm từ loại trừ và tiêu chí chấp nhận. Người giao việc phải chọn nội dung thích hợp để gửi cho đội Marketing. Tài liệu thô trong brief cũ và định vị nguồn hạn chế chỉ phục vụ luồng kiểm tra có quyền.

Nút **Kiểm tra mức sẵn sàng** đối chiếu đối tượng, sản phẩm, kênh, vùng, ngôn ngữ và loại đầu ra với căn cứ. Khi có khác biệt, giao diện nêu trường cần xác minh. Gửi nhiệm vụ đã sửa hoặc chọn lại nguồn phù hợp rồi kiểm tra lại. Yêu cầu và chỉ dẫn không tạo thêm bằng chứng cho nhận định thương mại. Mâu thuẫn giữa chuỗi cấm và câu chữ bắt buộc cần được giải quyết trước khi xếp việc.

WF-03 v3 và WF-13 v6 sử dụng `amc.marketing-manifest/2`. Hệ thống lưu digest của task intent, revision và digest của hướng dẫn, các tham chiếu tri thức, định danh chiến dịch và thế hệ của brief. Khi ghi nhận, xếp việc, duyệt và bàn giao, máy chủ kiểm tra lại thẩm quyền hiện tại. WF-03 v2 và WF-13 v5 vẫn xử lý manifest v1 cùng contract lịch sử của chúng.

## Hạ tầng và dữ liệu

Module PostgreSQL `amc_c3` v1 bổ sung cột nguồn gốc nhiệm vụ với mặc định `agency` cho hàng hiện hữu. Đối với nhiệm vụ nội bộ, cột `recipient_id` ghi định danh tác giả thật. Quyền gồm vai trò hiện hành, workspace inhouse và đúng phạm vi. Thu hồi quyền người giao nội bộ kết thúc công việc đang chờ hoặc đang xử lý. Gate phía máy chủ chặn chia sẻ ngoài với bản giao nội bộ.

Việc triển khai có thể gán pool worker vào một chiến dịch đã có ngân sách bằng `python -m scripts.provision_pool internal-route WORKER TENANT CLIENT BRAND CAMPAIGN`, dùng quyền publisher hiện có. Lệnh dùng chung một định danh vận hành theo workspace, giữ quyền editor cần thiết cho leasing, không tạo mailbox, mật khẩu, portal grant, workspace mới hoặc quyền QA. Chạy lại cùng phạm vi dùng lại chính định danh. DBA có thể thu hồi route hoặc tạm dừng workflow. Chỉ cấp route cho worker và chiến dịch đã được đơn vị vận hành cho phép.

## Kiểm và quay lại phiên bản đã duyệt

Chạy `python -m pytest -q tests/test_c3_task_intent.py` trên SQLite và PostgreSQL dùng runtime hạn chế. Trên PostgreSQL thử nghiệm, publish `catalog/landing-seo-v6.json` rồi chạy `python tests/browser_c3_task.py` với cấu hình mailbox, base URL và thư mục bằng chứng của bộ Chromium hiện hữu. Bài Chromium nhập mục đích, đối chiếu trường còn thiếu, kích hoạt workflow rồi ghi nhận manifest và run trong ba kích thước màn hình. Inference và chất lượng đầu ra có phiếu nghiệm thu riêng.

Khi cần ngừng release, tắt quyền kích hoạt release hiện hành tại từng campaign và để các bản đã lưu ở chế độ xem lịch sử. Agency có thể sử dụng lại release cũ cho công việc tương thích. Giữ schema và manifest lịch sử để bảo toàn truy vết. Nhiệm vụ nội bộ cần release hiểu được hợp đồng nội bộ.
