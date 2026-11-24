# AIRC-500 · Đề xuất hội đồng kiểm định độc lập của AMC

**Trạng thái ngày 24/11/2026:** thiết kế để phản biện nội bộ. Mốc đối chiếu AMC là `ece8ecc84b4938900821ff85403bb5b8243534c6`, schema sản phẩm v18. Commercial GA giữ quyết định **NO-GO** theo [release gates](../../docs/SECURITY_AND_GA_BLOCKERS.md). PR #16 tiếp tục theo phạm vi riêng.

Hội đồng trả lời ba câu hỏi cho Product Owner: bản sửa ảnh hưởng ai, bằng chứng nào thay đổi được quyết định, và Codex cần sửa hoặc kiểm thử điều gì. Một dịch vụ điều phối của nhóm engineering sẽ tự lập lịch theo rủi ro. Product Owner giữ quyền quyết định ngân sách, phạm vi sản phẩm và phát hành.

| Tài liệu / dữ liệu | Dùng để làm gì |
|---|---|
| [Catalog 500 reviewer](reviewers.jsonl) · [nguồn biên soạn](disciplines.json) | Tra từng ID, nhiệm vụ, rubric, nguồn, quyền và hợp đồng kết quả |
| [Hợp đồng thực thi](CONTRACTS.md) · [JSON Schema](contracts.schema.json) | Implementer của coordinator, broker, verifier và report dùng chung ngữ nghĩa |
| [Ngân sách và lập lịch](COST.md) | Admission, giới hạn tài nguyên và đối soát khi timeout |
| [Threat model](THREAT-MODEL.md) | Quyền đọc, phân vùng, gốc tin cậy và tình huống mất độc lập |
| [Kế hoạch kiểm định](EVALUATION.md) | Fixture có nhãn, chỉ số, test chấp nhận và điều kiện chuyển giai đoạn |
| [Mẫu báo cáo hợp nhất](REPORT.md) | Mẫu bàn giao 15 mục kèm trạng thái thực của lần soạn thiết kế |

## Ranh giới kiến trúc

Engineering vận hành coordinator và kho bằng chứng riêng. Importer được cấp quyền Git **đọc** để xác minh repo, số PR, hai commit và quan hệ tổ tiên. Nó xuất manifest theo blob và dòng mã, cùng diff, hai phía của rename/delete và dependency graph. Bộ lọc loại dữ liệu ngoài phạm vi trước khi tạo bundle. Worker không nhận checkout có quyền ghi, token GitHub, socket Docker, URL database AMC hay quyền shell. Adapter model nội bộ nhận duy nhất bundle của một assignment. Nghiên cứu dùng kho trích dẫn chính thức đã duyệt, có phiên bản, ngày và nguồn. Khi thiếu tài liệu, reviewer gửi yêu cầu evidence đến broker.

| Thành phần và chủ thể tin cậy | Đọc | Được ghi |
|---|---|---|
| Importer / evidence broker | Git objects đã pin, test attestation hoặc trích dẫn đã duyệt | Source manifest, bundle theo assignment |
| Planner / coordinator | Manifest, catalog lock, ownership, policy, hạn mức | Kế hoạch, lease, reservation và checkpoint trong kho engineering |
| Reviewer / adapter | Bundle được cấp; packet phản biện chỉ sau khi mở vòng | Câu trả lời qua hộp thư nội bộ của assignment; adapter ghi receipt riêng |
| Test service | Fixture tổng hợp và chương trình test đã duyệt, cố định digest | Attestation ký riêng, artifact có thời hạn |
| Verifier / arbitration | Hồ sơ niêm phong, đối chứng và chứng cứ broker cấp | Quyết định theo finding, liên kết duplicate, dissent |
| Reporter | Sổ sự kiện và disposition đã khóa | Báo cáo và đầu việc dạng draft cho người triển khai |

**Triển khai đề xuất.** Một kho content-addressed lưu bundle, output gốc và artifact. Journal giao dịch riêng lưu run, event, lease, reservation, cursor. Worker không có đường ghi vào hai kho này. Coordinator kiểm tra khóa và nguyên tử hóa các chuyển trạng thái quan trọng. Bản pilot có thể dùng một process và SQLite cho journal một máy. Trước khi chạy nhiều dispatcher, thay journal bằng DB engineering có khóa giao dịch và kiểm thử cạnh tranh. Docker dùng cho test service với image pin digest, filesystem nguồn chỉ đọc, thư mục scratch có quota và mạng mặc định đóng. Toàn bộ có thể dừng bằng cách ngừng coordinator. Ứng dụng Marketing tiếp tục chạy độc lập.

## Chọn reviewer

1. Lập danh sách đường dẫn thay đổi, symbol/contract được chạm và các consumer trực tiếp/bắc cầu trong manifest. Ghi cả tác động nghiệp vụ như client nhìn thấy gì và chi phí được ghi cho ai. Đường dẫn chưa phân loại phải xuất hiện trong coverage gaps. Thiếu graph hoặc owner ở vùng nhạy cảm nâng mức rủi ro và cần người xác nhận trước khi kết luận đủ phạm vi.
2. Bản đồ phiên bản đầu gắn `app/identity*` và migrations quyền với identity, UX disclosure, privacy và QA; delivery/QA với snapshot, content claims, UX state và khách hàng; registry/worker với contract AI, budget, recovery và integration; thay đổi frontend với nhiệm vụ màn hình, accessibility và API tiêu thụ; spec với PM và discipline sở hữu điều khoản. Các rule này dùng **symbol và dependency** để bổ sung cho path. Một thay đổi vô hại trong tài liệu có thể dùng PM + chủ thể chuyên môn. Một thay đổi thay quyền, tác động tiền hoặc dữ liệu lịch sử luôn là high trở lên.
3. Low chọn 2–4 ID cho các nghĩa vụ bằng chứng. Medium chọn 5–12, gồm một người phản chứng. High chọn 12–30 với ít nhất một reviewer cho từng ranh giới bị ảnh hưởng, một người kiểm chứng riêng và arbitration khi còn tranh chấp. Critical hoặc nghiệm thu V1 đề xuất full mode. Với targeted, nếu số nghĩa vụ vượt trần, tách thành các batch cùng run hoặc báo thiếu coverage để chủ run quyết định. Budget và deadline là giới hạn cứng.
4. Trong mỗi nghĩa vụ, ưu tiên đúng subject, lens bù điểm mù, quyền tối thiểu, lịch sử chất lượng trên fixture tương ứng và model family khác nếu có. Khi hòa dùng ID ổn định. Ghi các ID được chọn/bỏ, lý do, model family thực có và phần thiếu. Full mode phân 490 chuyên viên đánh giá mù và 10 trọng tài thẩm định hồ sơ sau niêm phong. Không có tranh chấp, trọng tài vẫn có thể thẩm định coverage và điều kiện quyết định. Chỉ báo “500 đã tham gia” khi có đủ 500 ID với output được chấp nhận.
5. Ví dụ, đổi quyền đọc bản giao của hai khách trong cùng agency sẽ kéo `SP-006` (ma trận quyền khách), `SP-007` (cặp ca cho phép/bị giới hạn), `PM-011` (đường duyệt của khách), `SE-021` (contract khi cạnh tranh), `QT-032` (đối chứng oracle) vào danh sách cùng các consumer và reviewer còn lại theo high. Bản đồ phải ghi quan hệ từ đầu vào tới bản giao, không tự suy ra mọi file trong repo đã được xét.

## Catalog và nguồn cho phép

100 chủ đề có invariant và phép đối chiếu riêng. Mỗi chủ đề kết hợp với 5 phương pháp **của chính discipline**. Ví dụ, `MK-021` đối chiếu claim về hiện vật với mục tiêu brief, `MK-022` phải chỉ ra cặp câu nguồn và claim, còn `MK-025` đưa cách diễn giải khác theo phân khúc. Điểm rubric 4/3/3 phản ánh invariant, phép kiểm chứng và chất lượng deliverable. Rubric định hướng công việc; verifier vẫn cần chứng cứ để xác nhận một finding.

| Prefix | Discipline | Số ID | Prefix | Discipline | Số ID |
|---|---|---:|---|---|---:|
| PM | Product & Market | 50 | MK | Marketing Domain | 100 |
| SE | Software Engineering | 70 | AI | AI & Multi-Agent | 50 |
| SP | Security & Privacy | 50 | UX | UX/UI & Usability | 40 |
| QT | QA & Testing | 40 | BF | Business & Finance | 30 |
| LC | Legal & Compliance | 20 | IO | Infrastructure & Operations | 25 |
| ID | Integration & Data | 15 | AR | Independent Final Arbitration | 10 |

`source` và `registry` là blob được pin. `charter`, `policy`, `marketing`, `approved_reference` là trích đoạn có chủ sở hữu và locator. `journey`, `workflow`, `finance` là trace tổng hợp đã lọc. `render` là ảnh hoặc cây accessibility đã lọc. `test` là kết quả fixture được test service chứng thực. `sealed_case` là packet tranh luận có ACL riêng. Catalog khai báo quyền tối đa. Grant thực là giao của catalog, run, assignment, phase và ACL từng artifact.

## Quyết định tái sử dụng

| Cơ chế AMC đã đọc | Quyết định cho AIRC |
|---|---|
| [Registry fingerprint](../../migrations/registry_release.py), [kiểm tra tương thích](../../app/registry_compatibility.py) | Pin catalog, rubric, policy và phiên bản model trong manifest. Catalog engineering có vòng đời riêng với catalog vai trò Marketing. |
| [Dispatcher](../../app/pool_dispatch.py), [DAG](../../app/workflow_dag.py), [scheduler telemetry](../../app/scheduler_telemetry.py) | Áp dụng nguyên tắc claim, scope, lease và lý do chờ. Không cấp worker hội đồng quyền gọi dispatcher nghiệp vụ. |
| [Ledger](../../migrations/009_company_operations.sql), [đối soát](../../app/operations.py) | Dùng mẫu reserve/settle/reconcile với account engineering riêng. Chi phí review không vào sổ khách hàng. |
| [QA revision](../../app/revision_qa.py), [quyết định snapshot](../../docs/ADR-007-QA-EVIDENCE-REVISION.md) | Mượn nguyên tắc quyết định gắn phiên bản. Finding pin hai SHA và lần chạy, một lần review mới có run ID mới dù cùng tree. |
| [Bộ chấm mù](../../docs/reviews/landing-qa-eval/evaluate.py), [kết quả hội đồng AI trước đây](../../docs/reviews/ai-panel-20261124/README.md) | Dùng lại ý tưởng digest của corpus, blind book và so nhãn theo đơn vị. Ghi nguồn nhãn, tương quan model và giới hạn ngoại suy. |
| [Product charter](../../docs/PRODUCT_SPEC_V1.md), [ADR nền tảng](../../docs/ADR-001-OWN-SaaS-CORE.md), [reuse survey](../../docs/GITHUB_RESEARCH_AND_REUSE.md), [handoff](../../docs/CODEX_LOCAL_HANDOFF.md) | Giữ quyền quyết định của con người và một bộ gate thương mại cho V1. Không thêm dependency runtime bên thứ ba trong đề xuất này. |

## Tiếp quản trên máy mới

Từ thư mục gốc repo, dùng Python 3.12. Catalog và phép kiểm tra cơ bản chỉ dùng thư viện chuẩn.

```sh
python engineering/airc500/catalog.py
python -m unittest discover -s engineering/airc500 -p "test_design.py" -v
```

Để sửa một chuyên môn, chỉnh [disciplines.json](disciplines.json), chạy `python engineering/airc500/catalog.py --write` rồi chạy lại hai lệnh trên. Giữ ID ổn định khi cập nhật nội dung. Không đổi thứ tự subject/lens trong catalog v1 đã dùng để review. Một lần phân bổ lại cần catalog version mới, bảng ánh xạ và lưu manifest cũ. [Kiểm tra JSON Schema và các ca nghiệm thu](EVALUATION.md).

## Lộ trình và quyền quyết định

| Bước độc lập với roadmap Marketing | Điều kiện kết thúc | Người chịu trách nhiệm |
|---|---|---|
| A · duyệt thiết kế hiện tại | Kiểm tra đủ catalog, hợp đồng, economics, threat model, test plan và dissent về thiết kế | Engineering owner |
| B · importer, journal, broker và sealed blind review local | Một PR tổng hợp, một model local pin digest, thử từ chối receipt sai, mất điện và hủy sau reserve | Tooling maintainer và verifier độc lập |
| C · peer exchange, arbitration và report | Khép vòng dissent hoặc chuyển chủ thể có thẩm quyền với evidence; đo pilot trên holdout | Evaluation owner |
| D · full-council rehearsal theo yêu cầu | Đủ attestation thật, ngân sách và kiểm thử hồi phục; công bố coverage và chi phí thực | Engineering và chủ ngân sách |

Bước B–D là backlog engineering riêng. Không đưa AIRC vào required check của các PR Marketing trong giai đoạn này. Rollback thiết kế bằng cách revert riêng thư mục và liên kết bàn giao. Không có migration, dữ liệu khách hoặc quyền sản phẩm cần phục hồi.
