# Mục tiêu chung của doanh nghiệp, thương hiệu và chiến dịch

Nhân sự agency chọn khách hàng cùng một thương hiệu tại Hồ sơ doanh nghiệp, mở Danh mục Marketing và chọn **Mục tiêu chung doanh nghiệp**. Điền tên, người phụ trách và lưu nháp. Admin hoặc owner ghi lý do để duyệt. Mục tiêu chung thuộc cặp tenant–client. Khi đổi sang thương hiệu thứ hai của cùng khách hàng, nhân sự có thể chọn lại cùng phiên bản đã duyệt theo tên.

## Tạo cây mục tiêu

- Với cấp **Thương hiệu**, chọn đúng một mục tiêu cha. Mục **Mục tiêu chung làm cha** tra bản đã duyệt của công ty. Trường cha trong thương hiệu hỗ trợ mục tiêu công ty cục bộ đã tạo theo hợp đồng C1.
- Với cấp **Chiến dịch**, chọn chiến dịch của thương hiệu đang mở và một mục tiêu cha cấp thương hiệu. Khi chỉnh sửa, server giữ nguyên cấp và danh tính chiến dịch trong cùng một dòng lịch sử.
- Khi lập KPI, chọn một mục tiêu của thương hiệu hoặc mục tiêu chung của công ty. KPI có thể lưu nháp với các số liệu còn thiếu. Quyết định duyệt KPI tiếp tục yêu cầu chứng cứ C1.
- Mục tiêu chung mới được lưu thành revision dưới client. Quyết định có actor, lý do, digest và sequence. Bản nháp sửa tiếp chưa thay thế thẩm quyền của bản trước. Bản mới đã duyệt thay thế thẩm quyền cũ cho quyết định tiếp theo. Việc thu hồi không phục hồi bản cũ. Tra lịch sử bằng ID bản gốc qua `GET /api/tenants/{t}/clients/{c}/company-objectives/{revision_id}/events`.
- `GET …/company-objectives?approved_only=true&q=…` trả lựa chọn theo client và quyền của người gọi. `POST …/company-objectives` nhận tên, phụ trách, key và expected_revision. Gửi quyết định qua `POST …/{revision_id}/events` với key, expected_digest và expected_sequence. Có thể khôi phục kết quả ghi bằng `GET …/commands/{key}` của đúng actor.

## Chuyển máy và nâng cấp

Dùng cùng checkout cho API và publisher. Sao lưu database bằng công cụ PostgreSQL đang vận hành, chạy `docker compose run --rm migrate` theo cấu hình repository và khởi động API sau khi publisher thành công. Kiểm tra `SELECT version FROM amc_business.versions ORDER BY version` cho kết quả 1, 2, 3. Cặp bảng `business_company_objectives` và `business_company_objective_edges` nằm trong backup. App dùng role `amc_runtime`; publisher dùng owner riêng. Gặp phiên bản module lạ, dừng và kiểm tra các commit publisher trước khi khởi động. Để rollback có dữ liệu, khôi phục bản sao trước nâng cấp vào database mới và khởi động checkout cũ với database đó.

Module v3 độc lập với core v22. Nhánh A1 giữ số migration core 023. Bản tích hợp dựa trên #31 ở `0ef8719` và giữ kiểm tra digest riêng của Claim Desk. Khi tích hợp A1, giữ kiểm tra module [1,2,3], publisher idempotent của từng module và kiểm tra digest helper Claim Desk. Những mục tiêu ghi tại C1 với level=company thuộc một thương hiệu cụ thể. Chuyển sang chia sẻ bằng cách tạo và duyệt phiên bản công ty riêng, rồi lập revision mới của mục tiêu con để giữ ID và snapshot cũ cho lần tra cứu tiếp theo.

Trong brief làm việc, chọn mục tiêu cấp thương hiệu hoặc chiến dịch. Brief ghim ID, digest và trạng thái lúc lưu của đúng mục tiêu đã chọn. Mục tiêu cha chung truy được từ revision thương hiệu. Hai lần chọn nhãn trùng tên ở hai khách hàng vẫn đi qua phạm vi client/brand cụ thể.

## Kiểm thử

Ở DB thử, chạy `python -m pytest -q tests/test_company_objectives.py tests/test_marketing_catalog.py tests/test_business_workspace.py` như job PostgreSQL. `python tests/check_workspace_upgrade.py` cần PostgreSQL loopback rỗng có tên bắt đầu bằng `amc_test`, quyền publisher và Git history. Test dùng đúng publisher v22, v1, v2 và chạy v3 hai lần trên dữ liệu tổng hợp. Job browser từ CI chạy `python tests/browser_objectives.py` trên desktop 1280px và mobile 390px, kiểm tra hai thương hiệu cùng liên kết một mục tiêu chung và quyết định của chiến dịch. Các bộ test đều có thể chạy lại bằng môi trường trong CI.

C2.5 lưu mục tiêu và KPI nội bộ. Chỉ tiêu thực tế do nhân sự nhập cùng căn cứ. Import số liệu tự động và adapter WF-03/WF-13 thuộc các increment tiếp theo. Commercial GA vẫn NO-GO.
