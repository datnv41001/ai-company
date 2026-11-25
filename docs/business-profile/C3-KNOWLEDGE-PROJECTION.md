# Dữ liệu nghiệp vụ đầu vào cho WF-03 và WF-13

C3 tạo bản phát hành adapter riêng sau khi C1 và C2 có hợp đồng ổn định. Mỗi workflow kê khai vai trò của dữ liệu đầu vào, trường bắt buộc, trường tùy chọn, purpose và mức hiển thị cho phép. Manifest cũ tiếp tục tái lập được qua release pin. C3 dùng bản brief, nguồn và quyền đã kiểm tra khi nhận lệnh thật.

| Dữ liệu | WF-03 nghiên cứu và chiến lược | WF-13 nội dung và SEO |
| --- | --- | --- |
| Công ty, brand, hướng dẫn | Ghim revision chung và override ở brand | Ghim thêm guideline về cách dùng từ và giới hạn công bố |
| Product, variant, thị trường | Chọn subject cụ thể và thị trường nghiên cứu | Trùng SKU, locale, channel, region và đối tượng của asset |
| Audience, objective, KPI | Tách giả thuyết cần kiểm tra, dữ kiện có nguồn và câu hỏi còn thiếu | Chỉ dùng fact có nguồn cho câu công khai. Mục tiêu và định nghĩa KPI là chỉ dẫn nội bộ |
| Giá, hàng, policy, claim | Trình bày xung đột và thiếu căn cứ như vấn đề nghiên cứu | Giữ nguyên qualifier, điều kiện và reference; dữ kiện thiếu hoặc disputed chặn sử dụng câu tương ứng |

Server tạo bytes canonical từ role của từng entry, revision của công ty/brand/sản phẩm/đối tượng/mục tiêu, scope, evidence handle và trạng thái fact/hypothesis. Sắp thứ tự ổn định, ghim schema/projection version, release adapter, campaign/brief generation và hợp đồng đầu ra. Evidence handle có kiểu riêng cho ô catalogue, quan sát giá, nghiên cứu mẫu người dùng hay định nghĩa phép đo; bằng chứng giá không thể xác minh một phân khúc. Với nghiên cứu ghi sampling frame, phương pháp, địa bàn, kỳ thu thập và giới hạn. Với KPI ghi định nghĩa tử số, mẫu số, đơn vị, thời gian, cách quan sát và nguồn có thể đối chiếu. Một URI/ID đơn lẻ không đủ. Manifest lưu cả yêu cầu bắt buộc còn thiếu. Dữ liệu nguồn hạn chế chỉ truy xuất qua phần server có quyền. Worker nhận đúng projection cấp cho vai trò của nó.

| Ranh giới | Công việc trong transaction | Kết quả khi dữ liệu đã đổi |
| --- | --- | --- |
| Queue | Resolve đúng input, grant, campaign/brief generation, digest, thời hạn và spend cap. Ghi authority decision cùng enqueue hoặc một outbox có fence trong cùng giao dịch | Trả trạng thái chặn kèm dữ kiện cần sửa. Không có run hoặc reservation thứ hai khi retry |
| QA | Ghim revision/digest của deliverable và knowledge manifest thực sự dùng; xác minh lại tất cả dependency dưới khóa nhất quán | Giữ draft, hiển thị claim mất hiệu lực. Điểm QA cũ vẫn thuộc lần đánh giá cũ |
| Share | Kiểm quyền người giao và người nhận, trạng thái QA, hiệu lực từng nguồn và generation ngay tại transaction tạo bản bàn giao | Giữ snapshot trước đó. Quyết định mới yêu cầu khắc phục nguồn hoặc duyệt lại theo revision |

Biên nhận lịch sử cho biết ai đã quyết định ở thời điểm nào. Khi command được gửi lại sau thu hồi, trả trạng thái lệnh ban đầu để đối soát; mọi side effect còn chờ cần kiểm tình trạng hiện hành trước khi thực hiện. Hàng đợi không được lấy một receipt cũ làm quyền thực thi mới. Định danh lệnh và transaction fence bảo đảm chỉ một lần ghi khi phản hồi thất lạc. Nếu withdrawal và authorize đến đồng thời, commit order quyết định hiệu lực. Dùng hai kết nối thật để kiểm cả hai thứ tự ở từng ranh giới, kể cả worker tiếp quản lease hoặc khởi động lại sau mất ACK.

Khi nâng release, chạy lại adapter cũ với manifest đã lưu, kiểm bytes và quyền truy xuất lịch sử. Kiểm riêng vết nguồn sai SKU, dữ kiện chưa đủ, scope khác, KPI không tương thích, giá hết hạn giữa queue và QA, thu hồi sau QA, A → B → A và giao lại sau restart. Rollback bằng chọn release trước cho công việc mới và bảo toàn releases, snapshot, lease, ledger đã có. Hợp đồng này chưa kích hoạt workflow hay giao nội dung ra ngoài.
