# Nghiên cứu công khai theo câu hỏi

Đề xuất cho increment sau V4. Core AMC không gửi dữ liệu cho provider. Broker chỉ nhận mã câu hỏi từ danh mục công khai, locale, loại nguồn và mốc thời gian. Chẳng hạn một câu hỏi về cách nền tảng đếm sự kiện dùng các thuật ngữ chung đã duyệt. Việc chuyển từ câu hỏi nghiệp vụ sang mã chủ đề diễn ra trong môi trường riêng. Khi thiếu chủ đề, lưu nghĩa vụ chờ duyệt thay vì đưa nguyên văn brief hoặc nhận xét của reviewer vào truy vấn.

| Quyết định | Hợp đồng đề xuất |
| --- | --- |
| Phạm vi tìm kiếm | Operator cho phép riêng provider, host, endpoint, từ vựng công khai và TTL trong manifest. Chỉ manifest có quyền mới được bật. Crossref REST là ứng viên cho metadata các nghiên cứu. Dùng kho tài liệu nhà cung cấp đã duyệt cho quy tắc sản phẩm. Dùng nguồn cộng đồng được phép để tìm tín hiệu cần kiểm thêm. [Tài liệu Crossref](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) |
| Giới hạn | Tối đa hai truy vấn cho mỗi chủ đề, năm kết quả mỗi truy vấn, hai nhà xuất bản cho mỗi kết luận, một lần truy xuất nội dung mỗi URL đã được admission. Cấp ngân sách byte, thời gian và số lượt ở cấp run trước khi gửi. Lỗi quyền, robots, quota, redirect ngoài danh mục hoặc timeout trở thành nguồn thiếu. |
| Chọn nguồn | Đầu tiên kiểm đúng đối tượng, kỳ, khu vực và ngày hiệu lực. Xếp tài liệu chính thức, nghiên cứu gốc rồi ý kiến cộng đồng theo loại câu hỏi. Gom các bản sao và site đăng lại cùng một nghiên cứu. Hai nguồn trái nhau được giữ cạnh nhau với ngày và phạm vi. |
| Bằng chứng | Lưu URL, publisher, thời điểm, đoạn trích cần thiết, locator, digest, tình trạng truy xuất và quyền lưu trữ. Metadata phục vụ tìm tài liệu. Cần đọc nội dung mới có thể quy kết phát biểu. Digest cho phép so lại bytes đã lưu. Khi không lưu toàn văn, phải ghi giới hạn replay và kiểm lại publisher nếu cần. |
| Phát hành | Hai reviewer thực hiện đánh giá đầu tiên độc lập, sau đó mới đọc các finding đã ghim. Lưu cả bất đồng, ca chưa đủ bằng chứng và kết luận cuối có source handle. Người phụ trách xem assignment trước khi đưa sang triển khai. |

## Đo giá trị của tìm kiếm

Đăng ký trước cùng một bộ ca mới và hai nhánh cùng số token. Một nhánh dùng thư mục cố định, một nhánh dùng tìm kiếm bị giới hạn. So số ca đồng thời đúng kết luận, nguồn áp dụng, lý do và hành động. Đối chiếu cả cờ sai, từ chối phù hợp, số lần thiếu nguồn và chi phí trên mỗi sửa đổi có căn cứ. Báo cáo theo từng reviewer/checkpoint. Kết quả v5 trong cùng thư mục chỉ đo so sánh reviewer trên nguồn tổng hợp cố định. Quyết định kích hoạt provider, xác nhận quyền đọc revision AMC, cô lập và quản lý khóa độc lập còn mở.
