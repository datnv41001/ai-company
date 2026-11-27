# O-09 · Chuẩn bị bộ đối chiếu mù cho Sales và Service

**Quyết định chờ người giữ bộ ca độc lập.** Vòng #62 đã xác định ba nhánh tất định, đầu vào chung, cách giữ lần trả lời đầu và ngưỡng quyết định. Chưa có bộ ca kín được cấp, biên nhận khóa độc lập, dự đoán trên holdout hay điểm chất lượng mới. Số thẻ triển vọng đã chạy bằng 0. Điểm 8/24 của mỗi control thuộc cohort đã mở nhãn ở vòng trước. [Đối chiếu O-09](../department-study/advisory/TASK-HANDOFF.md) · [Hồ sơ #61](../round61/INTELLIGENCE.md)

## Phiếu đặt bộ 12 họ, 24 thẻ

| Điều người giữ bộ ca cần thực hiện ngoài repository | Cách người thứ hai kiểm trước khi khóa |
|---|---|
| Viết 6 họ RFQ về điểm giao và 6 họ dịch vụ về địa điểm thực hiện. Mỗi họ có một bản VI và một bản EN tương đương. | Đếm 6 × 2 + 6 × 2 thẻ. Hai bản cùng họ phải có cùng người nói, ý định, phạm vi, thời điểm tương đối, nguồn và người có quyền. Đọc ngược từ mỗi bản để phát hiện bản dịch vô tình cung cấp thêm manh mối. |
| Phân bổ trong mỗi hành trình 2 họ cần hỏi khách, 2 họ cần chuyển chủ policy và 2 họ có thể bàn giao. | Người giữ khóa kiểm được 4 họ ở mỗi quyết định, 12 họ độc lập về thiết kế. Ghép cặp và thứ tự ở trong vault. Mỗi ID thẻ là mã ngẫu nhiên, không mã hóa nhãn, họ, nhánh hoặc câu trả lời. |
| Phủ tình huống cập nhật/rút dữ kiện, nguồn mất hiệu lực, CRM và lời khách khác nhau, điều khoản bất đồng và ca đủ điều kiện. Có cách diễn đạt tự nhiên ngoài mẫu regex đã công khai. | Đối chiếu với deck cũ và fixture công khai theo ý nghĩa và câu chữ. Giữ nguyên lỗi có thể có của candidate trên câu lạ. Chuyên viên thứ hai kiểm VI/EN trước khi release inputs. |
| Mỗi thẻ có một brief, một trường đích, lời khách, CRM tại cutoff, policy kèm ref/revision, phạm vi, thẩm quyền, hiệu lực và câu hỏi mẫu được phép. | Cả ba nhánh có cùng dữ kiện quan sát được. Giá trị/nguồn có thể là unknown. Khóa các xung đột theo thông tin thực sự có thể thấy và ghi cách xử lý ca ngoài sức biểu diễn của candidate. |

Product Owner xác nhận chưa có custodian hoặc vault được duyệt. Người triển khai bàn giao thiết kế công khai ở trạng thái **chưa niêm phong**. Custodian và người chấm giữ riêng bản ngữ liệu, bảng cặp, đáp án, rubric chi tiết và mapping nhánh. Mỗi tệp kín có digest trên byte thực cùng nonce bí mật, ghi nhận thời điểm và một bản cam kết ở người thứ hai trước khi chia sẻ inputs. Chỉ công bố digest có nonce hoặc biên nhận tổng hợp. Khóa riêng người được quyền mở, hạn lưu và phương án phục hồi. Bản input/case đã bị lộ phải ghi sự cố và chuyển sang tập phát triển.

### Sơ đồ kho riêng để custodian tiếp quản

Đây là cấu trúc đề xuất. PO chọn người và nơi lưu trước khi tạo. Dùng thư mục ngoài Git và ngoài thư mục đồng bộ đám mây, ACL theo tài khoản Windows hoặc quyền sở hữu POSIX. Tách tài khoản runner khỏi tài khoản custodian. Quản trị viên máy có thể đọc dữ liệu cục bộ nên vault cần nằm trên máy mà developer/candidate không quản trị.

| Thư mục riêng dự kiến | Vật lưu và quyền tối thiểu |
|---|---|
| `design/` | Custodian ghi phiên bản protocol, manifest digest, thời hạn, snapshot thuật toán, các view, phiên bản scorer và thứ tự. Người giữ digest nhận bản cam kết độc lập ở nơi riêng trước khi phát input. |
| `sealed/` | Custodian và người duyệt nhãn có quyền đọc hạn chế. Lưu gold, rubric chi tiết theo ca, bảng pair/branch, thứ tự, nonce, thời điểm khóa và kết quả kiểm dịch. Runner và developer không có quyền đọc. |
| `inputs/` | 24 ID xáo trộn, chỉ có projection từ cùng bộ nguồn tổng hợp đã duyệt. Runner có quyền đọc. Tách bản working của từng nhánh. |
| `first-run/` | Mỗi nhánh có 24 receipt, output thô, lỗi và log đóng gói. Runner chỉ gửi output lần đầu. Custodian chụp bản bất biến, khóa digest và giao bản độc lập trước khi chấm. Mất điện hoặc quá hạn tạo ca bỏ dở, giữ phần đã có. |
| `blind-grade/` | Chỉ người chấm và custodian tiếp cận. Gói xóa tên nhánh, ghép output với đúng input theo mã chấm, giữ thời điểm, quyết định và lý do độc lập. Hai lượt chấm bất đồng lưu riêng. |
| `report/` | Custodian mở gold sau khi khóa predictions. Đối chiếu toàn bộ 72 vị trí, kiểm digest và tổng hợp. Chỉ xuất thông tin đã duyệt công bố. Backup riêng theo quyền cùng thời hạn lưu, kiểm phục hồi trước khi dùng dữ liệu kín. |

Với mỗi ca, custodian đăng ký trước các ô rubric gồm hành động, trường, giá trị hiện hành/unknown, trích đoạn và ref, revision/hiệu lực policy, người nhận, sự cần thiết của câu hỏi và mức hữu ích của escalation. Người chấm đánh dấu từng ô đạt/sai/thiếu, dẫn lại bằng chứng có ID và ghi bất đồng. Ở nhánh hỏi, chỉ chấp nhận một câu khả thi đúng trường, đúng người, đúng ngôn ngữ. Ở nhánh chuyển nội bộ, kiểm chủ quyết định cùng lý do và việc người đó thực sự có thể xử lý. Ở nhánh ready, kiểm nguồn, thẩm quyền và phạm vi trước bàn giao. Hành động biết sai scope hoặc tự quyết quyền phát hành là lỗi nghiêm trọng dù đúng cấu trúc. Chi tiết đáp án từng thẻ, cách mã hóa packet và ánh xạ phiếu do người giữ vault tạo riêng.

## Phiên bản nhánh và phép chiếu danh nghĩa

Gốc các file dưới đây là `tests/evaluation/department/`. SHA-256 tính trên byte nguồn sau khi chuẩn hóa CRLF thành LF, để đối chiếu giữa Windows và Linux. Snapshot của các thuật toán đã nhận diện. Custodian còn phải khóa checkout, adapter, scorer, inputs, rubric và thứ tự cùng lúc trước khi đo.

| Nhánh hoặc công cụ | Entry point | SHA-256 |
|---|---|---|
| Control trường bắt buộc | `handoff_baseline.py:baseline` | `fe79cc327796b4be942c7af2bef798571cfe52ae02ed3093f93f883ab2fce384` |
| Control có quy tắc câu và điều khoản | `handoff_comparison.py:improved` | `fe5b7d208815e7c18e5f744a43e8647cc929dbf747f57e52e1ece86078938abb` |
| Candidate chọn căn cứ | `task-handoff/clarification.py:project → resolve → route → draft → verify` | `ff3a3ed6870720466ae15b91e4dfabf0dd9a95400bebfc04226ba35a04e6d842` |
| Chấm phần quyết định dùng chung | `handoff_score.py:score` | `bba1bd8bbe5059fa6222a59f2cf3cd80f291561bb1852097857e02ae50eeaf8b` |

Chỉ khác biệt về thuật toán được đưa vào so sánh. Custodian chuẩn bị hai view từ **cùng** source packet. Với controls, ID/locale giữ nguyên, journey đi theo brief, `required_fields` ánh xạ tên trường đã được áp dụng, `received_fields` là snapshot CRM thô, `buyer_message` nguyên văn. Trong `brief` trình bày policy và phạm vi, thời điểm, ref, revision cùng các dữ kiện nguồn có sẵn cho candidate theo một định dạng trung lập đã khóa trước. Với candidate, dùng đúng `scope, as_of, current_policy_revision, policy, crm, buyer` của các nguồn đó. Trước khi khóa, dùng fixture phát triển xác nhận hai view có cùng nội dung có thể biết. Cấm điền suy luận, đáp án hoặc nhãn vào view. Nếu không thể biểu diễn nguồn mâu thuẫn trong hợp đồng một policy, ghi hạn chế và counted error cho nhánh đó. Candidate có thể từ chối vì nguồn sai scope, policy cũ hoặc ngoại lệ. Lưu từ chối nguyên văn.

Mỗi quyết định đầu được ghi một lần theo `input_digest, algorithm_digest, card_id, started_at, finished_at, raw_output_or_error`. Custodian ghi đủ 24 vị trí cho từng nhánh, kể cả timeout, không phản hồi và malformed. Khóa ba tập dự đoán với người giữ digest trước khi cho người chấm đọc nhãn. Giữ output gốc bất biến. Công cụ chấm hiện hữu yêu cầu output bốn khóa, nên dùng phần `proposal` của trace candidate cho thước đo chung. Các ca lỗi đi vào mẫu số 24 với điểm 0. Trace chi tiết được chấm riêng theo source ref, trích đoạn, giá trị hiện hành/unknown, policy revision và người nhận. Hai control chỉ trả bốn khóa. Bất kỳ trường bổ sung nào chúng không phát ra phải ghi là thiếu.

## Phiếu kết quả cần trả về

- Tính số đúng quyết định **và** trường theo từng control trên chính 24 thẻ mới. So candidate với control có tổng đúng cao hơn. Nếu hòa, kiểm gate riêng với cả hai. Giữ bảng theo VI/EN, hành trình và quyết định. Báo cặp cả hai đúng/chỉ VI/chỉ EN/cả hai sai trên 12 họ.
- Gate O-09 cần thêm ít nhất 4/24 đúng, không giảm đúng ở ngôn ngữ nào và không tăng false-ready so với control mạnh hơn. Không chấp nhận bất kỳ kết luận sai scope hoặc thẩm quyền bịa. Mọi ca tăng thêm có nguồn/trường/người nhận khớp. Người chấm mù nghiệp vụ cần xác nhận tất cả câu hỏi mới đúng hữu dụng và đúng ngôn ngữ. Thiếu chấm mù để gate ở trạng thái chờ.
- Ghi cả số ready hữu dụng, hỏi khi đã đủ, hỏi người sai thẩm quyền, escalation thừa/sai người, chuyển kiểm thủ công và ca không ra output. Báo phút sửa và tổng chi phí trên mỗi việc được người nhận chấp nhận khi có receipt. Mẫu số bằng 0 hoặc thiếu chứng từ thì giữ null. Giữ bất đồng của người chấm, đặc biệt khi đúng nhãn nhưng câu hỏi vô ích.
- Sau mở nhãn cohort chỉ dùng làm regression. Bất kỳ thay đổi thuật toán, người chấm đã nhìn mapping, hoặc dự định chạy model mới đều cần quyết định/cohort phù hợp trước khi đo khả năng tổng quát.

Từ repo, `python -m pytest -q tests/evaluation/department/task-handoff/test_task_contract.py` đã đạt **2 test** trong vòng này trên fixture công khai. Trên inputs/gold công khai trong `handoff-v2`, chạy lại `check_cards`, `baseline`, `improved` và `score` cho kết quả mỗi control **8/24** đúng, **14** false-ready và **0** malformed/missing. Kết quả xác minh khả năng chạy lại lab. Việc chốt bộ private cần custodian độc lập, người kiểm song ngữ, scorer nghiệp vụ và quyền truy cập vault của họ. [Nguồn về chấm quyết định kèm căn cứ](MARKET.md)

## Mẫu trống để bàn giao

Các khối JSON sau chứa tên trường và giá trị trống. Custodian sao chép từng mẫu vào thư mục riêng được nêu ở trên. Chỉ mẫu trống được đưa vào Git. Mọi giá trị null tại thời điểm chuẩn bị đều có nghĩa là chưa có dữ liệu. Mã họ, mã người chấm và nhãn chỉ được điền tại vault.

**1. Phiếu soạn một họ trong sealed/.** Nhân phiếu thành 12 bản. Viết bản gốc rồi giao người thứ hai đọc bản dịch bằng chính nguồn tổng hợp và đối chiếu độc lập ý nghĩa. Ghi bất đồng và giải quyết trước khi khóa. Tạo ngẫu nhiên hai ID thẻ riêng, xáo trộn thứ tự 24 thẻ, xuất cho runner phần dữ kiện quan sát được. Giữ nguyên mã họ, phân bổ, đánh giá tương đương và gold trong sealed/.

```json
{
  "private_family_id": null, "journey": null, "synthetic_source_refs": [],
  "synthetic_scope": null, "knowledge_cutoff": null, "effective_policy_ref": null,
  "cards": {"vi": {"opaque_id": null, "input_path": null}, "en": {"opaque_id": null, "input_path": null}},
  "equivalence": {"meaning": null, "timing": null, "role": null, "source_parity": null, "resolved_dissent": null},
  "gold": {"decision": null, "field": null, "current_or_unknown": null, "evidence_refs": [],
           "quoted_source_spans": [], "policy_revision": null, "recipient": null, "why": null}
}
```

**2. Cam kết thiết kế và kiểm quyền.** Tạo canary bằng byte tổng hợp trong từng vùng để thử ACL trước khi đưa ca thật vào. Đăng nhập đúng từng tài khoản dự kiến. Thử runner đọc inputs, ghi output mới, thử đọc canary trong sealed và ghi đè canary đã khóa. Người chấm chỉ đọc packet được giao. Developer thử đọc sealed và mapping. Người giữ digest đọc cam kết, xác minh bản phục hồi. Ghi kết quả thực tế cho từng phép cùng lý do nếu bỏ qua. Nếu một quyền đọc/ghi vượt mức hoặc chưa có lần thử thật, giữ trạng thái chờ. Không đưa tên người, đường dẫn thật hoặc thông tin đăng nhập vào báo cáo công khai.

```json
{
  "protocol_revision": null, "checkout": null, "input_digest": null, "projection_digest": null,
  "algorithms_manifest_digest": null, "scorer_digest": null, "rubric_commitment": null,
  "pair_mapping_commitment": null, "gold_commitment": null, "order_commitment": null,
  "sealed_at_utc": null, "second_holder_receipt": null, "restore_check": null,
  "access_tests": [{"role": null, "zone": null, "operation": null, "expected": null,
                    "observed": null, "time_utc": null, "receipt_ref": null}]
}
```

Để hai người băm lại giống nhau, với mỗi tệp kín sinh 32 byte nonce ngẫu nhiên riêng. Tính SHA-256 trên nonce thô nối ngay trước byte tệp gốc. Custodian giữ nonce và tệp riêng trong sealed/. Người thứ hai giữ cam kết digest và thời gian trước khi phát. Các hash nguồn LF trong bảng code dùng quy tắc riêng đã mô tả. Sau khi khóa lần trả lời đầu của cả ba nhánh, người giữ thẩm quyền kiểm lại cam kết trước khi mở gold cho scorer.

**3. Dòng dự đoán và dòng chấm.** Lưu một bản ghi kết quả đầu theo mỗi lần phân công. Dùng một trong các trạng thái returned, malformed, exception, timeout hoặc no_response. Ba nhánh có 72 vị trí kể cả khi runner hỏng. Chỉ chuyển sang người chấm bản kết quả đã bỏ tên nhánh và đóng gói đúng ID. Từng ô rubric nhận pass, fail, missing hoặc not_applicable kèm lý do. Bất đồng được giữ cả ý kiến ban đầu và kết quả phân xử.

```json
{
  "first_run": {"card_id": null, "blind_run_ref": null, "input_digest": null, "algorithm_digest": null,
                "started_utc": null, "ended_utc": null, "status": null, "raw_output_or_error_ref": null,
                "raw_digest": null, "capture_receipt": null},
  "blind_grade": {"grade_packet": null, "reviewer_ref": null, "decision_and_field": null,
                  "current_value": null, "evidence_span_and_ref": null, "policy_revision_and_validity": null,
                  "authority_and_scope": null, "recipient": null, "ask_necessary_and_useful": null,
                  "escalation_useful": null, "rationale_refs": [], "dissent_ref": null, "adjudicated": null}
}
```

**4. Báo cáo tổng hợp.** Lập cùng bảng cho hai control và candidate. Bên cạnh hiệu số tổng đúng, ghi từng hiệu số theo VI, EN và số gia đình đổi kết quả. Để diễn tả độ bất định thăm dò, có thể báo khoảng bootstrap 95% đã đăng ký trước sau khi khóa design. Mỗi lần lấy có hoàn lại 6 họ RFQ và 6 họ lịch dịch vụ, giữ nguyên cả hai ngôn ngữ và cả ba nhánh trong từng họ. Tính tỷ lệ đúng của candidate và từng control, hiệu số tỷ lệ theo từng cặp nhánh. Dùng 10.000 mẫu, seed 62 và hai phân vị 2,5%/97,5% theo nội suy tuyến tính. Báo phương pháp, seed, số họ và khoảng riêng cho từng hiệu số. Mẫu nhỏ và chủ đích chỉ hỗ trợ phân tích nội bộ. Gate O-09 vẫn dùng số đếm trên mẫu gốc đã đăng ký. CI phần mềm công khai chỉ chạy fixture phát triển. Custodian chạy scoring kín ngoại tuyến và giữ log cùng digest để reviewer có quyền đối chiếu.

```json
{
  "cohort_status": "unsealed", "count_families_assigned": 0, "count_cards_assigned": 0,
  "arm_summary_template": {"arm": null, "exact": null, "assigned": null, "unsafe_ready": null,
    "invalid_or_missing": null, "extra_asks": null, "unhelpful_escalations": null, "scope_authority_errors": null,
    "by_locale": {}, "by_journey": {}, "by_expected_action": {}, "paired_outcomes": {}},
  "paired_difference_vs_each_control": [], "paired_interval_method": null, "receipt_refs": [],
  "newly_correct_fully_grounded": null, "new_asks_blind_accepted": null, "dissent_count": null,
  "rework_minutes": null, "cost_per_accepted": null, "gate": "pending_independent_custody"
}
```
