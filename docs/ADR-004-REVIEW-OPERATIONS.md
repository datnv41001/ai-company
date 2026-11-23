# ADR-004 · Vận hành cổng duyệt nội bộ

## Quyết định sau review PR #1

- **Danh sách.** GET `/api/tenants/{tenant}/reviews` trả mảng như trước. Mỗi trang mặc định 25, tối đa 100 dòng. Khi có trang sau, lấy header `X-Next-Cursor` rồi truyền `?cursor=...&limit=...`. Thiếu header nghĩa là hết. Sắp xếp giảm dần theo cặp (created_at, id) bất biến để xử lý nhiều bản cùng thời điểm. Cursor được tra trong phạm vi hiện tại. Nếu bị thu hồi quyền với dòng neo, tải lại từ đầu. Bản mới xuất hiện trước trang hiện tại khi làm mới. Bộ lọc áp vào cả dữ liệu và cursor. Một truy vấn JOIN sự kiện kết thúc lấy trạng thái cho cả trang. Nội dung và bình luận chỉ tải khi mở chi tiết.
- **Lý do.** Từ chối hoặc yêu cầu sửa cần ít nhất 5 ký tự sau khi bỏ khoảng trắng hai đầu. Lý do đi cùng sự kiện bất biến. Ngưỡng này chặn bỏ trống, chất lượng góp ý vẫn do người duyệt chịu trách nhiệm. Dữ liệu v3 từng cho phép lý do rỗng được giữ nguyên.
- **Sửa và hủy.** Thời điểm lưu bản sửa đầu tiên là lúc hủy yêu cầu đang chờ, kể cả khi bản sửa mới chưa qua QA. Mở màn hình soạn thảo chưa làm thay đổi yêu cầu. Nhân sự từ editor được hủy chủ động ở chi tiết phiên bản. Khóa giao dịch sắp thứ tự ghi. Nếu khách quyết định trước, quyết định được giữ cho đúng snapshot. Nếu agency lưu trước, quyết định đến sau nhận 409. Hai thao tác hủy và sửa thành công hoặc rollback cùng nhau. Chia sẻ bản mới vẫn cần QA độc lập.
- **Lời mời.** Admin/owner chọn tài khoản đã đăng ký, client, brand/campaign tùy chọn và quyền. Lời mời có hạn 7 ngày, xuất hiện trong ứng dụng của đúng người nhận. Quyền truy cập bắt đầu khi người nhận chấp nhận. Chỉ có một lời mời chờ cho một tài khoản trong một agency. Màn hình quản trị cho phép rút lời mời, sửa quyền hoặc thu hồi toàn bộ quyền xem. Cấp trực tiếp qua API quản trị cũ vẫn tồn tại. Hệ thống chưa xác minh email và chưa gửi email.
- **Ranh giới PostgreSQL.** `portal_invitations` có FORCE RLS và FK theo tenant/client/brand/campaign. Hai hàm có quyền owner dùng search_path cố định. Hàm danh bạ chỉ trả ID/email từ grant của agency cho admin. Hàm chấp nhận khóa đúng lời mời người đang đăng nhập, lấy toàn bộ phạm vi từ dữ liệu đã lưu, thêm membership, grant và audit trong một giao dịch. Không truyền role hay scope vào hàm chấp nhận. Quyền thực thi chỉ cấp cho runtime và chủ hàm.

## Phản biện và thiết kế nhiều client hoặc nhiều brand

Grant duy nhất vẫn phù hợp với trường hợp một tài khoản làm việc cho một client trong agency. Hai brand rời nhau hiện không thể được chọn mà vẫn loại các brand còn lại. Mở toàn bộ client trong tình huống này sẽ cấp dư quyền.

Khi có nhu cầu đó, dùng membership ngoài làm căn cứ vào workspace và bảng các dòng quyền có khóa riêng (tenant, user, client, brand tùy chọn, campaign tùy chọn, can_comment, can_decide). FK chứng minh chuỗi cha, unique index tách ba cấp phạm vi để xử lý NULL. Quyền cho một tài nguyên là hợp của **các dòng khớp tài nguyên đó**. Kiểm tra quyền xem và quyền ghi theo cùng snapshot, không gộp quyền quyết định ở client B với quyền xem ở client A. Giữ phân biệt role nội bộ/ngoài. Danh sách client, RLS, directory và các API cũ đang giả định một client sẽ phải chuyển cùng đợt.

Kế hoạch chuyển đổi gồm tạo bảng mới, backfill đúng một dòng cho mỗi grant hiện có, so sánh tập bản ghi nhìn thấy trước và sau, thêm test quyền chồng lấn và thu hồi từng dòng, rồi chuyển cả đọc và ghi sang grant mới trong một phiên bản. Trước khi cho phép tạo dòng thứ hai còn có thể quay về mô hình cũ. Sau đó cần giữ dữ liệu mới và đối soát khi phục hồi. Thiết kế này cần chủ sản phẩm xác nhận tình huống dùng chung tài khoản giữa các client trước khi triển khai.

## Nâng cấp và phục hồi

Migration 004 thêm bảng, index, policy và check cho các quyết định mới. Runner chạy lại an toàn. Các site tự quản cần dùng cùng quyền migration owner như schema 3. Sao lưu trước khi nâng cấp. Nếu giao dịch migration lỗi, PostgreSQL rollback. Nếu đã có lời mời, quyết định hoặc quyền mới, ngừng ghi và lưu bản v4 nguyên trạng. Khôi phục bản sao v3 sang DB khác cho commit `81e4791`, đối soát những thay đổi phát sinh rồi mới mở lại. Trả app về v3 sẽ đưa chính sách duyệt lúc sửa về cách cũ.

## Kiểm chứng và phần tiếp theo

Suite tạo 1.001 snapshot cùng thời điểm cho mỗi backend, duyệt toàn bộ bằng cursor, kiểm tra query count, client khác và trạng thái kết thúc. Tests lời mời dùng tài khoản admin, người được mời và người ngoài. Browser dùng hai phiên đăng nhập, gửi và nhận lời mời, tải thêm, yêu cầu sửa có lý do, đổi rồi thu hồi quyền. Workflow CI ở gốc repo chạy cả PostgreSQL và Docker Compose.

Các rào cản trước khi phục vụ khách thật vẫn gồm xác minh danh tính/email, chống lạm dụng và phục hồi vận hành. Phần tiếp theo của sản phẩm là thiết kế đường đi từ brief đến công việc của AI Director và chuyên viên trong cùng tenant, dùng kết quả QA và cổng bàn giao này. Runtime, ngân sách, outbox và connector cần tiêu chí nghiệm thu riêng.
