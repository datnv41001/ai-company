# Hai brief đối chứng · Research → Strategy → Content

## Công việc được giao

Product marketing lead cần chọn chủ đề cho bản nháp trang sản phẩm khay linh kiện **Route Tray**. Họ có hai cách trình bày cụ thể, bàn giao ca và kiểm kê quý. Người nhận là Content lead. Studio programme manager có một quyết định khác cho lớp sửa quần áo **Fold Studio**, giữa hướng dẫn học viên mới chuẩn bị và hướng dẫn đặt chỗ theo nhóm. Brief này dùng tình huống đặt lịch. Người ra quyết định, mục tiêu, quyền sử dụng, giới hạn claim và hai phương án có trong từng packet. Hai brief, nguồn, lời người mua và câu trả lời decoder đều do nhóm triển khai tạo cho nghiên cứu nội bộ. [Route Tray](../../../tests/fixtures/strategy_study/route-tray.json) · [Fold Studio](../../../tests/fixtures/strategy_study/fold-studio.json)

## Baseline và phép so sánh

Trước khi viết candidate, nhóm đã gọi validator thực sự do registry phân giải cho Research @4 và Strategy @4. Hai ID nguồn hợp lệ đi kèm kết luận cố định “Both sites requested worker tracking.” Validator chấp nhận dù nguồn mô tả một khay thụ động tách lô và sự khác nhau giữa hai tình huống sử dụng. Sau khi dựng packet có đủ mã nguồn gốc, harness tái hiện bằng `registry_adapters.specialist_request`, `resolve(...).validate`, `c3_studio.compose` và `c3_studio.quality_issues`. Ở bước soạn bản nội bộ, câu trên vẫn có trong rationale, danh sách cảnh báo cấu trúc trống. Đây là một ca qua validator và staff composition. Quyết định QA, client snapshot và chất lượng phổ biến của model cần các phép đo khác. [Cách gọi binding](../../../scripts/strategy_study.py) · [Output model có sẵn từ CI #62](ARCHIVED-WF03.json)

Cả hai nhánh lấy cùng các nguồn được phép ở cutoff. Mỗi nguồn được biểu diễn thành handle, excerpt và metadata cho adapter cũ, gồm loại quan sát, tình huống, phân khúc, phương án, mục đích dùng, revision và giới hạn lấy mẫu. Cả brief và lựa chọn của người giao việc vào task intent. Strategy nhận checkpoint Research trực tiếp làm predecessor. Baseline giữ câu trả lời decoder mở cố định để người khác tái lập được đường xử lý. Candidate dùng đúng hai checkpoint đã validate và cùng packet để lập thêm bản đối chiếu. Người soạn packet đã gắn các ghi nhận `used/asked/declined` với phương án trong nguồn tổng hợp. Các nhãn đó có sẵn cho cả hai nhánh. Chưa đo độ chính xác khi người thật phân loại dữ liệu thô hoặc khi model sinh câu trả lời mới.

## Kết quả từng tình huống

| Phép đổi đã kiểm | Research và Strategy phải thể hiện | Bàn giao tiếp |
| --- | --- | --- |
| Route Tray, trưởng ca | Một ca *dùng* sơ đồ bàn giao và một người *hỏi* về kiểm kê. Đề xuất bàn giao dựa trên ca đã dùng. | Bản nháp sơ đồ hai khung. Chủ kênh cho phép soạn trên trang sản phẩm; phương pháp đo đã có nguồn riêng. |
| Cùng sản phẩm, người quản kho | Nguồn ở đúng ngữ cảnh kiểm kê được dùng làm căn cứ. Chuyển sang phương án kiểm kê. | Giữ lại đến khi có kênh và cách đặt nội dung phù hợp phương án đó. |
| Một quan sát được sửa ở revision 2 | Ghi nhận đã dùng thay từ sơ đồ bàn giao sang sơ đồ kiểm kê. Phương án đổi sang kiểm kê ngay cả khi giữ nguyên decoder. | Giữ assignment có vị trí đăng. |
| Hai trưởng ca dùng hai phương án khác nhau | Giữ hai episode và trade-off. Cần thêm dữ kiện để chọn. | Hold. |
| Thu hồi quyền kênh và hết hạn phương pháp đo đúng tại cutoff | Quan sát gốc vẫn hỗ trợ giả thuyết bàn giao. Kênh và phép đo về unknown. | Hold. |
| Fold Studio, học viên lần đầu | Trích nguyên văn lần dùng checklist chuẩn bị. Một người từ chối bản hướng dẫn đặt nhóm và một organizer ngoài nhóm đích có hành vi khác. | Có thể đề xuất hướng first visit. Chưa phân công sản xuất lên kênh khi thiếu quyền và cách đo. |
| Brief Fold Studio thiếu segment và tình huống | Hỏi lại người giao việc trước khi chọn phương án. | Hold. |
| Chỉ quan sát instructor diễn tập | Giữ giới hạn mẫu. Chưa có căn cứ suy ra hành vi học viên mới. | Hold. |
| Thêm bản ghi của client khác | Cả prompt baseline lẫn candidate loại dữ kiện của client kia. Kết luận về first visit giữ nguyên. | Hold. |

Trên chín phép đối chứng thuộc hai brief, một bản giao ở mức `draft_for_approval`. Tám bản còn ở `hold`; trong đó năm bản có hướng đề xuất nhưng thiếu căn cứ giao việc có kênh. Chọn chủ đề và cấp phép hành động là hai quyết định riêng. [Kỳ vọng và phép kiểm literal quote, authority, cutoff và downstream](../../../tests/test_strategy_study.py)

## Phần việc còn lại của người sử dụng

Với Route Tray, bản baseline yêu cầu editor tự đối chiếu ít nhất ba điểm cụ thể: bỏ claim theo dõi nhân sự, xác định segment theo tình huống bàn giao và kiểm quyền kênh thay cho đề xuất chạy search ads. Bản bàn giao mới chỉ đưa câu mô tả khay đã cho phép vào phần claim và chỉ giao sơ đồ bàn giao để duyệt. Với Fold Studio, editor có thể giữ nguyên quan sát đã trích từ `studio-one` nhưng phải loại suy diễn “Every learner wants a private group booking.”, xin quyền kênh và làm rõ đơn vị đo trước khi lập assignment có vị trí đăng. Việc trùng đúng cả đoạn nguồn được đánh dấu là literal; đó không phải bộ chấm entailment ngôn ngữ tự nhiên. Paraphrase đúng có thể vẫn cần editor đối chiếu.

Câu hỏi về lần gần nhất ra quyết định và các phương án đã cân nhắc là gợi ý phỏng vấn. Chưa quan sát người dùng trả lời các câu đó. Không có số đo phút biên tập, conversion, market size, đối chứng về model hay practitioner acceptance. Cần kiểm trên các nguồn mới có consent và người đánh giá nghiệp vụ trước khi suy rộng.

## Chạy lại

Từ thư mục gốc sau khi cài dependency phát triển, dùng `python -m scripts.strategy_study --output review-63` với thư mục đích mới. Mỗi thư mục ca có `before.json` (prompt quan sát được, checkpoint, staff draft và flags), `after.json` (ma trận căn cứ và lựa chọn) và `WORK-ORDER.md` (bản giao đọc được). `index.json` ghim checksum từng cặp và mã băm packet. Khi chạy `python -m pytest -q tests/test_strategy_study.py`, có thể đặt `AMC_STRATEGY_CASE_RESULTS` tới thư mục trống để lưu expected/actual theo ca. Cả hai lệnh đều dùng fixture. [Runner](../../../scripts/strategy_study.py)
