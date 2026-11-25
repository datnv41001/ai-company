# Bàn giao Business Knowledge Center cho vòng review nội bộ

## Trải nghiệm trên máy mới

Dùng nhánh tích hợp của [PR #31](https://github.com/datnv41001/ai-company/pull/31). Từ checkout sạch, tạo cấu hình local và khởi động Docker Compose bằng các lệnh sau. Mỗi máy dùng mật khẩu và hộp thư thử riêng.

```shell
git switch feature/knowledge-center-acceptance
python scripts/init_env.py
docker compose up --build -d
docker compose ps -a
```

Job migrate phải hoàn tất. Mở origin local được cấu hình trong Compose, đăng ký và xác minh qua hộp thư dev theo [hướng dẫn khởi động](../../HANDOFF.md). Mở **Hồ sơ doanh nghiệp**, chọn khách hàng và thương hiệu. Lưu một phần hồ sơ chung rồi chuyển sang thương hiệu thứ hai để kiểm tra kế thừa. Mở danh mục để tạo SKU, audience hoặc mục tiêu. Trong **Nguồn và nhận định**, người có quyền duyệt có thể đối chiếu trích dẫn và câu dùng cho Marketing. Trong **Brief nháp**, chọn **Chọn dữ liệu từ danh mục** rồi tạo brief cá nhân. Mỗi mục được chọn ghim đúng revision và digest. Có thể tạo brief khi còn thiếu dữ liệu. Xem [workspace](C2-WORKSPACE-RUNBOOK.md), [danh mục](C2-CATALOG-RUNBOOK.md) và [bàn duyệt](C2-CLAIM-DESK.md).

Bản nghiệm thu dùng mode `inhouse` cho cá nhân hoặc đội nội bộ và `agency` cho tổ chức phục vụ nhiều khách hàng. Người bán Solo thử bằng một thành viên, một workspace và không có người nhận portal. Toàn bộ tài khoản, sản phẩm, nguồn và phiếu duyệt trong phép thử là dữ liệu tổng hợp.

## Mốc đã chốt trên main

| PR | Commit đã merge | Git tree trùng cây đã chạy integration | CI trên chính commit merge |
| --- | --- | --- | --- |
| C1 [#22](https://github.com/datnv41001/ai-company/pull/22) | `bf003af1ef7f0223ac0c7163b3a5d5baf5b970e0` | `7e836025e05d9b2b407acf93b8958deb9c6e2de4` | [3/3](https://github.com/datnv41001/ai-company/actions/runs/45526145638) |
| Thiết kế C2/C3 [#24](https://github.com/datnv41001/ai-company/pull/24) | `7449ca2b0a927d0e9f04ab0453b87d555b9f0aa0` | `a9d75a22a9ab9bc66fd870ea6dbcc2a8b84a9e3b` | [3/3](https://github.com/datnv41001/ai-company/actions/runs/45527517642) |
| Research Broker thử nghiệm [#26](https://github.com/datnv41001/ai-company/pull/26) | `b976565be27e3f6e08fda6a55e37037f7595e0f7` | `1697aa8cfde6beeee60f57e481ffaf9bb3fc21e9` | [3/3](https://github.com/datnv41001/ai-company/actions/runs/45528612133) |

Workspace [#27](https://github.com/datnv41001/ai-company/pull/27), catalog [#29](https://github.com/datnv41001/ai-company/pull/29), claim desk [#30](https://github.com/datnv41001/ai-company/pull/30) và nghiệm thu [#31](https://github.com/datnv41001/ai-company/pull/31) xếp theo thứ tự phụ thuộc. Head và integration đã đối chiếu cùng kết quả CI được ghi trong PR tương ứng. Mỗi lần đổi base cần chạy lại CI cho head và integration trước khi merge.

## Kiểm tra bằng chứng

Trong run Pull Request, chọn job **compose-browser (integration)** và tải artifact `knowledge-center-journeys-integration`. Đối chiếu `tested_revision` trong `journeys.json` với checkout của chính job. File ghi từng persona, viewport, thời gian, ảnh và phép kiểm đếm trên PostgreSQL. Ca bổ sung về mất phản hồi, tranh ghi hai tab, thu hồi quyền và phản hồi đến muộn ở `tests/browser_knowledge.py`. Ca editor và nguồn hạn chế ở `tests/browser_claim_desk.py`. Log API cho biết số test, các đường nâng cấp có dữ liệu và restore sang database khác. Để tái chạy trên máy khác, dùng cùng lệnh và biến loopback của [workflow CI](../../.github/workflows/ci.yml) với database thử mới.

Mốc 3 phút cho thiết lập và 5 phút cho brief là mục tiêu đối với người dùng thật. Thời gian đo bằng Chromium là thời gian máy thực hiện kịch bản. Chỉ tiêu cần một pilot riêng có người sử dụng.

## Hợp đồng dữ liệu và việc còn mở

- **C2-G01/G03** · Catalog yêu cầu mã SKU, biến thể và địa bàn chính tắc. Nếu có trùng hoặc phạm vi chưa xác định, cần người phụ trách phân giải trước khi dùng. Chưa có bộ master địa lý toàn cầu.
- **C2-G02/G04** · Dữ liệu có các chiều người mua, thanh toán, dịch vụ và điều kiện thương mại đối chiếu qua mã. Đơn vị chưa có quy đổi đã xác định cần người dùng làm rõ. C1 chỉ cho duyệt giá trong khoảng hiệu lực. Có thể lưu giá tương lai dưới trạng thái nháp.
- **C3-G01/G02** · Hash và revision giữ được bản đã dùng. Độ tin cậy của nguồn và sự phù hợp trong câu AI sinh ra cần đối chiếu riêng. Brief nháp hiện chỉ chuẩn bị đầu vào nội bộ. Khi các hợp đồng ổn định, nghiệm thu WF-03/WF-13 có release mới, giữ bản cũ và kiểm quyền lại tại queue, QA và share. So sánh chất lượng nghiên cứu, chiến lược và bản nội dung theo rubric với cùng brief đóng băng, có/không có tri thức. [Ranh giới transaction và tiêu chí chất lượng](C3-KNOWLEDGE-PROJECTION.md)
- **Identity A1** · Core migration 023 dành cho [#25](https://github.com/datnv41001/ai-company/pull/25). Nhánh Business Knowledge Center này dùng core 22 và `amc_business` v2. Lần diễn tập hai thứ tự trên database mới cho thấy A1 có thể giữ nguyên hàng workspace khi nâng core 22 → 23 nhưng thay định nghĩa hàm `knowledge_commercial_conflict`. Chiều ngược lại, publisher C2 hiện tại từ chối core 23 trước khi ghi. Cần một publisher và runtime tích hợp cả hai nhánh, giữ quy tắc thương mại mới, kiểm khóa A1, RLS và restore rồi mới mở writer. [Diễn tập hai thứ tự và lệnh tái lập](C2-A1-PUBLISHER-ORDER.md) · [Kết quả PostgreSQL native](publisher-order-v22-v23.json). Rollback từng module dựa vào bản sao trước nâng cấp đã thử restore, giữ bản sau nâng để đối soát.
- **AIRC** · [#28](https://github.com/datnv41001/ai-company/pull/28) có 20 invocation local trên holdout tổng hợp. Xem matrix, receipt và cách tái lập tại PR. Chưa đạt ngưỡng cho hội đồng đọc repository hay tự động đánh giá chất lượng thương mại.

Commercial GA **NO-GO**. Pilot dùng dữ liệu tổng hợp, xuất bản và chi tiền bên ngoài vẫn đóng.

