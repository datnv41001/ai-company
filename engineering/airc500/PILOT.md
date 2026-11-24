# Pilot AIRC trên nguồn Marketing tổng hợp

## Kết quả lần chạy đã bàn giao

[Hồ sơ đầy đủ](evidence/qwen-marketing-01/REPORT.md) · [Các kết luận, lập luận và số liệu](evidence/qwen-marketing-01/results.json) · [19 lượt inference và bằng chứng](evidence/qwen-marketing-01/index.json).

Pilot tạo hai commit thật trong một Git repo tạm để mô phỏng PR Marketing. Base `6f23449c5a3467ddcb5e8e773c40768837d5bbc5`, head `a381db60e8b539b3cdd06c0bee343b3348f204c4`. Cấu hình targeted dùng **9 reviewer ID**, gồm tám chuyên viên mù, hai lượt phân lại cho chuyên viên thuộc miền khác và một trọng tài. Baseline dùng **một** ID, tám lượt mù với cùng seed, phân vùng ca và giới hạn token như tám lượt mù của targeted. Hai run dùng cùng Qwen2.5-0.5B-Instruct Q4_K_M. Việc chọn nhiều chuyên môn trên model này chỉ thay đổi câu hỏi và độ phủ.

| Phép đo | Targeted | Một reviewer |
|---|---:|---:|
| Lượt inference thực / receipt được nhận | 11 / 11 | 8 / 8 |
| Token input / output | 4.473 / 2.419 | 2.960 / 2.025 |
| Precision, recall, FPR của candidate | 50%, 50%, 50% | 50%, 100%, 100% |
| Phát hiện P1 trên ba unit P1 có lỗi | 2/3 | 3/3 |
| Candidate có đúng dòng và chênh lệch xác nhận được | 2/4 | 10/20 |
| Duplicate, đếm trên candidate trước xác minh | 0/4 | 12/20 |
| Verified unit có đề xuất sửa nêu đúng giá trị cần thay | 0/2 | 0/4 |
| Phí dịch vụ model / unique verified finding | 0 USD / 2 = 0 USD | 0 USD / 4 = 0 USD |

Đối chứng xác nhận H01 (giá vé) và H04 (số khách) trong targeted. H05 và H08 bị bỏ sót. Qwen đảo giá trị được duyệt và giá trị đăng trong lời giải thích của cả hai finding đúng, đồng thời đề xuất giữ nguyên. Phần trăm ở đây đo theo unit trên 4 ca lỗi và 4 ca sạch có oracle xác định trước; mức tin cậy chuyên gia, hiệu quả trên người dùng thật, điện năng và giá giờ máy chưa được đo. Báo cáo lưu nhãn deterministic riêng; bộ này có 0 nhãn do nghiệp vụ con người hoặc AI phân xử.

Không xuất hiện thiểu số reviewer đúng bị ít nhất hai reviewer thật bác trong lần chạy này. Để kiểm chứng quy tắc quyết định, lượt trọng tài thật còn nhận ba phát biểu từ **fixture biên soạn** sau blind seal. Hai phát biểu nói giá khớp, một phát biểu có hai dòng Git chứng minh USD 18/12. Verifier độc lập giữ lập luận thiểu số có căn cứ và lưu quan điểm `insufficient` của chính Qwen. Regression riêng kiểm cùng tính chất trên input mô phỏng có nhãn.

## Chạy lại trên máy mới

Cần Python 3.12 và Git. Dùng venv engineering riêng và cài dependency:

```sh
python -m pip install -r engineering/airc500/requirements-pilot.txt
python -m unittest discover -s engineering/airc500 -p "test_*.py" -v
python engineering/airc500/pilot.py verify --out engineering/airc500/evidence/qwen-marketing-01 --trust-sha256 400f86483df5c4521ace9c26c5f83975f2e45415d56c8af1a6e684e259948ca9 --archive-sha256 dacc572f1d25c18c491c0c6364111603a2038dab13e8d89df0d6997f147a6167
```

Hash registry public và hash index bên trên là hai mốc review của lần chạy này. Verifier kiểm toàn bộ file public, chain journal, epoch, seal, assignment, Ed25519, bytes trả về, usage, pha trao đổi, từng locator và các chỉ số. Kiểm chứng offline không cần model, quyền ghi GitHub hoặc database AMC. Git phải được phép khởi tạo repo tạm. Trên máy Windows bị giới hạn thư mục Temp, đặt `$env:TEMP` và `$env:TMP` thành đường dẫn tuyệt đối tới một thư mục tạm có quyền ghi trong workspace.

Để chạy **inference mới**, chuẩn bị llama.cpp `llama-server` và GGUF Qwen theo [script kiểm checksum của AMC](../../scripts/fetch_workforce_model.py). Tập tin weights bắt buộc khớp SHA-256 `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`. Lệnh dưới đây cần thư mục output mới; sửa hai đường dẫn theo máy.

```sh
python engineering/airc500/pilot.py run --model /path/to/model.gguf --server /path/to/llama-server --out .local/airc-new
```

Adapter tự khởi động một process chỉ nghe loopback, ghi hash binary và weights, đối chiếu token từ template thật và khóa phiên bản model trước lượt gọi. File chứa key transport tạm nằm trong thư mục riêng và bị xóa khi process dừng. Khóa ký Ed25519 chỉ ở bộ nhớ. Giới hạn của run là 45 phút, 90 giây mỗi attempt, 3.000 input, 1.000 output, tổng tối đa 88.000 token, concurrency 1 và phí model trả ngoài bằng 0. Giới hạn output cấu hình cho fixture là 720 token. Một lỗi định dạng có usage đã đối soát được thử lại tối đa một lần. Khi mất ACK, journal giữ phần phơi nhiễm và ghi báo cáo incomplete.

Nếu cần hủy, dùng `python engineering/airc500/pilot.py cancel --group .local/airc-new/targeted` ở terminal khác. Khi coordinator cũ đã dừng, dùng `python engineering/airc500/pilot.py recover --group .local/airc-new/targeted` để replay checkpoint và fence run bị gián đoạn. Khóa adapter tạm kết thúc theo process; lần chạy mới nhận run ID mới. Lượt đến trễ chỉ đối soát ledger. Hồ sơ `incomplete.json` và SQLite private journal ở máy chạy cho biết reservation đang mở, người đã tham gia và phạm vi còn thiếu.

## Ranh giới thực thi và bàn giao

Importer chấp nhận đúng hai Git blob dạng tệp thường; broker chỉ phát các field và dòng theo domain bị ảnh hưởng. Cùng domain có cả ca sạch. Casebook công khai này dành cho kiểm tra engineering; muốn đo khả năng tổng quát phải thay bằng holdout kín do người độc lập quản lý. Phiếu reviewer chỉ chứa nhận định, hai locator, lý do và đề xuất. Challenger được xem packet đã seal của miền khác. Verifier xác minh độc lập bằng giá trị thực trong Git và chữ ký adapter. Trọng tài nhận evidence và các quan điểm còn tranh chấp, không có quyền đặt verified. Khi giá trị trong nguồn/thực tế đổi SHA, phải cấp run mới. Phân biệt các vai trò bằng capability và mã tin cậy của pilot; bảo vệ host, phân quyền giữa nhiều process và custody khóa dài hạn là công việc trước khi mở vận hành nhiều máy.

`calls.jsonl` lưu request thực và raw response dạng base64 để bảo toàn bytes, `events.json` là bản xuất journal, `normalized.jsonl` gồm các bản ghi wire được schema xác nhận. Phần mềm cung cấp một candidate ban đầu và disposition có đối chứng tách riêng trong `results.json`. Muốn đổi điều khoản/claim sau khi sửa fixture, tạo run mới; giữ nguyên run cũ để so sánh. Rollback bằng dừng adapter và trở lại revision tooling cũ. Thư mục evidence chỉ có dữ liệu tổng hợp, public key và hash.

Pilot chỉ đọc fixture. Backlog mở rộng là review nguồn Marketing có quyền, thêm corpus đủ cỡ mẫu, và chất lượng lập luận/đề xuất sửa. Scale 25–50 sau khi qua thử phục hồi và tái lập điểm trên holdout, 100–150 sau khi đo fairness/quota và chất lượng theo family, đủ 500 sau khi có phê duyệt ngân sách và đủ 500 ID có output/receipt hợp lệ trên một run. Kết luận commercial GA hiện giữ NO-GO.
