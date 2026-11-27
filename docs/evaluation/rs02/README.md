# RS-02 · Từ câu trả lời Research tới quyết định của editor

**Bàn giao nghiên cứu nội bộ · 27/11/2026.** RS-01 giữ kết quả âm. B thắng 1/4 cặp theo tiêu chí số trường cần sửa, dưới ngưỡng 3/4. Số trường sửa A/B là 25/23, điểm rubric là 17/48 và 24/48. Mỗi nhánh chỉ đạt 1/8 ở tiêu chí câu hỏi và bằng chứng nghiên cứu. WF-03 tiếp tục là baseline. [Phiếu và kết quả khóa](../rs01/FINAL.md)

## Chứng nhận merge #66

| Đối tượng | Git SHA |
|---|---|
| Main trước merge / parent 1 | `a6fa1976f9a5d4557a4e3b64ac28dec2eb0fc0a4` |
| Head được chấp thuận / parent 2 | `06f2b35c2b4fc8404ca059d9d0be6a9029544d17` |
| Trial được chấp thuận | `956ba9514e53ab84465158d7f2a37f0113346174` |
| Merge main / baseline RS-02 | `9cf1380361efe03d6de4455f9f0313aa32a8db80` |
| Tree chung của head, trial và main sau merge | `de0897b20a41475a250417f903c37c865492cd03` |

So với parent 1, merge chỉ thay đổi 20 tệp trong hồ sơ RS-01, hai sổ nghiên cứu và bốn script đánh giá. Verifier tất định tính lại kết quả từ bằng chứng đã khóa. GitHub ghi nhận 0 workflow run và 0 check run trên merge SHA; CI sau merge không chạy. Xem [commit và hai parent](https://github.com/datnv41001/ai-company/commit/9cf1380361efe03d6de4455f9f0313aa32a8db80). PR #65 có cập nhật mô tả về main mới; transcript vẫn gắn với candidate `3a9d8908fed6bb062cc364f43d79889647075f0d`. Chứng nhận này không xác nhận một cold handoff mới.

## Replay bốn brief đã công khai

Mỗi cặp sử dụng nguyên văn ba first replies/nhánh. Chương trình đối chiếu 24 first replies với HTTP response trong archive và lưu hash; điểm cùng nhãn lỗi lấy từ phiếu khóa. Cả bốn packet đều bị schema từ chối. TaskIntent thiếu purpose, deliverable_type, exclusions và acceptance_criteria. ActionIntent còn từ chối buyer_action và editorial_style viết tự do. KPI nghiên cứu có năm trường tự do; MeasurementDefinition yêu cầu version, business_outcome, window_days và owner_role. Ở tầng hiển thị, locale `en` cũng bị từ chối. Nếu chỉ đổi locale thành `en-US`, composition vẫn dừng ở `numerator` do KPI sai cấu trúc.

Để quan sát tác động biên tập, phép so ngoại tuyến chỉ đổi locale hiển thị và bỏ contract sai schema ở bản sao. Giữ nguyên ý định, nguồn, qualifiers và raw replies. Không diễn giải fallback action hoặc method trên nhánh này thành action/KPI đã duyệt. Tầng 3 chạy **structural QA** trên bản sao; cả tám dossier đều thiếu manifest có thẩm quyền, reviewer và recipient để ký handoff. [Dữ liệu ba tầng, hash và lỗi theo từng trường](replay.json)

| Ca | Trường đã bị yêu cầu sửa còn xuất hiện nguyên văn trong Studio (A, B) | Phần Studio giữ được | QA cấu trúc và phần còn cần editor |
|---|---|---|---|
| Tile | 5/6, 5/6 | Diện tích thùng, hao hụt cần duyệt và điều kiện vận chuyển ở đúng evidence. | A/B đều bị báo hai lỗi lặp. Ở B, hiểu sai quyền duyệt diện tích còn trong staff evidence_needed; Studio thay ô evidence bằng nguồn. Câu hỏi ở B vẫn là một giả thuyết. |
| Delivery | 5/6, 3/4 | Bốc dỡ bị loại trừ; xác nhận của hãng vận tải phải bằng văn bản. | A không có cảnh báo cấu trúc, dù positioning/rationale ngụ ý giao nhanh hoặc bảo đảm khung giao. B có một lỗi lặp. |
| Counter | 6/7, 6/7 | Studio giữ nguồn và giới hạn mẫu cùng quan sát. | A không có cảnh báo; B có một lỗi lặp. Cần phân biệt sở thích giả định với căn cứ lựa chọn thử nghiệm. |
| Check | 4/6, 5/6 | Studio giữ toàn bộ khai báo đã cung cấp. | Cả hai không có cảnh báo cấu trúc. Editor vẫn cần câu hỏi phân biệt hai cách mua hoặc một thử nghiệm đủ rõ để đổi quyết định. |

Các phân số trên đếm trường raw bị đánh dấu trước đây có giá trị xuất hiện **nguyên văn** ở bất kỳ trường nào trong bản Studio. Chúng không đo số chỉnh sửa thực tế của bản ghép. Research notes giữ evidence_needed; Studio evidence lấy dữ kiện/qualifier từ nguồn. Một câu được đưa ra khỏi ô hiển thị vẫn có thể gây hiểu sai ở notes, rationale hoặc positioning. Chưa đo thời gian editor hoặc chấm lại điểm chuyên môn trên bản Studio.

## Hai brief mới qua API có kiểm scope

| Brief tổng hợp | Quyền và dữ kiện kiểm được | Diễn giải nghiệp vụ |
|---|---|---|
| Kiểm tra đồng hồ áp suất | API tạo manifest từ brief và nguồn đã duyệt. KPI ghim id, revision, digest; xác nhận trên yêu cầu hợp lệ, cohort 18 ngày, distinct appointment ID. Studio kế thừa nguyên câu đo chính kể cả khi worker đề xuất đếm phiên. Đổi câu đó bị QA phát hiện. | Worker không phải suy lại event, denominator, window hay dedup. Ca thử chưa có phép đo hiệu quả dịch vụ thật. |
| Vách chia ô kho | Manifest hợp lệ có action RFQ và có wording/qualifier; thiếu primary definition. Đề xuất đếm biểu mẫu còn là văn bản của kế hoạch. Thử gắn định nghĩa appointment trả 409. | Chưa có tỷ lệ RFQ đã duyệt, số liệu thực đo hay quyết định qualification bởi Sales. |

Cả hai API path kiểm trên SQLite và PostgreSQL. Handle không tồn tại bị từ chối ngay khi validate reply. Bộ kiểm handoff hiện hữu kiểm withdrawal, stale revision (412), quyền reviewer/recipient, buyer/scope thay đổi và hai campaign trùng tên trong agency. [Brief đầu vào](controlled-briefs.json) · [Ca kiểm mới](../../../tests/test_rs02_contract_alignment.py) · [Ca phân quyền và thu hồi](../../../tests/test_strategy_runtime_handoff.py)

## Ví dụ chuyên môn và giới hạn QA

Quyết định là viết hướng dẫn sử dụng khay lúc giao ca hay soạn bảng thông số cho người mua. Một quan sát ở một lần giao ca chỉ đủ căn cứ cho một hướng dẫn nội bộ giới hạn. Phỏng vấn về bước gần nhất giúp phân biệt *không biết thao tác* với *thiếu thông số để chọn*. Nếu hai quan sát được phép sau đó đều tìm thông số trước, giữ lại hướng dẫn và đề nghị người có thẩm quyền xem xét bảng thông số. Kết quả trái chiều cũng dẫn tới giữ việc. Chưa thu thập các quan sát đề xuất. [Tình huống, giới hạn mẫu và quy tắc đổi hướng](editor-example.json)

Codex viết ví dụ kiểm soát theo vai trò biên tập dựa trên commission tổng hợp sẵn có. Chưa có xác nhận tác giả là một editor nghiệp vụ độc lập. Phép thử kiểm khả năng biểu đạt và đường bàn giao; không có invocation model mới. Research notes chứa yêu cầu thu thêm bằng chứng. Studio biểu đạt được câu hỏi phỏng vấn nhưng QA đánh dấu hai câu tự biên tập là unresolved. Chữ ký Research bị từ chối, không phát hành work order. Ở một commission riêng, dùng phiên bản Studio đã qua QA, reviewer đủ thẩm quyền ký diễn giải có điều kiện. Người nhận chỉ thấy hướng dẫn nội bộ đã duyệt; lời diễn giải, mẫu quan sát và ghi chú riêng không đi ra khỏi giới hạn bàn giao. Phương án thứ hai không duyệt lại câu hỏi bị giữ ở phương án thứ nhất.

**RED để review phạm vi sau.** Trạng thái nghiệp vụ mong đợi là editor có thể ghi một câu hỏi phỏng vấn trung lập mà không cần chứng minh nội dung một câu hỏi như một khẳng định. Ca tái hiện khóa đúng hai span, HTTP 409 và work order chưa phát hành. Đề xuất nhỏ nhất để xem xét là cho phép reviewer đủ quyền xác nhận phân loại “hướng dẫn nghiên cứu” cho đúng span và revision. Cần đối chứng bằng câu hỏi dẫn dắt có claim, qualifier sai, nguồn bị thu hồi, thay revision và quyền người nhận. Cơ chế giữ việc hiện còn nguyên. Với Delivery A, mức phát hiện của lớp cấu trúc được đo trên packet ngoại tuyến; chưa có căn cứ gọi đó là lỗi lọt qua QA có chữ ký.

## Bàn giao cho người review

Tại checkout candidate, dùng Python và dependencies theo README của repo. Tái hiện offline bằng `python tests/evaluation/rs01_final.py` và `python tests/evaluation/rs02_replay.py`. Lệnh mặc định chỉ so sánh replay; `--write` dành riêng cho chủ đích tái tạo tệp. Để xác minh cả PostgreSQL dùng database thử cách ly với các role và biến môi trường theo cấu hình integration của repo, bật `AMC_TEST_PG=1`, rồi chạy `python -m pytest -q tests/test_rs02_contract_alignment.py tests/test_strategy_runtime_handoff.py tests/test_strategy_handoff_contract.py tests/test_measurement_integrity.py`. Đối chiếu số case với receipt để phát hiện trường hợp PostgreSQL bị skip.

[Protocol đối chứng và ngân sách đề xuất](NEXT-PROTOCOL.md) · [Receipt kiểm thử](test-receipt.json) · [Danh mục SHA-256](MANIFEST.json). Nghiên cứu dừng tại Independent Review. Không thay runtime, adapter, schema hoặc quyền recipient. Chưa xác lập BUSINESS_VALIDATED. Production và Commercial GA vẫn NO-GO.
