# Kỹ năng Marketing và bản giao theo người đọc

Các bản WF-03 `research-strategy-draft@3` và WF-13 `landing-seo-draft@6` dùng thư viện kỹ năng khi xử lý manifest v2. Định nghĩa nằm trong các tệp JSON ở `catalog/marketing-skills/`. Mỗi tệp ghi đầu vào, phương pháp, loại khách hàng, thẻ nguồn, ví dụ đúng/sai, schema đầu ra, rubric và phạm vi kiểm thử.

| Kỹ năng v1 | Vai trò thực thi | Quyết định cần giúp người dùng đưa ra |
| --- | --- | --- |
| market-research | Research | Đặt một câu hỏi về lần mua gần nhất và nói rõ cần thu thêm chứng cứ gì. |
| icp-segmentation | Research | Xác định người ra quyết định và vấn đề mua hàng trong đúng thị trường. |
| positioning-value | Strategy | Chọn thuộc tính có căn cứ và giải thích nó giúp khách quyết định như thế nào. |
| campaign-channel | Strategy | Chọn thông điệp thử trên kênh đã duyệt, mô tả giả thuyết và phép so sánh. |
| kpi-measurement | Strategy | Xác định sự kiện, kỳ đo và cách đếm tránh trùng. |
| landing-conversion | Content | Viết tiêu đề, giá trị, lợi ích có nguồn và bước tiếp theo cho người mua. |
| search-intent-seo | SEO | Viết tiêu đề SEO, mô tả và ý định tìm kiếm khớp với nội dung trang. |

Một lượt gọi role có thể xử lý nhiều kỹ năng. Khi đóng gói, publisher ghi từng định nghĩa theo `(marketing_skill, id, version)` trong cùng bảng `amc_ops.registry_versions`. Cả workflow manifest và từng role contract ghim các phiên bản của mình. Adapter dựng prompt từ phương pháp và rubric, dựng schema từ hợp đồng từng kỹ năng, rồi kiểm tra các trường trả về và handle nguồn. Các ví dụ giúp người biên tập thiết kế ca hồi quy. Rubric chuyên môn cần được chấm bằng nội dung thật.

## Bản giao và quyền đọc

Trong **Đội ngũ AI → Điều phối Marketing AI**, chọn **Xem kết quả và chi phí** trên lần chạy @3 hoặc @6. Mở từng phần trong **Tài liệu Marketing của lần chạy** để đọc nghiên cứu, quyết định chiến lược, nội dung trang, SEO, nguồn, phép đo hoặc bản xem trước. API nhân sự `GET /api/tenants/{tenant_id}/workforce/runs/{rid}` trả cùng bảy phần trong `marketing_artifacts.sections`. Khi công việc chưa tạo tài liệu, bản xem trước ở trạng thái chờ.

Trong **Bản xem trước cho khách**, bản làm việc hiện tại mang revision và digest của lần lưu mới nhất. Mở **Xem bản khi AI tạo** để đối chiếu với nội dung từ checkpoint đầu tiên của bản giao. Kiểm tra QA từng nhận định gắn với tiêu đề và nội dung của lần lưu hiện tại. Các mục dành cho nhân sự vẫn là đề xuất cần biên tập. Danh sách trường cần biên tập ghi các trường rỗng, nội dung trùng nhau và trường bị giữ lại khỏi phần dành cho khách.

Người làm việc nội bộ đọc bảy phần qua `app.c3_assets.artifacts(workflow, projection, checkpoints)`. Research có câu hỏi, phân khúc, giả thuyết và dữ liệu thiếu. Strategy có định vị, lý do, kênh và giả thuyết thử. Measurement có KPI được duyệt, hành động đo và quy tắc đếm. WF-13 có nội dung trang đích và metadata SEO riêng. Evidence giữ câu được phép công bố và các handle role đã viện dẫn; trạng thái `source_handles_only` chờ đối chiếu từng nhận định ở Evidence Gate. Phần do workflow kia đảm trách có thể để rỗng.

Preview ban đầu của WF-03 chỉ chiếu các dữ kiện sản phẩm cho phép khách xem. Người duyệt chiến lược cần mở Research, Strategy và Measurement. Với WF-13, preview ghép nội dung hướng tới người mua với giá và điều kiện đã duyệt. Những sửa đổi sau đó dùng tiêu đề và nội dung trên revision hiện tại của deliverable. Snapshot khách lưu đúng revision đã được duyệt.

Director và các role nội bộ nhận brief, quy tắc thương hiệu và nguồn đã ghim. Để chuyển yêu cầu như “viết ngắn gọn” sang Content hoặc SEO, adapter chỉ gửi gợi ý biên tập từ tập từ vựng cố định. Yêu cầu tự do ngoài tập đó cần người biên tập đối chiếu. Nội dung gốc hợp lệ của từng lần thực thi nằm trong `raw_reply` của checkpoint nội bộ. Editor có thể so phần bị giữ lại với preview. Nhật ký lần gọi thất bại tiếp tục dùng cơ chế hiện có.

## Kiểm tra giá và ngôn ngữ

Nguồn và thị trường phải phê duyệt đúng locale. Vi-VN ghi `210.000 VND / 1 m²`; en-US dùng `1,234.56 USD / 1 kg`. Ngữ cảnh Gốm Bắc bao gồm đơn tối thiểu 50 m², địa bàn, thuế, vận chuyển và thi công. Với AN-1, hãy phê duyệt đơn vị `machine` để thể hiện giá theo máy. Học phí theo người dùng `participant`. Tổng số tiền tính theo minor unit của tiền tệ. Khi đơn vị cũ chỉ là `service`, hoặc locale nằm ngoài vi-VN/en-US, readiness yêu cầu bản tri thức phù hợp. Không thay thế một cách ngầm định phần đơn vị hay điều kiện của nguồn cũ.

## Phát hành, kiểm tra lại và quay về phiên bản trước

1. Chạy `python scripts/build_c3_releases.py`. So diff của hai manifest mới cùng skill JSON và kiểm hai tệp lịch sử `research-strategy-v2.json`, `landing-seo-v5.json` với Git.
2. Chạy `python -m pytest -q tests/test_c3_skill_library.py tests/test_c3_editorial.py`. Trên PostgreSQL thử nghiệm, đặt `AMC_TEST_PG=1` và cấu hình DSN publisher/runtime riêng theo HANDOFF. Ca publisher kiểm cả bảy dòng bất biến và việc chạy lặp.
3. Sau review runtime, trên DB tổng hợp chạy `python migrations/apply.py --publish-registry catalog/research-strategy-v3.json` và `python migrations/apply.py --publish-registry catalog/landing-seo-v6.json`. Kích hoạt đúng workflow và các role ở campaign đã chọn. Lưu manifest digest, runtime fingerprint, bản ghi run/usage và kết quả QA.
4. Nếu cần quay lại, disable bản mới cho công việc tiếp theo và kích hoạt lại @2 hoặc @5 tại đúng campaign. Khi thay đổi phương pháp, thêm version mới và giữ bộ adapter, schema, định nghĩa, digest cũ để đọc lại hồ sơ đã đóng. DB từ chối ghi đè một phiên bản đã xuất bản.

## Nguồn để đối chiếu phương pháp

Thẻ K-01 ghi nhận cách Wecommit tổ chức lại ghi chú và lần về nguồn qua bài viết đi kèm video. K-05 dùng tư liệu về phỏng vấn và lựa chọn cơ hội. K-06 đến K-08 dùng hướng dẫn viết cho người đọc và thiết kế phép đo. Các thẻ ghi rõ nội dung thực sự được đọc và giới hạn áp dụng. [Sổ nguồn](research/SOURCE_REGISTRY.md) · [Thẻ kiến thức](research/KNOWLEDGE_CARDS.md)

Google mô tả nội dung thẻ title như một tín hiệu để tạo title link và có thể chọn snippet từ nội dung trang. Các định nghĩa sự kiện trong tài liệu GA4 giúp phân biệt lead với kết quả giao dịch. Các hướng dẫn này được đọc trực tiếp dưới dạng tài liệu công khai. [Title links](https://developers.google.com/search/docs/appearance/title-link) · [Snippets](https://developers.google.com/search/docs/appearance/snippet) · [Recommended events](https://developers.google.com/analytics/devguides/collection/ga4/reference/events)
