# Thẻ kiến thức ứng dụng

Mỗi thẻ phân biệt **điều nguồn ghi nhận** với **giả thuyết áp dụng cho AMC**. Ví dụ sản phẩm là tình huống tổng hợp để xây ca nghiệm thu. Trạng thái triển khai và đầu vào được phép dùng tra trong [ma trận](APPLICABILITY_MATRIX.md).

<a id="k-01"></a>

## K-01 · Second Brain theo doanh nghiệp

Người làm Marketing cần trở lại được chứng cứ gốc sau khi một ghi chú được rút gọn. Quy trình raw → bản biên tập → chỉ mục → tái kiểm ở Wecommit cho một mô hình tổ chức kho cá nhân. [SRC-WE](SOURCE_REGISTRY.md#src-we)

**Áp dụng thử.** Với SKU có hai bảng giá, lưu locator, phạm vi và ngày hiệu lực ở nguồn. Brief chọn revision đã đối chiếu. Khi có bảng mới, người phụ trách nhận yêu cầu đánh giá lại; bản đã giao vẫn truy được nguồn cũ.

**Giới hạn.** Một kho Obsidian cá nhân không kiểm chứng quyền giữa hai khách hàng. Kiểm bằng hai brand cùng tên và nguồn restricted. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-01)

<a id="k-02"></a>

## K-02 · Lấy đúng ngữ cảnh tại thời điểm dùng

Anthropic mô tả việc giữ tham chiếu nhẹ rồi chỉ lấy phần liên quan khi agent cần. Phần nguồn được đọc muộn có thể thay đổi sau khi lập kế hoạch. [SRC-AC](SOURCE_REGISTRY.md#src-ac)

**Áp dụng thử.** Research nhận fact, giả thuyết và câu hỏi mở theo mục đích. Copy chỉ nhận câu dùng được và qualifier. Ghi revision, digest, số token, nguồn thiếu và outcome của từng bước.

**Giới hạn.** Giảm token có thể bỏ mất thời hạn giá hoặc thị trường. Thử cùng brief có/không có projection, so lỗi ngữ cảnh, chất lượng và chi phí. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-02)

<a id="k-03"></a>

## K-03 · Marketing Skill có phiên bản

Mẫu skill của Anthropic tách mô tả thường trực khỏi phần hướng dẫn chuyên môn nạp khi cần. [SRC-AS](SOURCE_REGISTRY.md#src-as)

**Áp dụng thử.** Dùng pin hiện có của WF-13 để đổi rubric cho nội dung landing. Lưu ví dụ, counterexample và release. Mở lại run trước nâng cấp phải cho đúng rubric cũ.

**Giới hạn.** Một skill mô tả đúng quy trình vẫn có thể dẫn đến câu Marketing sai. Không nhận script từ bài đọc làm quyền chạy. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-03)

<a id="k-04"></a>

## K-04 · AI Director theo mục tiêu có thể kiểm

Google Cloud mô tả cách chọn mẫu điều phối theo phụ thuộc và điều kiện dừng. Tăng số agent thường kéo theo chi phí phối hợp. [SRC-GC](SOURCE_REGISTRY.md#src-gc)

**Áp dụng thử.** Mục tiêu báo giá của chiến dịch có nhánh nghiên cứu và chiến lược. Director phải nêu đầu ra cần có, điều kiện dừng và nguồn còn thiếu trước khi đề xuất plan. Trạng thái hoàn tất lấy từ công việc và bản giao đã ghi.

**Giới hạn.** Số nhiệm vụ xong chỉ đo tiến độ thực thi. Đạt KPI kinh doanh cần nguồn chỉ số riêng. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-04)

<a id="k-05"></a>

## K-05 · Chọn cơ hội trước khi chọn chiến thuật

Migicovsky hỏi về lần gần nhất người dùng gặp vấn đề. Torres nối nhu cầu quan sát được với outcome rồi so nhiều giải pháp. Ví dụ của Marketing Against the Grain là brainstorming cho một sản phẩm giả định. [SRC-YC](SOURCE_REGISTRY.md#src-yc) · [SRC-LP](SOURCE_REGISTRY.md#src-lp) · [SRC-PT](SOURCE_REGISTRY.md#src-pt) · [SRC-MT](SOURCE_REGISTRY.md#src-mt)

**Áp dụng thử.** Nếu nhiều khách hỏi về đổi trả, ghi lần gặp, phân khúc, chứng cứ và kết quả mong muốn. So cập nhật trang sản phẩm với hướng dẫn cho tư vấn viên, ghi giả định có thể bác bỏ cho từng lựa chọn.

**Giới hạn.** Tần suất trong một mẫu tự chọn chưa chứng minh nhu cầu toàn thị trường. Số gợi ý do AI sinh không làm tăng độ tin cậy. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-05)

<a id="k-06"></a>

## K-06 · Asset Intelligence và tái sử dụng có ràng buộc

Ahrefs mô tả chuyển video thành bài viết. Search Central khuyến khích nội dung giải quyết việc người đọc thực sự cần và có đóng góp riêng. [SRC-AH](SOURCE_REGISTRY.md#src-ah) · [SRC-PF](SOURCE_REGISTRY.md#src-pf)

**Áp dụng thử.** Từ bài hướng dẫn của brand A, tạo bản nháp email cho cùng đối tượng. Giữ quan hệ với revision gốc, quyền dùng lại, thị trường, qualifier, điều chỉnh cho kênh và lý do người đọc cần phiên bản mới.

**Giới hạn.** Đổi định dạng không đảm bảo thứ hạng hay doanh số. Quyền đọc nguồn và quyền tái sử dụng cần được xét riêng. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-06)

<a id="k-07"></a>

## K-07 · Thử nghiệm Marketing có điều kiện kết luận

Công trình KDD ghi nhận các trường hợp nhóm vận hành thử nghiệm diễn giải sai biến động chỉ số. Case Zalora được cộng đồng thuật lại đặt giả thuyết từ vấn đề khách không nhận ra chính sách hoàn trả. [SRC-EX](SOURCE_REGISTRY.md#src-ex) · [SRC-BV](SOURCE_REGISTRY.md#src-bv)

**Áp dụng thử.** Trước thử nghiệm ghi đối tượng đủ điều kiện, đơn vị phân bổ, kỳ đo, metric chính, metric bảo vệ và quy tắc kết thúc. Khi thiếu mẫu, tracking đổi giữa kỳ hoặc outcome đến muộn, báo chưa kết luận.

**Giới hạn.** Chưa có dữ liệu gốc của case cộng đồng. Các mức lift trong bài không phải baseline hay forecast cho agency. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-07)

<a id="k-08"></a>

## K-08 · Từ lead đến doanh thu có thể đối soát

GA4 đặt tên riêng cho tạo lead, đủ chuẩn và chuyển đổi. Search Console và Analytics đo các bước khác nhau. MeasureSchool nêu cách thống nhất tên để người vận hành hiểu cùng một cài đặt. [SRC-GA](SOURCE_REGISTRY.md#src-ga) · [SRC-SC](SOURCE_REGISTRY.md#src-sc) · [SRC-MS](SOURCE_REGISTRY.md#src-ms)

**Áp dụng thử.** Ví dụ tổng hợp: hai event tạo lead lặp cùng khóa, một lead được qualify, chưa có hóa đơn. Báo một lead, một lead đủ chuẩn và doanh thu chưa biết. Đơn vị tiền, múi giờ, kỳ đối soát và nguồn sổ bán hàng phải hiển thị khi có giá trị.

**Giới hạn.** close_convert_lead tự thân không chứa bằng chứng đã thu tiền. Clicks và sessions cũng không có quan hệ một-một. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-08)

<a id="k-09"></a>

## K-09 · Cải tiến liên tục qua ca lỗi đã duyệt

Anthropic phân biệt trace của agent với trạng thái thật của hệ thống. Bài kèm talk của Hetzel khởi đi từ lỗi tác động đến người dùng rồi ghi lý do của một kết quả đúng. [SRC-AV](SOURCE_REGISTRY.md#src-av) · [SRC-AI](SOURCE_REGISTRY.md#src-ai)

**Áp dụng thử.** Nếu bản giao ghi 'đã duyệt' mà DB không có quyết định khớp revision, đưa ca tổng hợp vào regression. Chạy candidate và baseline trên cùng input, kiểm tác dụng phụ và xét duyệt trước khi thay release.

**Giới hạn.** Điểm do model chấm thay đổi theo model. Cần phân tách phép đo deterministic, nhận xét chuyên môn và trạng thái chưa xác minh. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-09)

<a id="k-10"></a>

## K-10 · Thư viện kiến thức cho reviewer

Husain và Shankar đề xuất đọc các ví dụ trước, mô tả lỗi bằng ngôn ngữ cụ thể rồi gom nhóm. Một taxonomy hữu ích gắn được với ca và lý do. [SRC-HA](SOURCE_REGISTRY.md#src-ha) · [SRC-AV](SOURCE_REGISTRY.md#src-av)

**Áp dụng thử.** Thẻ 'ngày hiệu lực của offer' kèm ví dụ phù hợp, phản ví dụ, nguồn, phạm vi và lần đối chiếu. Chỉ ghim vào tác vụ evaluator qua phiên bản. Giữ tách nguồn học khỏi đáp án holdout.

**Giới hạn.** Một retrieval receipt chứng minh thao tác truy xuất đã được ghi. Chỉ capability run có đối chứng mới cho thấy chất lượng finding thay đổi. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-10)

<a id="k-11"></a>

## K-11 · Command Center theo việc người dùng đang làm

Linear giảm cạnh tranh thị giác giữa navigation và vùng nội dung. Geist phân biệt màu bề mặt, biên, chữ và trạng thái. W3C giải thích cách nội dung reflow khi không gian thu hẹp. [SRC-LI](SOURCE_REGISTRY.md#src-li) · [SRC-VE](SOURCE_REGISTRY.md#src-ve) · [SRC-WC](SOURCE_REGISTRY.md#src-wc)

**Áp dụng thử.** Cùng một tác vụ tạo brief giữ tên và thứ tự focus trong hai theme. Agency nhìn rõ khách/brand đang chọn. Biểu đồ tiến độ có số và chữ đọc được kể cả khi bỏ màu. Khi nguồn lỗi, hiển thị lỗi thay vì giá trị 0.

**Giới hạn.** Các case thiết kế không chứng minh AMC dễ dùng. Phải thử dữ liệu thật qua API, cả workspace rỗng, trên desktop/tablet/mobile và đo riêng với người dùng. [Đối chiếu mã và yêu cầu](APPLICABILITY_MATRIX.md#k-11)

Đợt áp dụng tiếp theo bổ sung transcript YC, ca SEO của Rakuten và phương pháp so sánh bản giao cho K-06 đến K-10. [Xem nguồn, quyết định, tiêu chí và phương án bác bỏ](C3-QUALITY-AND-REVIEWER-CAPACITY.md).
