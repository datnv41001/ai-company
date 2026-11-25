# Marketing từ Business Knowledge

WF-03/research-strategy-draft@2 tạo đề xuất chiến lược từ tài liệu nội bộ. WF-13/landing-seo-draft@5 tạo nội dung trang đích và SEO để biên tập. Cả hai bắt đầu bằng brief nội bộ C2, một brief chiến dịch mà khách đã gửi và các revision nghiệp vụ được duyệt. Bản phát hành dùng PostgreSQL, worker pool và model local. Commercial GA remains NO-GO.

## Khởi động trên máy mới

Từ root của checkout có hai tệp catalog bên dưới, làm theo phần Docker Compose, cấu hình đăng ký tài khoản kiểm thử, pool và model local trong [HANDOFF](../../HANDOFF.md). Publish từng release bằng identity migration. Lệnh dưới đây hỗ trợ chạy lại với cùng nội dung.

```bash
docker compose up -d --build
docker compose run --rm migrate python migrations/apply.py --publish-registry catalog/research-strategy-v2.json
docker compose run --rm migrate python migrations/apply.py --publish-registry catalog/landing-seo-v5.json
```

1. Trong Hồ sơ doanh nghiệp, lưu bốn trường chung và ít nhất một revision thương hiệu. Tạo mục tiêu cấp công ty, nối mục tiêu thương hiệu và mục tiêu của đúng chiến dịch. Chọn KPI đã duyệt, có nguồn định nghĩa. Tạo sản phẩm hoặc biến thể, thị trường, audience và nhận định công khai kèm nguồn. Với nhận định cần chuyên môn, người phê duyệt khác tác giả phải có ủy quyền còn hiệu lực.
2. Trong Brief nháp, ghim sản phẩm, audience và mục tiêu chiến dịch rồi lưu. Trong AI Workforce, mở yêu cầu cho người nhận có quyền. Người nhận đăng nhập và gửi brief chiến dịch.
3. Mở lại brief nội bộ. Trong **Chuẩn bị Marketing từ brief này**, chọn WF-03 hoặc WF-13, brief chiến dịch, thị trường, KPI và nhận định. Nhập đầy đủ phạm vi, gồm tiền tệ và số lượng khi chọn giá. **Kiểm tra mức sẵn sàng** hiển thị dữ liệu cần bổ sung. Với nguồn chứng minh hạn chế, quản trị viên phụ trách cần thực hiện bước này.
4. Quản trị viên bật quy trình cho chiến dịch. **Xếp việc cho AI** ghim manifest và gửi yêu cầu hiện tại với ngân sách model bằng 0. Dùng ID chạy trong AI Workforce để xem công việc từng vai trò và bản giao. Trong màn hình duyệt bản giao, người QA độc lập mở và duyệt đúng revision trước khi người có quyền chia sẻ cho khách.

## Authority và lịch sử

Trong brief vừa xếp việc hoặc phần chi tiết run của AI Workforce, quản trị viên chọn **Đối chiếu mã nguồn với tài liệu gốc** để mở bảng F1… → revision nguồn, digest và locator đã ghim. Dữ liệu được tải theo quyền hiện tại và đóng lại khi rời tab. Bảng riêng này vẫn đọc được khi nguồn hết hiệu lực để đối chiếu lịch sử. Những lần sử dụng mới luôn kiểm tra lại căn cứ.

C3 dùng revision của bốn trường hồ sơ công ty và override thương hiệu. Bản kế tiếp cần hợp đồng riêng cho revision hướng dẫn từ vựng, giọng thương hiệu và giới hạn công bố, kèm phê duyệt trường nào được đưa vào prompt từng vai trò.

Manifest bất biến lưu canonical JSON, SHA-256, trường profile và C2 brief, đúng chiến dịch/brief và thế hệ thay đổi của chúng, chuỗi mục tiêu, revision sản phẩm/biến thể, market, audience, KPI và toàn bộ dependency của claim. Private SQL rows kế thừa mức bảo mật cao nhất. GET /marketing/manifests/{id} trả lại projection gốc cho nhân sự có quyền. Các đường C1 preview/authorize giữ nguyên giao thức riêng.

Worker nhận tên sản phẩm/SKU, bối cảnh được phép, câu đã duyệt, điều kiện và mã F1… theo vai trò. Tài liệu nguồn, trích dẫn hạn chế, tên nhà cung cấp, locator, người duyệt và khóa giao dịch ở phía server. Audience là giả thuyết cần nghiên cứu thêm. KPI là định nghĩa đo lường. Nhân viên phải đối chiếu các nhận định do model viết trước khi chia sẻ.

Điểm xếp việc, QA và chia sẻ lấy khóa trong cùng transaction với hiệu ứng thật. Chúng đọc lại trạng thái khách/brand/campaign, scope người nhận, nguồn, điều kiện giá và chuỗi mục tiêu. Duyệt và chia sẻ ghi cả revision và digest của bản giao. Đổi profile hoặc nguồn sau khi đã tạo manifest yêu cầu chuẩn bị lại trước hiệu ứng mới. Đọc quyết định hoặc bản giao cũ không tạo việc mới. Một run cho mỗi brief khách gửi; nếu cần chuẩn bị lại sau khi run đã tạo, dùng một brief mới.

Quyền và hiệu lực của nguồn áp dụng cho toàn bộ material đã ghim ngay cả khi người biên tập bỏ một câu. Quyết định QA vẫn là trách nhiệm của con người. Các bản đã chia sẻ giữ nguyên nội dung và lịch sử.

## Kiểm tra, đánh giá, rollback

```bash
python scripts/build_c3_releases.py
python -m ruff check .
python -m pytest -q tests/test_c3_authority.py tests/test_c3_races.py tests/test_c3_operational_guards.py
```

Dùng quy trình CI PostgreSQL cho các test đánh dấu PG. Job Compose publish hai release và chạy tests/browser_c3.py ở desktop 1280 px và mobile 390 px cùng bộ browser hiện có. Hai tệp catalog, mã adapter và registry-runtime.lock.json là một đơn vị triển khai. Thay đổi mã runtime cần kiểm định và phê duyệt đúng fingerprint. Bộ thử schema cũ và các bản catalog trước tiếp tục chạy trên CI.

Kiểm tra chất lượng thực tế dùng bộ ca tổng hợp, đầu ra WF-03/WF-13 và receipt invocation cho từng lượt tại [bộ so sánh C3](../../tests/evaluation/c3/). Ghi riêng kết quả cấu trúc và kết quả Marketing, mức sửa của con người cần pilot riêng.

Để dừng tiếp nhận việc mới, quản trị viên disable release trong campaign. Dùng revoke nếu cần dừng việc đang chạy theo quy trình vận hành registry. Dùng image đã kiểm định và release cũ cho brief mới. Giữ database v22 và bản ghi sau C3 để truy vết. Kiểm thử C3 sử dụng dữ liệu giả lập, mọi hoạt động chia sẻ đều là bản giao nội bộ trong lab.

## Đọc bằng chứng nghiệm thu

| Ca kiểm | Cách quan sát |
| --- | --- |
| Rút nguồn trước và sau từng lệnh queue, QA, share | Sáu giao dịch tranh chấp dùng `pg_blocking_pids` tại COMMIT, đối chiếu số receipt đã ghi với kết quả API. |
| Mất phản hồi và worker dừng sau khi nhận việc | Hai yêu cầu xếp việc đồng thời cùng trả một run. Lease cũ hết hạn, worker tiếp quản. Kiểm số bản giao, receipt và từng bút toán. |
| Thiếu điều kiện sử dụng | Sai công ty, SKU, biến thể, campaign, locale, stock bị tranh chấp hoặc rút ủy quyền làm dừng tác vụ. Ca hết hạn báo giá dịch riêng thời điểm đánh giá, giữ nguyên dữ liệu giá và thời hạn các nguồn khác. |
| Phiên bản QA và bản giao | Gửi cả `expected_qa_revision` và `expected_content_digest` khi chia sẻ tài sản C3. Gửi lại sau khi sửa nhận 412; gửi lại sau khi mất ACK cho đúng bản vẫn lấy cùng bản giao. |
| Thao tác thực tế trong browser | Artifact `knowledge-center-journeys-*/marketing-workflows/` trong job Compose có hai kích thước Chromium, trạng thái đã sẵn sàng, số run sau khi xếp việc và ảnh tại từng bước. |
| Phiên thiết bị | Ba ca `revoked_device` yêu cầu API phiên của A1. Trên core v22 chúng được đánh dấu skip. Bản tích hợp thử trên PostgreSQL giữa C3 và [PR #36](https://github.com/datnv41001/ai-company/pull/36) (`c9ae22ba`, core v24) đã xác nhận logout chặn cả ba điểm, không phát sinh receipt. |

Job PostgreSQL trong [PR C3](https://github.com/datnv41001/ai-company/pull/37) chạy bằng role ứng dụng hạn chế; identity migration kiểm tra kết quả cuối và tạo/xóa database tổng hợp. Kiểm registry cũ và mới trong cùng database trước khi đánh giá nâng cấp. Ảnh browser native dùng Chromium 157.0.8103.52, PostgreSQL native 16.16; job Compose dùng image PostgreSQL 16.6.
