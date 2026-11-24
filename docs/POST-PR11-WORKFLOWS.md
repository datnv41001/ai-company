# Hai đề xuất sau PR #11

Trạng thái ngày 24/11/2026 là thiết kế để phản biện. Mỗi đề xuất có thể triển khai và rút bằng một PR riêng. Điểm xuất phát là schema v14 và bản nội bộ `576b8179`. Quy trình landing hiện có định danh và hợp đồng riêng. [Nghiệm thu và cách tái lập](../HANDOFF.md) · [Ma trận phạm vi V1](PR9-TRACEABILITY.md).

## PR cho tiểu quy trình WF-03 Research → Strategy

Một marketing lead cần chuyển tài liệu đã cấp cho campaign thành bản đề xuất chiến lược có thể kiểm tra ngược đến từng nguồn. Đề xuất dùng định danh mới `WF-03/research-strategy-draft@1`, opt-in theo campaign. Chủ workflow duyệt rubric nghiệp vụ và brief tổng hợp trước khi mở intake thử.

| Bước | Đầu ra và cách kiểm tra |
| --- | --- |
| Director | Chốt DAG gồm Research → Strategy → join. Manifest quy định các skill bắt buộc, terminal, adapter, policy, loại đầu ra, giới hạn lượt, timeout và ngân sách. Trình kiểm tra manifest và compiler cần nhận diện rõ workflow mới. Giữ mẫu hợp đồng và test cho tất cả phiên bản WF-13 hiện tại. |
| Research | Ghi riêng quan sát được, giả thuyết về người mua và khoảng trống. Mỗi quan sát có ID nguồn và đoạn trích trong bộ tài liệu đã ghim đúng tenant/campaign. Khi thiếu dữ kiện, xuất khoảng trống và câu hỏi thu thập. Khi ID nguồn sai, từ chối report theo chính sách thử lại của node. |
| Strategy | Đọc checkpoint Research qua cạnh trực tiếp cùng run và cùng plan revision. Ghi ID node, digest, nguồn kế thừa, đối tượng, định vị, khuyến nghị và giả định. Mỗi KPI có đơn vị, khoảng thời gian, phương pháp và nguồn đo. Với tỷ lệ, ghi rõ tử số và mẫu số. Mức cơ sở hoặc mục tiêu thiếu căn cứ được đánh dấu cần xác nhận. |
| Join, QA và giao bản | Join tạo bản đề xuất từ đúng checkpoint Strategy. Người QA kiểm tra nguồn và cách đo trên revision/digest đang xem. Khách mẫu quyết định trên snapshot đã chia sẻ. Mọi lần sửa tạo bằng chứng QA cho bản sửa. |

**Quyền và chi phí.** Backend xác nhận grant của actor theo tenant, campaign và skill trước khi phát công việc. Với grant bị thu hồi giữa hai bước, áp dụng đúng chế độ ngừng cấp mới hoặc thu hồi đang chạy theo hợp đồng registry. Chặn report muộn theo lease và generation. Dùng hợp đồng reserve, settle và reconcile hiện có cho mỗi attempt. Các nguồn giả lập, model local và giới hạn retry cho phép tái lập chi phí bằng Docker.

**Nghiệm thu.** Chạy hai brief đối chứng, một brief đủ nguồn và một brief thiếu hoặc có nguồn phủ định. Thử tráo nguồn giữa hai khách cùng agency và giữa hai agency. Dùng hai checkpoint Research để kiểm tra Strategy chỉ đọc đúng parent. Thử thu hồi giữa checkpoint và offer kế tiếp, report gửi lại, retry hết hạn và hold đã gửi. Nghiệm thu Qwen local phải xuất manifest/plan digest, output digest theo node, token, usage, đối soát và một snapshot qua QA người duyệt. Chạy lại đường WF-13 cũ và đối chiếu ledger, quyết định và snapshot trước/sau.

**Triển khai thử và rút.** Công bố phiên bản mới trên DB tổng hợp sau khi xác minh fingerprint ở từng replica. Cấp grant giới hạn một campaign thử. Khi cần rút, ngừng cấp intake cho WF-03, giữ adapter đến khi đã tiêu thụ report và đối soát hết hold. Nếu phải bổ sung schema, PR triển khai cần migration additive, nâng lặp được trên DB có dữ liệu và chứng minh cách phục hồi. Chủ nghiệp vụ quyết định mức đạt cho rubric trước khi căn cứ vào điểm để mở rộng.

## PR cho chẩn đoán nguyên nhân node chờ

Người điều hành cần biết node hay report nào đang chờ, điều kiện nào phải thay đổi và số liệu được ghi lúc nào. Đề xuất một truy vấn chỉ đọc theo tenant/campaign/run/revision/node, dùng cùng điều kiện xét cấp offer với dispatcher. Trả `observed_at`, giai đoạn, danh sách `wait_reasons`, thời điểm có thể thử lại nếu biết và bằng chứng tối thiểu của từng lý do. Một node có thể gặp nhiều lý do đồng thời.

| Mã dự kiến | Căn cứ và thao tác có ý nghĩa |
| --- | --- |
| `dependency_pending`, `retry_backoff` | Đọc cạnh và checkpoint đúng revision hoặc mốc retry của node. Hiển thị predecessor hoặc thời điểm thử lại. |
| `adapter_unavailable`, `report_waiting_adapter` | Phân biệt node chưa được cấp việc với report đã nộp cần dispatcher tương thích. So cặp adapter/digest đã ghim với khai báo runtime còn hiệu lực trong đúng pool. Hiển thị phiên bản cần khôi phục. |
| `worker_unavailable`, `worker_busy` | Xét worker được cấp route cho campaign, capability, heartbeat và lease đang hiệu lực. Phân biệt chưa có worker hợp lệ với worker hợp lệ đang thực hiện việc khác. |
| `capacity_full`, `budget_insufficient` | Đọc giới hạn đồng thời của agency và số slot đang dùng. Đối chiếu mức cap cho attempt với ngân sách còn khả dụng của kỳ theo sổ cái, có tính các khoản giữ. Cung cấp số liệu ngân sách theo quyền tài chính của actor. |
| `telemetry_unknown` | Replica cũ chưa báo capability, dữ liệu hết hạn hoặc độ phủ pool chưa đủ. Hiển thị tuổi bản ghi và phạm vi quan sát. Chỉ kết luận thiếu runtime khi có đủ telemetry cho pool liên quan. |

**Thu thập và phân quyền.** Dispatcher và worker báo capability bằng danh tính service đã xác thực, gắn replica, pool, route, thời điểm do DB ghi và fingerprint đã kiểm chứng. Công bố chu kỳ heartbeat, TTL và cách phân biệt worker bận còn lease. Chỉ trả tên cần thiết cho vận hành trong tenant được phép. Client reviewer chỉ truy cập bản giao theo quyền hiện hành. Đọc chẩn đoán không cấp lease, tạo hold, ghi usage hoặc xử lý report. Mọi thay đổi capacity hay ngân sách vẫn dùng API vận hành hiện có.

**Nghiệm thu và rút.** Dùng đồng hồ điều khiển được để thử heartbeat cũ/mới, adapter sai digest, report về khi adapter tương thích vừa rời pool, worker bận, hết capacity cùng lúc với thiếu tiền và hai tenant dùng chung pool. So kết quả với quyết định admission thực tế, kiểm tra snapshot nhất quán khi lease đổi và bảo đảm đọc lặp không đổi ledger. Xác nhận nhân sự đúng campaign thấy lý do đủ xử lý, khách A/B không thấy telemetry hay số dư của nhau. Mở chức năng đọc cho một pool dev, so thời gian chờ và tỷ lệ nguyên nhân chưa xác định trước khi tăng quy mô. Có thể tắt màn hình và truy vấn chẩn đoán độc lập với dispatcher.
