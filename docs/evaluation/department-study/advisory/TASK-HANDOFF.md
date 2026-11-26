# O-09 · Người điều phối xác minh một giá trị khách vừa sửa

## Quyết định từ bằng chứng cũ

Giữ nguyên baseline trong sản phẩm. Phép đếm dưới đây dùng cùng 24 thẻ đã mở nhãn, cùng dự đoán từ `FIRST-RUN.zip` và cùng scorer. Lần kiểm tra này chỉ đọc tệp, không gọi model. Cả hai bộ quy tắc đạt 8/24. Hai lượt chấm bằng AI cùng đánh giá 3/5 câu hỏi Qwen phát hiện thêm đạt đủ tiêu chí. Mỗi tình huống có hai bản ngôn ngữ. [Nghiên cứu gốc](PROSPECTIVE-HANDOFF.md) · [Biên nhận đối chiếu](../../../../tests/evaluation/department/task-handoff/offline-result.json)

| Đáp án đối chiếu | Số thẻ | Qwen chọn đúng loại thô | Qwen đạt đủ hợp đồng |
|---|---:|---:|---:|
| Hỏi khách một trường | 8 | 7 | 7 |
| Đủ điều kiện đi tiếp | 8 | 1 | 0 |
| Chuyển người có thẩm quyền | 8 | 6 | 0 |
| Tổng | 24 | **14** | **7** |

Trong 13 phản hồi sai hợp đồng, 12 phản hồi chuyển policy và một phản hồi ready vẫn chứa trường và câu hỏi gửi khách. Đếm loại thô giúp tìm bước gây lỗi. Phép đếm giữ nguyên cả 13 phản hồi trong điểm nghiệp vụ. Chưa biết đổi grammar sẽ làm model chọn loại nào ở lần sinh mới. [Hồ sơ lịch sử](../../../../tests/evaluation/department/handoff-v2/FIRST-RUN.zip)

## Một hành trình thử được bằng code

Với một trường đang theo dõi, người điều phối cần thấy giá trị cũ, lời khách gần nhất, giá trị có thể sử dụng, nguồn và người có quyền xác nhận. Lab chỉ nhận một trong hai trường, điểm nhận hàng hoặc địa điểm dịch vụ. Dữ liệu tổng hợp được soạn kèm đáp án để thử hợp đồng. Đây là fixture phát triển đã công bố. [Hồ sơ đầu vào](../../../../tests/evaluation/department/task-handoff/source-cases.json) · [Trace từng ca](../../../../tests/evaluation/department/task-handoff/offline-result.json)

| Bước | Dữ liệu và hành vi đã chạy | Ranh giới khi tích hợp |
|---|---|---|
| 1. Đọc lời khách | Đối chiếu cả câu với mẫu Việt/Anh đã khai báo cho đúng trường, giữ nguyên trích đoạn và dấu hiệu xác nhận, thay thế hoặc rút giá trị. | Nhận dạng ngôn ngữ mở còn cần đánh giá. Lời không khớp chuyển người rà soát. |
| 2. Chọn ngữ cảnh | So nguồn lời khách, snapshot CRM và policy với cùng agency/client/brand/campaign của ca. Kiểm tra tham chiếu, revision, cửa sổ hiệu lực và phê duyệt policy. | Trong sản phẩm, backend phải cấp scope và snapshot từ phiên được phân quyền. Bộ fixture mô phỏng đầu vào đã cấp. |
| 3. Xác định giá trị | Trả giá trị cũ, giá trị hiện hành hay chưa biết, lý do và nguồn chi phối. Câu rút thông tin, thông tin hết hạn và lời cũ hơn bản CRM được xử lý riêng. | Thời gian fixture có độ phân giải theo ngày và mỗi ca có một lời khách. Hai cập nhật cùng ngày từ nguồn khác nhau cần định danh, thứ tự và quy trình phân xử. |
| 4. Chọn người nhận | So giá trị với phạm vi policy. Nếu ngoài vùng, chuyển đúng `sales_manager` hoặc `service_manager`. Thiếu giá trị dẫn tới một câu hỏi cho khách. | Người duyệt giá hoặc vùng dịch vụ thuộc chính sách của doanh nghiệp. |
| 5. Lập đề xuất | Lấy câu hỏi theo ngôn ngữ/trường từ mẫu đã duyệt hoặc lập đề xuất chuyển nội bộ. | Câu hỏi tự do hoặc câu chứa nhiều ý cần phép thử riêng. |
| 6. Kiểm chứng | Đối chiếu đầu ra với dữ liệu hiện hành và người nhận dự kiến. Trả `human_review_required`. | Không có writer, model, API nền tảng hoặc chức năng xác nhận giao dịch trong lab. Nếu nối runtime, phải đọc lại revision trước khi người có quyền quyết định. |

Có 12 trace đúng kỳ vọng của fixture và chín phép từ chối riêng cho nguồn, scope, phiên bản, thời hạn hoặc ngữ nghĩa. Ví dụ, khách đổi `SV-10` thành `SV-80` thì trace giữ cả hai giá trị và chỉ đúng service manager vì `SV-80` ngoài vùng đã duyệt. Người thiết kế viết cả quy tắc và fixture. Kết quả kiểm hợp đồng này chưa đo khả năng hiểu lời khách tự nhiên hoặc chất lượng trước người dùng. [Mã kiểm chứng](../../../../tests/evaluation/department/task-handoff/clarification.py)

## Grammar và hai ví dụ dễ chấm nhầm

Đã đọc hướng dẫn GBNF công khai ngày 26/11/2026, đối chiếu tài liệu và header ở đúng upstream commit `1f8baae28d096624bd47d33d2d179ec479d47720`. Hướng dẫn nêu grammar áp dụng từ root theo Unicode, có thể biểu diễn nhánh, và việc chuyển JSON Schema chỉ hỗ trợ một tập tính năng. Lab thử GBNF viết tay theo ba loại quyết định. Nó chấp nhận một cách tuần tự hóa JSON có thứ tự khóa cố định. Phần đối chiếu lịch sử dùng JSON gốc đã parse bằng scorer cũ. [Tài liệu hiện hành](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md) · [Bản ở commit đã ghim](https://github.com/ggml-org/llama.cpp/blob/1f8baae28d096624bd47d33d2d179ec479d47720/grammars/README.md) · [Header C API](https://github.com/ggml-org/llama.cpp/blob/1f8baae28d096624bd47d33d2d179ec479d47720/include/llama.h) · [Giấy phép upstream](https://github.com/ggml-org/llama.cpp/blob/1f8baae28d096624bd47d33d2d179ec479d47720/LICENSE)

Trên Windows x64, bộ kiểm nạp DLL đúng hash và vocabulary cũ từ GGUF ở chế độ `vocab_only`. Không tạo inference context. Bộ kiểm đưa từng token đã biết vào grammar sampler, gồm cả token kết thúc, và ghi nhận chuỗi được chấp nhận hay bị chặn. 6 chuỗi đúng cú pháp được nhận và 8 chuỗi sai bị chặn. Một câu hỏi về cỡ giày vẫn đúng cú pháp. Một đề xuất ready khi khách đã rút địa điểm cũng đúng cú pháp. Bước 6 từ chối cả hai khi xét hồ sơ. Số lượt inference mới và phí provider đều bằng 0. Thời gian lao động, điện và cost/accepted job chưa đo. [Grammar](../../../../tests/evaluation/department/task-handoff/decision.gbnf) · [Chuỗi kiểm](../../../../tests/evaluation/department/task-handoff/grammar-cases.json) · [Biên nhận native](../../../../tests/evaluation/department/task-handoff/native-result.json)

Từ gốc checkout, lệnh đầu tạo biên nhận ở đường dẫn mới. Lệnh thứ hai chấm lại trace và đối chiếu hash của grammar, fixture và kết quả native đã lưu. Lệnh thứ ba là phép kiểm native tùy chọn trên Windows với DLL và GGUF đã có đúng hash. Khác phiên bản hoặc ABI sẽ bị từ chối trước khi nạp thư viện. Trên máy khác có thể dùng `test-gbnf-validator` của upstream cùng commit, kiểm từng chuỗi UTF-8 trong grammar-cases với file GBNF và so kết luận đúng/sai. Không cần model service.

```sh
python tests/evaluation/department/task-handoff/check.py --output task-handoff-replay.json
python -m pytest -q tests/evaluation/department/task-handoff/test_task_contract.py
python tests/evaluation/department/task-handoff/native_grammar.py PATH_TO_LLAMA_DLL PATH_TO_PINNED_GGUF
```

## Đợt đánh giá tiếp theo

Chưa cấp ngân sách cho một lượt model mới. Phép thử triển vọng có thể bắt đầu từ công cụ tất định. Một người giữ dữ liệu độc lập soạn và niêm phong 12 tình huống chưa xuất hiện ở thẻ hoặc fixture đã công bố, sáu RFQ và sáu lịch dịch vụ, mỗi ca có cặp Việt/Anh và một trường cần đối soát. Cân bằng ask, ready và clarify_policy, có thông tin rút/sửa, nguồn hết hạn, điều khoản xung đột và ca đủ điều kiện. Hợp đồng gold bổ sung giá trị hiện hành hoặc unknown, ref trích đoạn, revision chính sách và người được quyền xử lý. Khóa ngưỡng, phương pháp gán thời điểm, rubric và người giữ nhãn trước khi giao inputs. Hiện chưa có cohort độc lập này hoặc practitioner gán nhãn.

So baseline hiện hữu với nhánh tất định chọn dữ kiện và policy trên cùng thẻ. Dừng tiến bước nếu có thêm false-ready, thẩm quyền bịa, bất cứ lỗi scope nào, hoặc một ngôn ngữ giảm. Yêu cầu ít nhất bốn quyết định đúng thêm trên 24 thẻ, đủ cả trường/nguồn/người nhận cho mọi trường hợp mới đúng và tất cả câu hỏi mới đúng qua chấm mù nghiệp vụ. Ghi riêng tỷ lệ phải chuyển kiểm thủ công, số phút hiệu chỉnh và chi phí cho mỗi việc được chấp nhận. Nếu chỉ cải thiện cú pháp hoặc chỉ tăng số lần chuyển người, giữ baseline. Sau khi mở nhãn, thẻ trở thành fixture replay. Một lượt model tương lai cần cohort mới, proof khóa protocol và phê duyệt riêng trước inference. [Cách xếp năng lực và công cụ theo việc Marketing](TASK-ROUTING.md)
