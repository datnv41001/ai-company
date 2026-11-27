# Phản biện kỹ thuật của người nhận bản Research → Strategy

Một agent khác người viết candidate và người soạn fixture đã chạy exporter, đọc bản trước/sau và thử sửa nguồn trong bộ ca phát triển công khai. Đây là kiểm kỹ thuật trên dữ liệu tổng hợp. Agent dùng lại các câu trả lời bộ giải mã đã cố định và gọi adapter Research/Strategy @4 để kiểm checkpoint. Không có lượt inference, UAT hoặc chấm mù trong bài này.

## Hai kết quả sai đã quan sát ở bản đang phát triển

| Ca và thay đổi duy nhất | Đáng lẽ người viết nhận được gì | Kết quả đầu tiên quan sát được |
|---|---|---|
| C63-01. Sao một fact của Route Tray thành nguồn hiện hành thứ hai, cùng scope và mặt hàng, ID khác. Nguồn gốc phủ nhận việc nhận diện người. Nguồn thử khẳng định khay nhận diện từng người đang giữ linh kiện. | Cần người có thẩm quyền hòa giải hai phát biểu trước khi giao lời có thể tái sử dụng. | Handoff là `draft_for_approval`. Cả hai câu trái nghĩa cùng xuất hiện trong `product_wording`. Danh sách thiếu dữ kiện rỗng. |
| C63-02. Đổi riêng nội dung của `tray-channel` thành “The owned product page is unavailable throughout this pilot.” Giữ tên kênh, quyền đọc, scope và thời gian. | Tự dùng tên kênh trong câu phủ định không cung cấp căn cứ để chọn kênh đó. | Strategy vẫn đánh dấu `supported` cho `owned product page`. Handoff vẫn giao chính kênh này. |

## Điều có thể làm tiếp từ phiếu

Ở ca Route Tray, người phụ trách Content biết cần sơ đồ hai phần mô tả việc tách lô trong ca giao ca. Fact chỉ cho phép mô tả khay thụ động và qualifier về nhận diện người. Chuyển sang người quản kho đang kiểm kê làm lựa chọn đổi sang ví dụ phiếu kiểm đếm. Bản ban đầu bị gài claim theo dõi nhân sự vẫn lọt validation của checkpoint với handle hợp lệ. Ở ca Fold Studio, người viết nhận ý tưởng nội bộ về việc chuẩn bị vải và dụng cụ cho buổi đầu. Trên bản sửa, `internal_concept` cho phép họ thảo luận ý tưởng với chủ chương trình. Kênh và phép đo còn thiếu nguồn, nên tài sản có vị trí phát hành giữ ở `hold`.

Lượt xuất đầu tiên trên 9 biến thể cũng cho thấy ca hai hành vi trái chiều, brief thiếu phân khúc/tình huống và nguồn thiếu đúng phân khúc đều giữ việc ở trạng thái `hold`. Thử độc lập việc thu hồi fact theo revision mới đã loại lời sản phẩm khỏi handoff. Chuyển quan sát duy nhất phù hợp sang scope client khác làm mất căn cứ chọn và ID ngoại lai biến mất khỏi kết quả. Mức đại diện vẫn giới hạn ở các episode tổng hợp có chủ đích. Câu hỏi về hành vi gần nhất còn cần người nghiên cứu đặt trong tình huống thực tế của người mua. Quyền phát hành, phút người viết phải sửa và hiệu quả thương mại chưa được đo.

## Chạy lại sau bản sửa

Tôi thay lại đúng hai dữ kiện trên rồi dựng lại checkpoint hợp lệ của cùng packet. C63-01 trả `hold`, `message=null` và `owner reconciliation of competing product wording`. Các fact vẫn có trong phần Research để chủ sản phẩm đối chiếu. C63-02 trả kênh `unknown`, giá trị `null` và `needs_owner_verification=["tray-channel"]`; tài sản chọn vị trí giữ ở `hold`. Ca Route Tray có bằng chứng khẳng định từ chủ kênh vẫn cho phép chuyển bản nháp đến Content duyệt. Với cách làm thận trọng này, hai fact hợp lệ nhưng diễn đạt khác nhau cũng có thể cần người hòa giải. Thẩm quyền trong fixture là dữ kiện tổng hợp do biên tập viên mã hóa.

Đã chạy exporter thật bằng `python -m scripts.strategy_study --output <thư-mục-mới>`. Cả 9 ca tạo được cặp `before.json` và `after.json`. Chạy `python -m pytest -q tests/test_strategy_study.py tests/test_strategy_workpaper.py` đạt **21/21** phép kiểm sau khi bổ sung đối chiếu digest của mã quan sát. Giữ mã cũ khi sửa nội dung ghi nhận sẽ đưa quan sát về trạng thái chờ người đọc kiểm lại. Digest kiểm tính nhất quán của mã và nguồn. Việc gán đúng ý nghĩa vẫn thuộc người biên tập. Hai lỗi đầu được giữ ở bảng trên để đối chiếu với các [test về câu phủ định, thẩm quyền và lời sản phẩm](../../../tests/test_strategy_workpaper.py).
