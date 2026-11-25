# Chuẩn giao diện AMC

## Màn hình và phạm vi

Sidebar mở từng màn hình nghiệp vụ. Liên kết `?workspace=<id>#/knowledge` mở hồ sơ sau đăng nhập. Các đường dẫn `#/overview`, `#/campaigns`, `#/workforce`, `#/reviews` và `#/deliverables` mở tổng quan, chiến dịch, điều phối AI, phê duyệt và bàn giao. Cổng khách hàng chỉ có các màn hình thuộc vai trò của người nhận. Khi thu hẹp quyền, ứng dụng xóa dữ liệu cũ và hiển thị thông báo.

Nút tên workspace mở bộ chọn workspace. Trên Tổng quan, người dùng còn có thể lọc chiến dịch theo thương hiệu. Lịch sử trình duyệt giữ màn hình, thương hiệu theo dõi và chiến dịch. Mở Hồ sơ doanh nghiệp từ một thương hiệu đã chọn sẽ đi đến đúng hồ sơ trong phạm vi được cấp. Trên desktop, nút ở chân sidebar thu gọn thanh điều hướng. Trên điện thoại, thanh công cụ có menu, tên workspace, làm mới và tài khoản. Chọn **Tài khoản và giao diện** để đổi chế độ màu.

| Dữ liệu trên Tổng quan | Cách đọc |
| --- | --- |
| Toàn workspace | Bốn tổng số giữ nguyên khi đổi chiến dịch hoặc lọc thương hiệu. |
| Kế hoạch Marketing | Tiến độ lấy từ nhiệm vụ của chiến dịch đang chọn. |
| Bộ phận phụ trách | Mở thẻ để xem vai trò, tên nhiệm vụ và trạng thái kế hoạch. |
| Thực thi AI | Lượt chạy, trạng thái và số checkpoint đến từ Workforce. Mở **Workflow đã triển khai** để xem phiên bản, kỹ năng và quyền đã cấp trong chiến dịch. |
| Kết quả bàn giao | Mỗi bản có trạng thái QA, tình trạng nguồn và bước chia sẻ khả dụng theo quyền. Máy chủ kiểm tra điều kiện tại thời điểm gửi. |
| Kết quả kinh doanh | Khi chưa có nguồn đo, màn hình ghi rõ dữ liệu còn thiếu. |

### Kiểm tra giao diện PR #34

Job `compose-browser` chạy Chromium trên PostgreSQL ở 1440, 1280, 820, 390 và 320 CSS px. Dữ liệu tổng hợp được tạo qua API. Các phép thử giữ một phản hồi đọc nhiệm vụ thật hơn 650 ms, đo vị trí nút và panel trước, trong, sau khi tải, kiểm tra focus và cuộn. `ui-acceptance.json` ghi riêng điểm dịch chuyển sau thao tác gần nhất và dịch chuyển ngoài cửa sổ 500 ms. CLS tải ban đầu dùng cửa sổ phiên tối đa 5 s và khoảng nghỉ 1 s. Kiểm tra bổ sung gồm bàn phím, vùng chạm, nhãn tiếng Việt dài, email dài, sáng/tối/theo hệ thống và pinch zoom 200% trong Chromium.

Ảnh gốc có mã kiểm tra theo từng viewport. Ảnh mới và sáu cặp ảnh trước/sau nằm trong artifact `premium-ui-<revision>`. Hãy xem ảnh, mở liên kết trực tiếp bằng hai vai trò và đọc kết quả đo của đúng revision. Dữ liệu đo trong lab phản ánh máy chạy và bộ dữ liệu tổng hợp tại thời điểm đó. [Ảnh trước và SHA-256](ui-evidence/pr34-before/manifest.json)

Áp dụng chuẩn này cho PR có thay đổi giao diện nhân sự, khách hàng hoặc người dùng chưa đăng nhập. Người triển khai và reviewer dùng cùng các quy tắc trên desktop, tablet và điện thoại. [CSS dùng chung](../app/static/design-system.css) · [Kiểm thử trên Chromium](../tests/browser_premium_ui.py)

## Mục tiêu của từng màn hình

Mỗi màn hình cần trả lời người dùng đang ở tổ chức nào, dữ liệu thuộc phạm vi nào và thao tác tiếp theo dẫn tới đâu. Đặt tiêu đề và hành động chính trước các công cụ phụ. Với quy trình dài, người dùng có thể rời đi, tải lại và trở về đúng ngữ cảnh theo hợp đồng dữ liệu của tính năng. Chỉ thêm nhãn, mô tả hoặc biểu tượng khi chúng hỗ trợ quyết định hoặc thao tác cụ thể.

| Thành phần | Quy tắc triển khai |
| --- | --- |
| Khung ứng dụng | Dùng chung thanh điều hướng, khu vực tài khoản, chọn workspace và chọn giao diện. Liên kết phải đến đích sử dụng được trong phạm vi quyền hiện tại. |
| Tiêu đề và chữ | Dùng Inter hoặc font hệ thống hỗ trợ đầy đủ tiếng Việt. Tiêu đề cấp trang có độ lớn thích ứng với viewport. Nhãn, đơn vị và thông tin về nguồn dữ liệu luôn đọc được khi zoom. |
| Bề mặt và màu | Dùng `--canvas`, `--paper`, `--layer`, `--ink`, `--muted`, `--border` theo vai trò. `--accent` dành cho hành động, `--warn` cho việc cần chú ý và `--danger` cho lỗi. Văn bản mô tả trạng thái đi cùng màu. |
| Thẻ và số liệu | Dùng `.command-card`, `.metric`, `.state-chip`, `.panel` hoặc thành phần tương đương dựa trên cùng token. Chỉ hiển thị số 0 sau khi nguồn trả kết quả. Dùng dấu gạch và giải thích khi thiếu mẫu số hoặc chưa tải được dữ liệu. |
| Biểu mẫu | Mỗi trường có nhãn, ràng buộc và thông báo bằng ngôn ngữ người dùng. Giữ nội dung đang chỉnh sửa khi chỉ cập nhật bảng điều hành. Quyết định QA, tài chính và thay đổi quyền đi qua luồng có thẩm quyền của server. |
| Phản hồi | Hiển thị đang tải, dữ liệu rỗng, lưu thành công, lỗi có thể thử lại và mất quyền như những tình huống riêng. Gắn phản hồi gần thao tác. Vùng `role=status` thông báo thay đổi mà không tự chuyển focus. |
| Dữ liệu nghiệp vụ | Mọi tổng, nhóm, trạng thái và tỷ lệ đều có nguồn, phạm vi và mẫu số. Nút thử lại chỉ đọc không kích hoạt worker. Giữ nguyên tên và nội dung người dùng nhập. |

## Chủ đề và khả năng tiếp cận

Cho phép **Theo hệ thống**, **Sáng** và **Tối**. Chỉ lưu lựa chọn chủ đề dưới khóa `amc.color-mode` và dùng chế độ hệ thống khi trình duyệt chặn lưu trữ. Nếu hệ điều hành đổi chủ đề, cập nhật ngay trong chế độ theo hệ thống. Dùng `prefers-reduced-motion` và ưu tiên tương tác đơn giản qua HTML chuẩn.

Từ 901px, thanh điều hướng nằm bên trái. Từ 900px trở xuống, nút Menu mở thanh điều hướng có `aria-controls`, `aria-expanded`, quản lý focus và hỗ trợ Escape. Ở 630px trở xuống, form và danh sách trở thành một cột, chỉ số có thể dùng hai cột. Kiểm tra tối thiểu 320 CSS px, dữ liệu dài, bàn phím, focus nhìn thấy, chữ phóng lớn và cả hai chủ đề. Dùng tương phản tối thiểu 4,5:1 cho chữ thường và 3:1 cho chữ lớn. Vùng chạm chính tối thiểu 44 CSS px. Ngày giờ, tiền tệ, đơn vị và tình trạng thiếu dữ liệu phải được ghi rõ trong ngữ cảnh.

## Nguồn dữ liệu của trung tâm điều hành

| Khu vực | Nguồn và ý nghĩa |
| --- | --- |
| Tổng số chiến dịch, bản giao | Danh sách hiện tại từ `GET …/campaigns` và `GET …/deliverables` của workspace đang chọn. Dữ liệu có thể khác giữa các tài khoản. |
| Chờ QA, đã qua QA | Đối chiếu quyết định ghi trong deliverable với revision và digest của assessment. Bản ghi cũ mang trạng thái approved nhưng thiếu liên kết hợp lệ quay về Chờ QA. Server kiểm tra lại bằng chứng và nội dung khi chia sẻ thực sự. |
| Tiến độ và các bước | `GET …/campaigns/{campaign}/tasks` trả các bước kế hoạch. Tỷ lệ lấy số nhiệm vụ hoàn tất chia cho tổng nhiệm vụ của chiến dịch đó. Chọn một bước để mở nhiệm vụ và đầu ra dự kiến. Với tập rỗng, tỷ lệ chưa xác định. |
| Bộ phận | Nhóm các nhiệm vụ đã lưu theo `role_slug` và trường `group` của `GET /api/catalog/roles`. Khi thiếu tên nhóm, hiển thị vai trò sẵn có. Số việc là số nhiệm vụ được gán theo kế hoạch. |
| Lượt xử lý AI | Dùng brief có campaign ID để ghép với tối đa 100 run gần nhất mà Workforce trả về cho workspace. Hiển thị trạng thái và số checkpoint trên số bước trong workflow. Đây là nguồn theo dõi thực thi của worker. |
| Bản giao | Lọc bản giao từ API đúng campaign ID, hiển thị tiêu đề và trạng thái QA hiện tại. Chỉ số doanh thu, chuyển đổi hoặc ROI cần dữ liệu đo lường riêng. |
| Không gian trống | Với quyền ghi, liên kết dẫn tới doanh nghiệp, thương hiệu hoặc chiến dịch theo điều kiện còn thiếu. Chế độ agency và Marketing nội bộ lấy từ membership thực. |

Các dữ liệu trên nằm trong bộ nhớ theo phiên. Khi đổi workspace hoặc tài khoản, hủy yêu cầu đang tải, xóa phần trình bày cũ và chỉ chấp nhận kết quả đúng lần chọn mới nhất. Khi quay lại tab, xác minh membership trước khi đưa bảng điều hành trở lại. Khách cổng bàn giao chỉ có các luồng phù hợp với quyền khách hàng.

## Tiêu chí duyệt PR giao diện

1. Chạy lại các hành trình mà PR thay đổi bằng Chromium thật. Fixture tổng hợp có thể tạo qua API nghiệp vụ. Lưu ảnh desktop, tablet, mobile ở cả hai chủ đề cùng thông tin phiên bản và viewport.
2. Đối chiếu số trên màn hình với API và DB cùng phạm vi. Bao gồm dữ liệu rỗng, bản ghi cũ, dữ liệu bị thu hồi và hai lượt tải trả về đảo thứ tự.
3. Đi bằng bàn phím qua điều hướng, form và hành động chính. Kiểm tra tương phản, focus, reflow, thông báo lỗi, quyền chỉ đọc và cổng khách hàng. Đính kèm kết quả đo cùng giới hạn bằng chứng.
4. Ghi lại cách chuyển máy, lệnh thử, dữ liệu chưa có nguồn và cách rollback trong HANDOFF. Reviewer có thể yêu cầu thay đổi khi số liệu mẫu xuất hiện trong giao diện thật hoặc khi ảnh đẹp che một luồng chưa hoạt động.

## Cơ sở thiết kế

AMC dùng hệ thống token theo vai trò cho cả chế độ sáng và tối. Quyết định tổ chức màu dựa trên hướng dẫn chính thức của IBM Carbon và Vercel Geist. [IBM Carbon Color](https://carbondesignsystem.com/elements/color/overview/) · [Vercel Geist Colors](https://vercel.com/geist/colors)

Phân cấp điều hướng tập trung vào nội dung đang làm và hành động có thể thực hiện. Các trạng thái thành công, lỗi và cảnh báo dùng phản hồi phù hợp với ngữ cảnh. [Linear UI redesign](https://linear.app/now/how-we-redesigned-the-linear-ui) · [GOV.UK Notification Banner](https://design-system.service.gov.uk/components/notification-banner/)

Quy tắc menu thu gọn, focus và reflow dựa trên hướng dẫn W3C. [WAI Disclosure](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/) · [WCAG Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html)
