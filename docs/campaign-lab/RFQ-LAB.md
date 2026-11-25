# Campaign Execution Lab · Hành trình RFQ vật liệu xây dựng

Người phụ trách chiến dịch cần biết một yêu cầu báo giá đã đi từ tài sản nào đến Sales, đơn hàng nào đã hủy và doanh thu nào thực sự có thể quy về chiến dịch. Bản nội bộ này cho phép bộ phận Marketing và Sales diễn tập một hành trình dùng cùng mã sản phẩm, người mua và mục tiêu. Toàn bộ dữ liệu, người duyệt và đích nhận đều là fixture tổng hợp. Campaign Center chỉ dùng campaign thật làm ranh giới quyền vào lab.

## Chạy và kiểm tra trên máy mới

Từ gốc repository với môi trường Python đã cài `requirements-dev.txt`:

```shell
python -m scripts.campaign_execution_lab --output rfq-run.json
python -m pytest -q tests/test_campaign_lab.py
```

Trong ứng dụng, thành viên từ quyền editor trở lên gọi `POST /api/tenants/{tenant_id}/campaigns/{campaign_id}/execution-lab/replay` qua Campaign Center. Endpoint trả dữ liệu vừa chạy. Khách của agency và tài khoản ngoài tenant không được dùng endpoint này. Các lần nhấn chạy lại cùng kịch bản tạo lại kết quả tại chỗ, không cập nhật trạng thái của campaign, danh sách khách hoặc ngân sách đang vận hành. Các review, hệ số chi phí và chỉ tiêu trong lab chỉ áp dụng cho bộ dữ liệu này.

[Kết quả chạy đã lưu, gồm đầy đủ tài sản, quyết định và biên nhận](RFQ-REPLAY.json) · [Nguồn mục tiêu, tri thức, lịch và sự kiện](../../catalog/labs/b2b-rfq-v1.json) · [Các quyết định mẫu khóa theo nội dung](../../catalog/labs/b2b-rfq-v1-approvals.json)

## Luồng nghiệp vụ và phiên bản

Hợp đồng `campaign-execution-lab/rfq@1` lấy sáu hàng WF-06/07/17/18/19/20 từ catalog khi chạy và tái sử dụng bảy gói công việc cùng vai trò của kế hoạch campaign hiện hữu. Hợp đồng này quy định các bước diễn tập. Trạng thái và phiên bản các workflow sản phẩm giữ theo registry. [Đặc tả V1](../PRODUCT_SPEC_V1.md) · [Ma trận truy vết](../PR9-TRACEABILITY.md) · [Kế hoạch campaign](../../app/services/marketing.py)

1. Kiểm tra digest của mục tiêu và tri thức đã duyệt trong fixture. Đề xuất phân khúc thu mua nhà thầu, mục tiêu RFQ, ba kênh, chi phí thử nghiệm, người nhận và mốc nghiệm thu. Ghi các câu hỏi còn thiếu như tồn kho theo lô. Plan ở trạng thái `proposed` đến khi khớp quyết định riêng của người giữ ngân sách trong fixture.
2. Tạo bản trang tiếp nhận RFQ, bài mạng xã hội, quảng cáo tìm kiếm, SEO metadata, brief thiết kế và lịch nội dung. Mỗi tài sản khóa SKU, người mua, mục tiêu, phiên bản tri thức và đề xuất chiến dịch. Mã băm tiêu đề/nội dung dùng cùng quy tắc với QA của AMC. Brief thiết kế giao cho bộ phận sáng tạo để sản xuất hình ở bước sau.
3. Đối chiếu quyết định QA theo toàn bộ bản tạo và quyết định kênh theo đúng slot, tài sản và plan. Đổi nội dung hoặc lịch làm mất hiệu lực quyết định trong fixture. Khi so với file pin, dùng plan ở trạng thái `proposed` và tài sản ở trạng thái `generated`; response hiển thị trạng thái sau duyệt. Các quyết định là mẫu do chương trình kiểm chứng, chưa phải chữ ký của chuyên viên.
4. Trong lịch mô phỏng, mở trang ngày 3, thử quảng cáo ngày 4, ghi lần lỗi rồi thử lại thành công, hủy slot mạng xã hội. Mã slot chống nhân đôi chi phí khi gọi lại. Tối đa hai lần thực thi cho mỗi slot, kiểm tra ngày đến hạn và trần ngân sách trước mỗi lần. Biên nhận thành công chứa chi phí VND, digest bản giao và digest quyết định. Hành động hủy không tạo biên nhận thành công.
5. Đối soát sự kiện nguồn để trả dữ liệu cho Sales, báo cáo chi phí và đề xuất cải tiến theo kết quả mẫu. Thiếu đồng ý liên hệ hoặc dữ liệu công trình thì không chuyển Sales. Thử nghiệm tiếp theo được gợi ý trong báo cáo và cần người quyết định.

## Hợp đồng giao nhận CRM tổng hợp

| Dữ liệu | Quy tắc tiếp nhận |
| --- | --- |
| Dòng sự kiện | `event_id` là khóa lần phát, `type` mô tả loại sự kiện, `at` là ngày nguyên dương kể từ đầu lab. Cùng ID và cùng nội dung đếm một lần. Cùng ID khác nội dung làm dừng đối soát. Báo cáo ghi các event đến muộn, chiếu lại theo ngày nghiệp vụ rồi theo thứ tự nhận trong ngày. |
| Phiên truy cập | Nguồn gồm `session_id`, `visitor_id` giả danh và `action_id`. Hai phiên của một khách đếm một visitor. Chỉ nhận attribution nếu slot có biên nhận thành công trước hoặc trong ngày truy cập. Thiếu nguồn vẫn giữ RFQ, khoản bán và ngoại lệ. |
| Yêu cầu báo giá | `rfq_id` định danh yêu cầu nghiệp vụ. Cùng yêu cầu gửi lại với event ID mới và nội dung y hệt được gộp. Khác biệt phải đối soát. Chỉ đủ điều kiện khi có diện tích dương, quận/huyện, mốc cần hàng và đồng ý nhận báo giá. |
| Bàn giao Sales | Sau qualification, event `sales_handoff` tạo payload gồm khóa yêu cầu và idempotency, diện tích, địa bàn, ngày, quyền liên hệ giới hạn vào RFQ và đích Sales tổng hợp. Lịch sử kèm ID sự kiện nguồn. CRM có thể ánh xạ các trường này vào opportunity ở một tích hợp sau khi có quyền riêng. |
| Trạng thái Sales | Bàn giao → báo giá → đơn → xác nhận số tiền nguyên dương VND. Có thể từ chối RFQ trước khi đặt hàng hoặc hủy đơn đã đặt/đã xác nhận. Mỗi RFQ hỗ trợ một đơn trong bản này. Chuyển sai trạng thái tạo ngoại lệ và không ghi nhận tiền. |
| Báo cáo kỳ | `orders` gồm mọi đơn từng phát sinh, `confirmed_orders` chỉ gồm đơn xác nhận còn hiệu lực. Doanh thu xác nhận trừ toàn bộ đơn hủy. Doanh thu có nguồn chỉ tính trên session liên kết biên nhận hợp lệ. Chi phí là tổng chi phí mô phỏng của biên nhận thực thi thành công. |

## Bằng chứng và giới hạn

Kịch bản đã chạy có 25 dòng sự kiện. Ba visitor tạo bốn phiên. Năm RFQ dẫn tới ba RFQ đủ điều kiện, ba lần chuyển Sales, ba báo giá và ba đơn. Hai dòng trùng được khử. Một đơn hủy sau khi xác nhận khiến doanh thu còn 10 triệu VND, trong đó 8 triệu có nguồn. Hai RFQ thiếu attribution. Chi phí quảng cáo mô phỏng là 1,2 triệu VND, chi thực bằng 0. Báo cáo ghi riêng một RFQ thiếu thông tin và một yêu cầu bị từ chối. Quy mô mẫu không đủ để suy ra doanh thu tăng thêm hoặc lợi suất quảng cáo.

Mỗi lần chạy ghi `runtime_ms` của phép tính nội bộ. Sổ công việc ghi sáu đầu ra đúng quyết định fixture, số đơn vị được doanh nghiệp thực nghiệm chấp nhận vẫn bằng không. Thời gian biên tập, QA, mức tiết kiệm và chi phí lao động chưa đo. Chưa có kết nối CRM, trình xuất bản, nhà cung cấp quảng cáo hoặc model thực trong hành trình này. Cổng Commercial GA vẫn NO-GO.

Reviewer có thể đổi một chữ trong bản tài sản mà giữ quyết định cũ, gửi hai event cùng ID khác số tiền, hoặc đặt sự kiện hủy sau xác nhận trước khi đóng kỳ. Kiểm tra rằng lab từ chối bản cũ, báo xung đột và đối soát đúng doanh thu còn hiệu lực. Khi sang pilot người dùng, bước tiếp theo là một RFQ được tạo từ mục tiêu và dữ liệu được phép của chính doanh nghiệp, có người phụ trách thật phê duyệt và Sales ghi phản hồi trong môi trường kiểm thử.
