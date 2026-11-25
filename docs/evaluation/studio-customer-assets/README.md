# Marketing Studio · bản giao khách đã ký

Tư vấn chiến lược và biên tập viên agency có thể soạn bộ tài liệu từ brief đã duyệt, chuyển từng phần cho QA rồi bàn giao đúng phiên bản cho khách. Sales có thể sử dụng phương án RFQ và phương pháp đo. Nhân viên web nhận được nội dung trang cùng metadata SEO. Đây là hai nhiệm vụ mẫu trên dữ liệu tổng hợp.

| Nhiệm vụ | Các tài sản khách nhận | Bằng chứng tạo qua API |
| --- | --- | --- |
| WF-03 research-strategy-draft@3 | Chiến lược chọn đối tượng, cách triển khai trên kênh, điều kiện ra quyết định tiếp theo và kế hoạch kiểm định giả thuyết | [Snapshot và biên nhận chiến lược](marketing_strategy.json) |
| WF-13 landing-seo-draft@6 | Nội dung trang có điều kiện thương mại và CTA trong brief. SEO gồm tiêu đề trang, mô tả, ý định tìm kiếm | [Snapshot và biên nhận trang đích](landing_page.json) |

## Phạm vi và hợp đồng

Trong **Phê duyệt → Soạn và bàn giao cho khách → Biên tập tài liệu Marketing**, chọn **Soạn bộ tài liệu giao khách**. WF-03 giữ ba phần nội bộ và thêm hai phần riêng cho khách. Đề xuất chiến lược khách dùng sản phẩm, đối tượng, kênh và hành động được phép trong brief. Luồng báo giá ưu tiên yêu cầu đủ thông tin cho Sales, luồng chọn mẫu đối soát lựa chọn với yêu cầu ban đầu. WF-13 dùng đúng những trường copy và SEO được liệt kê. Người biên tập có thể xem thử một đề xuất thay thế cho mỗi trường, quyết định có áp dụng, rồi lưu. Kiểm tra nguồn, sửa câu và ký duyệt vẫn là công việc của người có thẩm quyền.

API `GET .../deliverables/{id}/studio` cung cấp `customer_edition` với phiên bản, giới hạn trường, nhãn và nhóm đề xuất. `PATCH .../studio` nhận toàn bộ `groups`, `expected_revision` và `delivery_version="amc.customer-marketing-assets/1"`. Lưu làm mất hiệu lực mọi chữ ký của lần lưu trước. Trước chia sẻ, mọi phần phải đủ bằng chứng và được ký độc lập, có quyết định QA cuối còn hiệu lực. Với brief có hành động người mua đã ghim, API từ chối chia sẻ bản làm việc chưa chuyển sang hợp đồng này. Brief lịch sử chưa có lựa chọn đó tiếp tục dùng giao thức cũ. Sau khi có edition, bản sửa phải giữ hợp đồng hoặc tạo nhiệm vụ mới. Nhiệm vụ nội bộ tiếp tục chịu giới hạn chia sẻ của nguồn.

Snapshot portal tiếp tục dùng tiêu đề và thân văn bản bất biến, SHA-256, số phiên bản và quyền tenant/client/brand/campaign. Biên nhận QA và chia sẻ lưu riêng cấu trúc tài sản, mã băm trường theo nhóm, chữ ký nhóm, phân loại và handle của từng nhận định, revision nguồn và digest. Phần nội bộ, locator nguồn, phiếu chuyên gia và ghi chú QA chỉ được truy xuất theo quyền nhân sự. Bản giao có đủ chữ ký vẫn cần một thao tác chia sẻ có thẩm quyền. Khi có lỗi phải sửa, khách đã nhận vẫn đọc được đúng bản cũ.

## Tái lập

Tại gốc checkout, cài bộ phụ thuộc như CI. Chạy các lệnh sau với Python của môi trường dự án. Đặt đường dẫn Chromium bằng `AMC_BROWSER_EXECUTABLE` nếu dùng Chrome đã cài. Linux CI dùng Chromium của Playwright.

```bash
python -m ruff check app tests migrations scripts
python -m pytest -q tests/test_customer_assets.py tests/test_c3_studio.py
AMC_CUSTOMER_EDITION_EVIDENCE=/tmp/amc-editions python -m pytest -q tests/test_customer_assets.py
AMC_STUDIO_EVIDENCE=/tmp/amc-studio python -m pytest -q tests/browser_customer_assets.py tests/browser_marketing_studio.py
```

Trên PowerShell, đặt biến trước lệnh, ví dụ `$env:AMC_STUDIO_EVIDENCE = '.local/studio-evidence'`. Bài API dựng tài khoản và nguồn qua API, gắn một run hoàn tất giả lập vào database SQLite dùng riêng rồi thực hiện đầy đủ lưu, gửi, ký, QA, chia sẻ và đọc như khách. Hai tệp JSON mẫu chứa cả bằng chứng riêng của nhân sự để người phát triển đối chiếu. Tại portal, khách chỉ đọc các trường của snapshot nằm trong grant. Browser kiểm tra giao diện thực bằng Chromium ở 1280, 820, 390 CSS px, sáng/tối, thao tác bàn phím và reflow. [Ảnh Studio và portal theo thiết bị](screens/sessions.json)

[Studio desktop](screens/studio-1280.png) · [Studio tablet tối](screens/studio-820-dark.png) · [Studio mobile](screens/studio-390.png) · [Portal desktop tối](screens/portal-1280-dark.png) · [Portal tablet](screens/portal-820.png) · [Portal mobile tối](screens/portal-390-dark.png)

## Phương pháp Marketing đã áp dụng

- Google Analytics mô tả riêng sự kiện gửi thông tin và bước một lead đạt tiêu chí. Trong playbook báo giá, hệ thống đề xuất so yêu cầu với bước Sales có đủ thông tin để báo giá, dùng cùng nhóm lượt truy cập. Đây là yêu cầu đo nội bộ. Phải lắp nguồn và đối soát trước khi báo số chuyển đổi hoặc doanh thu. Đã đọc mục *For lead generation* ngày 25/11/2026. [Tài liệu chính thức của Google Analytics](https://support.google.com/analytics/answer/9267735?hl=en)
- Google Search Central giải thích Google chủ yếu tạo snippet từ nội dung trang và có thể chọn meta description. Nghiệm thu WF-13 bàn giao cả nội dung trang và trường mô tả để biên tập viên đối chiếu độ phù hợp. Xếp hạng và snippet thực tế cần đo sau khi xuất bản có phép. Đã đọc *How snippets are created* và *Create unique descriptions for each page*, ngày 25/11/2026. [Tài liệu chính thức của Google Search Central](https://developers.google.com/search/docs/appearance/snippet)

**Giới hạn bằng chứng.** Hai nhiệm vụ kỹ thuật tạo bốn loại tài sản, đều dùng tài khoản và quy trình phê duyệt tổng hợp. Không phát sinh lượt gọi model mới trong phép thử này. Lịch sử thành bại của hai workflow và kết quả pilot mù nằm trong [hồ sơ đối chứng](../c3-product-v2/RESULTS.md). Chưa có chuyên viên Marketing chấm lần đầu, thời gian sửa/QA, chi phí mỗi bản được chuyên viên chấp nhận hoặc mức sẵn sàng trả tiền. Commercial GA vẫn NO-GO.

**Câu hỏi cho reviewer.** Hãy thử thêm câu hứa thương mại vào một trường chiến lược khách, thay lợi ích bằng một câu thiếu điều kiện hoặc mở bản giao bằng tài khoản khách thứ hai. Kiểm tra đúng điểm từ chối. Đối chiếu SHA-256 của snapshot gốc sau một lượt sửa và so từng trường với biên nhận của nhóm tương ứng.
