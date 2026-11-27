# Phản biện PR #64 · Phiếu Content và thứ tự sự kiện Sales

PR #64 đang chờ Independent Review. Mốc đối chiếu ban đầu là head `d79f76373af99585b6b8b720b2a60a93f882c48b`, tree `a19ba1ccdd4a7e85ffe12e004e62c64d61d0f59b`, trial `3d37b1b2d34a69cc80e8def2083bccbd37ebb3c8`. Base là main #63 `053410d161b15285a1ef264f853d4920a3d559e1`. [Gói bằng chứng ban đầu](https://github.com/datnv41001/ai-company/blob/876a8c044324c2a0b4a3c9657842aa92a600f4e0/docs/evaluation/round64-verification/START-HERE.md)

## AMC-R64-01 · Nhân sự Content cần nhận đủ brief

Ở bản cũ, hai phiên xác thực đã đọc cùng biên nhận và đều thấy trạng thái đủ lập bản nháp. Cả hai thiếu CTA, văn phong, yêu cầu bắt buộc, điều cấm và tiêu chí nghiệm thu. Ảnh trình duyệt và phép thử RED ở gói review lưu hiện trạng này. [Đối chiếu bản giao cũ](reviewed-handoff-red.json)

Trong Studio, reviewer chọn người nhận đủ quyền, kiểm bản xem trước các ràng buộc và ký việc chuyển tiếp trên đúng revision. Phiếu phân biệt brief đã ghim, câu sản phẩm đã qua QA, ngữ cảnh quan sát dùng cho bản nháp, hướng thông điệp và nghĩa vụ sản xuất. Tình huống và hướng viết đến từ lựa chọn tóm tắt của người ký. Ghi chú Research, danh tính người duyệt, thông tin định vị nguồn, mandate và mẫu quan sát riêng tư không thuộc phiếu Content. Hợp đồng đo lường và phê duyệt hành động giữ riêng. Người nhận chỉ được soạn bản nháp nội bộ.

- **Route Tray.** Đối chiếu hai phiên trên cùng receipt. Phiếu phải có `catalogue_download`, văn phong `concise`, hướng dẫn cho một lần giao ca, điều cấm `automatic worker tracking` và tiêu chí gắn asset với công việc đã quan sát. Đối chiếu ảnh người nhận để kiểm cách dùng thực tế.
- **Purchasing directors.** Brief, mục tiêu, quan sát, giới hạn mẫu và điều kiện nghiệm thu của ca mua tại quầy phải thuộc cùng tình huống. Đổi brief hay Research làm phán quyết cũ hết hiệu lực. Riêng fixture cũ đã tái dùng dữ kiện giao ca; đồng thời hợp đồng cũ không yêu cầu người ký xác nhận phạm vi nội dung được giao.
- **Giữ việc.** Reviewer có thể báo mâu thuẫn hoặc có thông tin riêng tư. Phần mềm còn kiểm các mâu thuẫn có quy tắc và dấu nguồn bị hạn chế. Quyết định ngữ nghĩa và việc cho phép chuyển tiếp vẫn cần người đọc brief. Ca vượt phạm vi, rút nguồn, mất quyền, gửi lại hoặc ký đồng thời tiếp tục qua các cổng hiện hữu.
- **Phiên bản và rollback.** `amc.internal-strategy-handoff/2` là contract staff mới trong cùng draft. Nếu gặp biên nhận dev /1, Studio giữ việc; editor phải lưu revision mới, QA duyệt và reviewer ký lại. Receipt cũ vẫn giữ lịch sử. Để rút tính năng, trở về main #63 vốn chưa có đường bàn giao này, bảo toàn dữ liệu và runtime lock tương ứng. Quay lại app /1 sẽ khôi phục hành vi thiếu brief. Không có migration, mở rộng quyền hoặc thay release WF‑03/adapter.
- **Giới hạn.** Bước này tạo phiếu giao việc. Các counterfactual, worker được kiểm soát và lịch sử Qwen chuẩn có run ID và mục đích kiểm khác nhau. O‑09, pilot practitioner và quota renderer vẫn mở.

## AMC-R64-02 · OPEN

JUnit lịch sử có HTTP 409 ở thao tác chuyển inquiry thứ hai cho Sales. Bản gốc còn trên máy; gói bằng chứng có bản đầy đủ đã bỏ hostname, tiền tố đường dẫn local và địa chỉ bộ nhớ, cùng SHA-256 trước/sau. JUnit gốc thiếu state và hai timestamp cần để quy nguyên nhân.

Chạy một lần trên mỗi checkout #63 và #64 đã review, PostgreSQL dùng một lần trên Windows. Cả hai inquiry đều ở revision 1, state `received`, thiếu `commercial_moq`, quantity 3 box, MOQ 5 và consent `quote_request`. Lệnh tự nhiên trả 200, chuyển event sequence 31 → 32. Thời điểm gửi trễ hơn `last_event_at` 0,903 ms ở #63 và 12,119 ms ở #64. Trên mỗi DB, hai lệnh đối chứng đều bị từ chối ở revision ban đầu: `refer` sớm 1 μs và `assign` ở state `received` với timestamp bằng thời điểm intake. Hai lệnh đó phân biệt được hai nhánh của cùng lỗi. Chưa tái hiện lỗi tự nhiên trong hai lượt này; giữ giả thuyết clock và state mở. Giữ nguyên runtime Sales và fixture lịch sử. [Timestamp, khoảng lệch đồng hồ, revision, scope, consent và receipt](sales-observations.json)

## Chạy trên máy khác

Dùng checkout theo SHA, Python và database thử riêng theo [hướng dẫn dự án](../../../../README.md) và job `api-tests`. Bật `AMC_TEST_PG=1` với role runtime, migration DSN và các khóa thử độc lập theo CI. Từ gốc repo chạy:

```sh
python -m pytest -q tests/test_strategy_runtime_handoff.py tests/test_strategy_handoff_contract.py
python -m pytest -q tests/browser_strategy_handoff.py
python -m pytest -q -rs --junitxml=api-regression.xml
```

Đặt `AMC_RUNTIME_STRATEGY_EVIDENCE` và `AMC_STRATEGY_UI_EVIDENCE` về thư mục mới để xuất biên nhận và ảnh. Để tái hiện RED, chạy pytest trên [probe](probe_reviewed_handoff.py) bằng cwd tại checkout cũ. Để kiểm Sales, đặt `AMC_SALES_PROBE` thành đường dẫn JSON mới và gọi `python <đường-dẫn-tới-probe_sales.py>` từ checkout được kiểm. Probe chạy đúng case cũ, giữ payload tự nhiên và ghi riêng hai phép đối chứng. Chỉ dùng DB tổng hợp đã migration.

Independent Reviewer có thể đối chiếu receipt của người ký và người nhận, thử một brief có nội dung riêng tư và mở ảnh Chromium trước khi quyết định về R64-01. [Đề xuất đối chứng #65, chờ cấp quyền](NEXT-65.md). Production và Commercial GA vẫn NO-GO.
