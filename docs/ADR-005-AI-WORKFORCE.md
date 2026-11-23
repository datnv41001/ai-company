# ADR-005 · Bộ máy thực thi Marketing AI nội bộ

## Từ brief đến bộ tài sản

Agency mở phiếu theo đúng campaign và chỉ định một người nhận đang có grant. Người đó đăng nhập, gửi mục tiêu, đối tượng, đề nghị và ít nhất một nguồn có trích đoạn. API báo trường thiếu và cho gửi lại cùng nội dung nếu mất phản hồi. Người nội bộ chọn kỹ năng bổ sung và ngân sách trước khi đưa brief vào hàng đợi. Mỗi brief tạo tối đa một run. Brand Kit phải có thông tin sản phẩm trước khi chạy.

Ở bước Director, model viết kế hoạch và giao một nhiệm vụ cụ thể cho từng chuyên môn trong phạm vi agency đã chọn. Backend giữ thứ tự Director → Research → Strategy → Content và nối SEO, Creative, Ads, Analytics nếu được chọn. Research tạo quan sát, giả thuyết và khoảng trống từ nguồn đã nhập. Strategy tạo định vị, kênh và KPI. Content tạo tiêu đề, nội dung và CTA. Bốn chuyên môn còn lại lần lượt trả đầu ra SEO, brief thiết kế, hai mẫu quảng cáo và thiết kế đo lường. Đây là các kỹ năng của một worker văn bản; Creative chưa sinh file thiết kế và Ads chưa mua quảng cáo.

Worker chụp dữ liệu Brand Kit, nguồn, brief và phiên bản prompt tại lúc xếp hàng. Mỗi lượt model chỉ nhận dữ liệu của run và các checkpoint trước đó. Không tự mở URL nguồn. Mỗi kết quả phải đáp ứng hợp đồng riêng của kỹ năng và dẫn một mã nguồn hợp lệ. Chỉ output chuyên môn đi vào bản làm việc có trạng thái chờ QA. Người QA có thể trả lại, sửa và gửi qua người QA khác theo cơ chế hiện hữu. Khi agency chia sẻ, bản giao được đóng phiên bản và băm. Khách duyệt phiên bản đó qua portal. Run tra cứu bộ tài sản đã được duyệt bằng deliverable, version, digest và sự kiện approved; bản đầy đủ có trong portal.

## Hàng đợi, chi phí và quyền

- PostgreSQL dùng khóa dòng và SKIP LOCKED. SQLite dùng BEGIN IMMEDIATE cho phát triển. Trước khi gọi model, worker commit lease, attempt và dự phòng chi phí. Khi xong, kiểm tra lại đúng scope, editor, token và hạn lease. Checkpoint cuối và bản làm việc được ghi trong một giao dịch. Nếu mất tiến trình sau khi gọi provider, lượt gọi có thể lặp khi lease hết hạn. Chỉ một kết quả được ghi. Phí của lượt mất phản hồi có thể đã phát sinh.
- Retry tối đa ba lượt cho từng kỹ năng, có khoảng chờ tăng dần. Checkpoint hoàn tất trước lỗi được giữ. Đến hạn cứng, tiến trình gọi model bị kết thúc. Worker khác có cùng phạm vi có thể tiếp quản lease đã hết hạn; run lỗi sau ba lượt giữ lịch sử để chẩn đoán. Bắt đầu công việc mới sau sửa cấu hình bằng một brief mới.
- Local dùng giao thức chat completions và JSON Schema của llama.cpp. Tùy chọn OpenAI dùng URL dịch vụ cố định, key của worker và mức giá do người vận hành cấu hình. Ngân sách là micro-USD mỗi run (1 USD = 1.000.000 micro-USD). Dự phòng dùng số byte dữ liệu, phần đệm và giới hạn token đầu ra. Lượt có usage hợp lệ được đối soát theo giá cấu hình. Khi không có usage tin cậy, giữ dự phòng. Chi phí local ghi 0 phí API; điện, phần cứng, hóa đơn thật và ngân sách tổng theo tenant chưa được đo.
- Hai bảng có FORCE RLS. Bảng intake chỉ cho người nhận đúng grant gửi dữ liệu một lần. Bảng run, prompt, Brand Kit và checkpoint chỉ dành cho nội bộ. Worker dùng tài khoản DB runtime và danh tính editor chuyên dụng được người triển khai cấu hình cùng tenant/client/brand/campaign. Kiểm tra lại khi claim và khi ghi kết quả. Context được phục hồi sau rollback trên cùng session. Model không nhận thông tin DB, token, công cụ SQL, lệnh shell hoặc connector.
- Đếm nguồn tham chiếu, đối chiếu số liệu trong câu với trích đoạn đã dẫn và hiển thị số cần QA. Chỉ số này không xác minh sự thật của nguồn, ngữ nghĩa, mức độ sáng tạo hay hiệu quả chiến dịch. Nhật ký ghi kỹ năng, phiên bản prompt/model, lần thử, thời gian, usage và chi phí; không in nội dung hoặc khóa vào log ứng dụng.

## Phản biện và bằng chứng

Test tích hợp kiểm tra người nhận sai, grant bị thu hồi, client/brand/campaign sai, worker ngoài tenant, hai worker cạnh tranh, khôi phục lease, từ chối kết quả cũ, retry, ngân sách, QA và lưu đúng digest khách đã duyệt. Bộ test dùng gateway kiểm soát để tạo lỗi xác định. Job CI `workforce-model` tải model có checksum, chạy suy luận thật trên CPU trong Compose với dữ liệu giả và hoàn thành luồng qua HTTP. Job browser kiểm tra gửi và xếp hàng từ giao diện.

Trong lần thử local với Qwen2.5-0.5B-Instruct Q4_K_M, bốn checkpoint hoàn thành sau năm lượt; Strategy đã retry một lượt cho đầu ra vượt giới hạn. Model gọi sản phẩm là “affordable” dù Brand Kit không có giá. Người kiểm thử dùng tài khoản QA mẫu trả lại bản nháp, sửa copy và gửi một tài khoản QA khác duyệt trước khi đóng phiên bản. Tài khoản khách mẫu đã duyệt v1. Ghi nhận 1.425 input token và 443 output token ở các lượt thành công, phí gọi model local là 0. Digest bộ tài sản đã sửa là `d77c340a5d80a6d86ec64379da1d12610e57e8aea3dfedb491556466f40273f6`. Đây là kiểm tra luồng và một ví dụ lỗi chất lượng. Đánh giá cho từng ngành cần bộ brief chuẩn và người chấm độc lập.

P0 trước khi dùng dữ liệu thật vẫn gồm xác minh email, chống lạm dụng, quản lý phiên, tách quyền dịch vụ và đối soát chi phí. Backlog P1 từ review PR #2 gồm quyền editor hủy ở cấp dự án, phân trang danh bạ/lời mời và nhiều grant trên một membership. Một worker hiện nhận một campaign theo cấu hình tin cậy. Điều phối nhiều campaign, ngân sách toàn agency, research ngoài nguồn nhập và ảnh/video là việc tiếp theo.

## Migration, rollback và nguồn model

Migration 005 chỉ thêm bảng brief/run, index, hàm và chính sách. Runner chạy lặp được; đường nâng từ v1/v2/v3/v4 giữ dữ liệu cũ. Trước nâng cấp cần chụp DB. Nếu phải quay lại, dừng worker và ghi mới, lưu nguyên DB v5 để giữ checkpoint và lịch sử phê duyệt, phục hồi bản v4 riêng rồi dùng commit `47a5718`. Đối soát mọi bộ tài sản phát sinh trước khi đưa hệ thống cũ vào sử dụng.

Trọng số là lựa chọn riêng của người vận hành, không lưu trong Git. Model mẫu là [Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/tree/9217f5db79a29953eb74d5343926648285ec7e67). Script kiểm tra SHA-256 trước khi cài vào thư mục models. Trình suy luận dùng [llama.cpp](https://github.com/ggml-org/llama.cpp); Compose ghim digest image, lần chạy Windows dùng CPU binary b12649. Cấu hình schema và giới hạn nội bộ ở app/workforce_gateway.py.
