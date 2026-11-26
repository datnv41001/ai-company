# So sánh bốn cách thực hiện cùng công việc Marketing

Có hai brief tổng hợp trong [gói pilot gốc](../PILOT.md), gồm yêu cầu báo giá và đặt lịch dịch vụ. Tám phiếu giao việc được tạo trước khi mời người thực hành. Chưa có quan sát của người hành nghề. Chỉ người điều phối giữ khóa và gói phân công. Người chấm cuối chỉ nhận brief, sản phẩm gắn mã ẩn và phiếu chấm của vai trò mình.

| Nhánh | Công việc được giao |
|---|---|
| A · Thủ công | Người làm Marketing đọc brief và hoàn thành bản giao từ mẫu trống. Lưu bản đầu trước khi biên tập. |
| B · Bộ soạn tất định | Dùng bản đầu của bộ soạn hiện có, ghi công đối chiếu nguồn, sửa và đóng gói. |
| C · Có AI hỗ trợ | Dùng bản đầu Qwen 1.5B đã lưu trong bộ so sánh cùng brief. Người làm Marketing biên tập và giao theo quy trình của mình. |
| D · Có AI và QA độc lập | Bắt đầu bằng đúng các byte của C. Sau bản đầu do Marketing chuẩn bị, một reviewer thứ tư đối chiếu nguồn, ghi nhận xét, công QA, digest trước/sau. Lưu bản cuối kể cả khi reviewer trả về. |

**Tổ chức chấm.** Người điều phối giữ [khóa mã](custodian.json) và [phiếu giao việc](work-orders.zip). Phát từng brief và phiếu riêng. Lấy consent, không ghi tên thật vào bộ dữ liệu kỹ thuật. Phân bổ người làm việc có kinh nghiệm tương đương và cân bằng thứ tự giữa hai brief; ghi việc một người đã từng thấy brief. Với cùng một brief, người thực hiện nhánh A phải hoàn thành trước khi được xem phương án của AMC. Ghi dấu thời gian bắt đầu, bản đầu, yêu cầu làm rõ, biên tập, QA và thời điểm bàn giao. Không dùng alias quen thuộc để suy đoán cách sản xuất.

Người điều phối xóa mọi dấu hiệu nhánh trong bản giao, giữ đầy đủ nguồn, rồi giao cho reviewer cuối và Sales hoặc Service bộ [phiếu chấm ẩn nhãn](scorecards.zip). Chấm bản đầu theo rubric đã khóa, quyết định tiếp nhận bản cuối và đánh giá 0–2 về tính hữu ích của các trường bàn giao. Yêu cầu đối chiếu hành động thật của người nhận: Sales có đủ thông tin liên hệ báo giá, hoặc Service có thể phân công đúng địa điểm và ca. Ba người ký độc lập gồm Marketing, reviewer cuối và người nhận. Người QA thuộc nhánh D có actor riêng, không được đồng thời chấm đầu ra cuối. Điểm dựa trên đúng hai phiên bản đã lưu.

**Đối soát.** Lưu file cuối tại `<artifacts>/<brief>/<alias>/delivered.artifact`. Với D, lưu thêm `first.artifact` là bản người QA độc lập thực sự nhận và hai SHA-256 trong `preqa.json`. Ba phiếu chấm khai cùng revision và SHA cuối. Gộp các phiếu đã điền thành một mảng JSON; gộp phiếu QA bổ sung của D thành mảng riêng. Ghi rõ giờ công đã xác minh và chứng từ model, compute, công cụ, nhân công, kể cả lượt lỗi. Người điều phối phân bổ tiền model vào `model_vnd`, compute vào `compute_vnd`, công cụ vào `tools_vnd`, chi phí khác vào `other_vnd`. Chi phí QA riêng của D chỉ nằm ở phiếu `preqa`. Giữ riêng số đo đọc gói đã có và thời gian/chi phí tạo gói đầy đủ. Cần truy được chi phí tạo bản đầu từ lần chạy tương ứng trước khi so với sản xuất thủ công từ đầu.

```sh
python tests/evaluation/department/four_arm_pilot.py prepare /path/to/new-kit
python tests/evaluation/department/four_arm_pilot.py score /path/to/new-kit/custodian.json observations.json preqa.json /path/to/artifacts
```

Chương trình giữ đủ cả tám phiếu giao việc, tính lại SHA từng file và báo ca thiếu quyết định hoặc thiếu chứng từ. Ghi công việc bị từ chối và chưa hoàn thành. Chỉ tính tổng chi phí trên số việc được doanh nghiệp chấp nhận khi biết kết quả và chi phí của toàn bộ các ca đã giao trong nhánh. Thiếu dữ liệu để trống, kể cả khi phí provider cục bộ được xác nhận bằng 0. Tránh công khai phiếu người dùng thật, tên, dữ liệu khách hàng hoặc tệp gốc chứa thông tin riêng.
