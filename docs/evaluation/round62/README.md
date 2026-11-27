# Vòng #62 · Phiếu đối chiếu yêu cầu báo giá

## 1. Base đã nghiệm thu

PR #61 đã merge vào main ở `2daa715dde0d13be227454822e32cabe6fd2f241`. Tree tài liệu là `4a82f3402f01e2e140c3107bd6450986686b339f`; tree sản phẩm của PR #60 là `1c40c678b0556cfa512b0a5f59c4eef457c60ef6`. #61 không chạy CI mới. AMC-R61-01 đã đối chiếu CRC và băm riêng archive ZIP 14.708 byte và XML giải nén 92.709 byte. 686 ca trong XML thuộc CI main #60, gồm hai skip. [Hai digest, parent và trial](MAIN-61.json)

## 2. Công việc của Sales

Nhân viên tiếp nhận cần biết khách yêu cầu gì, dữ kiện nào cản trở chuyển giao và ai có thể cho phép ngoại lệ. Business Desk hiện trả revision mới nhất theo quyền. SQL lấy mỗi entity một dòng hiện hành, còn reviewer chỉ nhận bốn trường. Vì vậy bản này xuất phiếu HTML và JSON ngoại tuyến từ hai fixture tổng hợp cố định. Script đọc file theo SHA-256, chạy bằng thư viện chuẩn Python, không có kết nối DB hoặc mạng. Hợp đồng `rfq-qualification/1` vẫn là đề xuất. [Business Desk](../../../app/campaign_role_desk.py) · [Projection và nguồn](../../../scripts/rfq_evidence.py)

## 3. Ba đầu ra

Tại thư mục gốc checkout, chạy `python -m scripts.rfq_card --output rfq-review` với thư mục đích mới. Mở `khe-gon.html`, `before.html` và `after.html`. Mỗi phiếu liên kết đến JSON cùng tên. So sánh theo inquiry ID, receipt ID, sequence và contract digest.

| Phiếu | Quan sát được | Hành động gợi ý |
|---|---|---|
| Khe Gọn ở receipt #60 | 1 hộp, MOQ ghi nhận 5, thiếu commercial_moq, chưa có người nhận | Chủ offer/Sales Operations xác minh điều kiện và quyền xét ngoại lệ |
| Inquiry tổng hợp riêng, revision 1 | 1 hộp, chưa đạt MOQ | Kiểm nguồn MOQ của chính inquiry này |
| Cùng inquiry đó, revision 2 | 5 hộp, đủ trường theo rule; thiếu receipt xác nhận qualification, tiếp nhận, báo giá, đơn và doanh thu | Sales Operations đối chiếu trước khi chuyển qua Desk có thẩm quyền |

[Receipt Khe Gọn theo commit](https://github.com/datnv41001/ai-company/blob/db862100aabf76641fe93fd207868c095f9027eb/docs/evaluation/round60-verification/artifacts/journey/wf08-v2/receipt.json) · [Fixture hai revision](../../../tests/fixtures/rfq_evidence/lineage.json)

## 4. Tái lập hai điểm cắt

Nguồn thứ hai dùng PostgreSQL và các writer sandbox hiện hữu để ghi visit, RFQ và CompleteRFQ. `cutoffs.revision_1` và `cutoffs.revision_2` trong fixture là hai thời điểm journal thực sự ghi nhận. Projection lọc theo recorded_at, sắp xếp theo sequence rồi kiểm liên tục revision. Lần bổ sung thiếu occurred_at riêng nên phiếu ghi “Chưa có bằng chứng”. Thời điểm tạo phiếu và thời gian có hiệu lực của policy là hai dữ kiện riêng. Một lần chạy test mới có ID và thời gian riêng.

## 5. Quyền và phạm vi

Fixture cố định có sequence 11 (visit), 12 (revision 1, 04:10:30.346121 UTC) và 13 (revision 2, 04:10:33.289134 UTC), ngày 27/11/2026. Đã kiểm 25 phép đối chiếu trên PostgreSQL. [Ma trận quyền và cách tái lập](DESK-AUTHORITY.md) · [Expected và actual](desk-authority.json)

| Người đọc hiện tại | Bằng chứng kiểm |
|---|---|
| Khách hàng A/B cùng agency | Mỗi khách thấy client record của mình; raw campaign và desk nội bộ bị ẩn. Hai campaign cùng tên, khác ID, đều có inquiry. |
| Marketing operator | Chỉ xem inbox trong campaign được cấp quyền. Truy vấn trực tiếp restricted journal qua runtime role không trả dòng RFQ. |
| Sales recipient | Cần role hiện hành và đúng assignment. Sau reassign hoặc thu hồi role, cutoff cũ không khôi phục quyền. |
| Reviewer | Inbox chỉ xuất id, plan_id, revision và state kể cả khi có thêm role. |
| Chủ thể tạo fixture | Dùng tài khoản thử trong PostgreSQL tạm để tạo tập dữ liệu tổng hợp. CLI chỉ đọc hai file đã ghim trong repository. |

API hiện hữu không phục vụ đọc lịch sử. Query thêm cutoff vào inbox vẫn cho trạng thái **hiện hành** đã lọc quyền. [Bài kiểm tra API/RLS theo phiên thực](../../../tests/test_rfq_desk_authority.py)

## 6. Phản hồi nghiệp vụ

Một yêu cầu 1 hộp cho offer có MOQ 5 chỉ xác nhận chênh lệch số lượng. Marketing có thể kiểm lại chữ trên form, khả năng khách hỏi mẫu thử và các inquiry độc lập cùng offer/revision. Chưa có lời giải thích của khách, mẫu so sánh hay quyết định đổi CTA, offer hoặc MOQ. [Nguồn, chín nhóm nghiệp vụ và phép kiểm tiếp theo](MARKET.md)

## 7. Kiểm thử và tiêu chí

| Nhóm nghiệm thu | Trục kiểm và nguồn đối chiếu |
|---|---|
| 1–2 | Receipt bất biến, nguồn, đơn vị, biên 1/5 và 5/5, trạng thái Sales độc lập |
| 3–5 | Cùng inquiry trước/sau; chặn dữ kiện đến sau cutoff; thời gian sửa chưa biết và sự kiện đến muộn |
| 6–8 | Không có dữ kiện MOQ, policy tổng hợp miễn MOQ, xung đột, thời gian hiệu lực, thu hồi nguồn và consent |
| 9 | Sai unit/scope, mất linkage, nguồn creative cần bằng chứng riêng, replay và collision |
| 10–12 | Đủ trường, quote sandbox, các mốc thương mại riêng; lưu lịch sử hủy/sửa và giá trị sandbox |
| 13–14 | PostgreSQL, hai client cùng agency/tên campaign, thu hồi role và assignment |
| 15–16 | Nhiều lần đọc có cùng dữ liệu; journal không phát sinh dòng. Giữ `intake-funnel/2` và primary null |

Chạy `python -m pytest -q tests/test_rfq_evidence.py tests/test_rfq_card_export.py`. Với DB thử đã migrate và biến CI như workflow, chạy thêm `python -m pytest -q tests/test_rfq_desk_authority.py`. Đặt `AMC_RFQ_TEST_EVIDENCE` và `AMC_RFQ_EVIDENCE` để lưu nguồn/cutoff/expected/actual. Kiểm tra trình duyệt dùng `python -m pytest -q tests/browser_rfq_card.py`. Windows có thể chỉ định Chromium qua `AMC_BROWSER_EXECUTABLE`; CI dùng Playwright Chromium. [Workflow](../../../.github/workflows/ci.yml)

## 8. Artifact và phục hồi

CI đầu trên `b82c2ead` phát hiện test RFQ và test Storyboard cùng xuất vào `connected-review/journey/wf08-v2`. Lỗi `FileExistsError` bảo vệ file đã tạo. Bản sửa truyền thư mục xuất của Storyboard qua lời gọi test sở hữu thư mục đó; RFQ có thư mục riêng. Chạy cùng lúc hai bài với cả hai biến xuất evidence để kiểm hồi quy. [Push đầu](https://github.com/datnv41001/ai-company/actions/runs/45938622029) · [PR đầu](https://github.com/datnv41001/ai-company/actions/runs/45938629680)

Trên Windows, 20 ca projection/export đạt, 1 ca PostgreSQL kiểm 25 phép đối chiếu đạt, Chromium mở 3 phiếu ở 3 kích thước × 2 theme. Lần chạy đầu của test giao diện dùng sai bộ giải mã màu cho token CSS `#fff` và trả NaN. Đã sửa phép đo hỗ trợ cả mã hex 3/6 chữ số, giữ ngưỡng contrast 4,5. Một lượt khởi tạo pytest bị từ chối thư mục tạm mặc định; lượt đạt dùng thư mục tạm riêng.

Artifact `rfq-evidence-head` và `rfq-evidence-integration` lưu phiếu, màn hình, dữ liệu kiểm, JUnit browser và kết quả đối chiếu. `api-regression-*` lưu JUnit suite đầy đủ. Mỗi revision có link đến lần CI trong draft PR. Để ngừng sử dụng phiếu, ngừng chạy exporter; có thể revert commit qua review. Schema v26, runtime, grants, KPI và dữ liệu sản phẩm không cần rollback.

## 9. Các giả thuyết đã loại

“Đủ trường tức là Sales đã duyệt”, “quote sandbox chứng minh doanh thu thật”, “thời điểm tạo chính là lúc sửa”, “hai campaign cùng tên có thể ghép receipt” đều trái bằng chứng. Một test ban đầu giả định client nhìn thấy raw campaign của mình. Kết quả thực cho thấy client chỉ nhìn thấy client record có quyền, còn route raw campaign là nội bộ. Một lần thử thiết lập profile cho case thứ hai dùng lại fixture đã có revision, trái precondition của writer. Test hiện dựng case độc lập có dữ liệu dương ở cả hai client.

## 10. AI và practitioner

Hai control trên bộ đã mở nhãn là kiểm hồi quy. Đơn vị suy luận prospective là 12 họ có cặp VI/EN. Cohort mới chưa niêm phong; chờ custodian độc lập và vault. Pilot v2 chuẩn bị tám work order, chưa cấp việc hoặc gửi lời mời. [Bàn giao O-09](BENCHMARK.md) · [Phiếu quyết định pilot](PILOT-DECISION.md)

## 11. Quyết định còn mở

Sales Operations quyết định chủ policy MOQ, quyền xét ngoại lệ, định nghĩa qualification và nguồn quyết định. Product Owner cần chỉ định custodian, duyệt vault và người giữ digest, cùng nguồn brief, nhân sự và ngân sách pilot. Giá trị sử dụng, thời gian tiết kiệm và hiệu quả thương mại cần đo với practitioner. AMC-R60-03 còn mở cho một thử nghiệm tải có quota riêng. Charter V1 giữ 49 module, 37 vai trò, 24 workflow mẹ. Dừng ở Independent Review. Production và Commercial GA **NO-GO**.
