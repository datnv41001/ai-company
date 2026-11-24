# Bắt đầu ở đây khi tiếp quản AI Marketing Company

## Review Scheduler Wait Diagnostics

Nhánh xuất phát từ `3af08b75b661e1d1681a5825939f7ce8656746b8`. Nhánh độc lập này dành số migration 16 cho chẩn đoán và chạy trực tiếp từ v14. PR WF-03 dành số 15. Trước lần merge thứ hai cần hợp nhất thứ tự migration, kiểm tra nâng từ cả hai trạng thái đang triển khai và cập nhật fingerprint cho cây mã kết hợp.

Trong DB dev, khởi động Compose và cấp các LOGIN riêng theo [runbook pool](docs/POOL-RUNBOOK.md). Khai báo danh sách đầy đủ dispatcher của **database này** bằng tài khoản migrate. Với cấu hình mẫu có đúng một dispatcher, chạy lệnh sau sau khi đã tạo LOGIN.

```sh
docker compose run --rm migrate python scripts/provision_pool.py inventory amc_ops_dispatch
```

Mỗi replica dùng LOGIN riêng. Truyền tên của tất cả replica vào lệnh inventory khi thay đổi pool. Dispatcher và worker tự báo heartbeat khoảng 3 giây/lần cùng fingerprint và capability. Dữ liệu tối đa 15 giây tuổi mới được dùng để kết luận thiếu adapter. Phiên dispatcher còn kết nối nhưng thiếu heartbeat, LOGIN dự kiến vắng mặt hoặc chưa khai báo danh sách cho kết quả `telemetry_unknown`. Worker bận được nhận diện qua lease dù không poll trong lúc suy luận. Khi bộ dựng yêu cầu của dispatcher khác fingerprint với API, phép tính ngân sách được đánh dấu chưa đủ dữ liệu.

Owner/admin mở **Điều phối Marketing AI → Xem kết quả và chi phí → Xem lý do node chờ**. API `GET /api/tenants/{tenant}/workforce/runs/{run}/wait-diagnostics` đọc một snapshot PostgreSQL cho các node cùng run/revision. Trường `candidate` đối chiếu tập ứng viên SQL của scheduler. Bước cấp offer còn đối chiếu runtime, ngân sách node/run/agency và lease dưới khóa scheduler. Một report có thể chờ adapter sau khi worker đã gửi. Giao diện trả thời điểm quan sát để nhận biết dữ liệu đã cũ. Client A/B và tài khoản tenant khác không có quyền đọc chẩn đoán.

RED tại `47f47cd` cho thấy API trả 404 cho quản trị viên. Chạy `python -m pytest -q tests/test_wait_diagnostics.py` với DB tổng hợp và môi trường PostgreSQL trong CI. Có ca READ ONLY, so ứng viên với offer thực, heartbeat hết hạn, report còn giữ, nhiều lý do đồng thời và thu hồi quyền qua suite chung. Job model ghi `wait-diagnostics-measurements.json` trong lần chạy Qwen có snapshot khách mẫu duyệt. Khi rút, tắt truy cập vào chẩn đoán và trả về image tương thích sau khi drain. Giữ bảng telemetry trong schema 16 để tiếp tục đối chiếu. Thay đổi inventory và heartbeat chỉ ghi bảng vận hành riêng.

## Main sau PR #11 · QA Content và SEO cho bản nháp landing

Ngày 24/11/2026, [PR #11](https://github.com/datnv41001/ai-company/pull/11) đã merge tại [`576b81798de148b75a6e74dd584551049dc5be9f`](https://github.com/datnv41001/ai-company/commit/576b81798de148b75a6e74dd584551049dc5be9f). Hai parent là base `4c588d8cbadc6e83da7a33e7977d12815673f663` và head đã review `a982b1efff9b323b3b0c6fed8d9138f5475f6a2c`. Cả merge và head có cùng Git tree `21a810d5e20b735936fcb62ce93b2c21346311ca`. Phạm vi phát hành là phát triển nội bộ trên dữ liệu tổng hợp. PostgreSQL dùng schema v14.

| Kiểm tra trên chính commit merge | Kết quả |
| --- | --- |
| [API và nâng PostgreSQL](https://github.com/datnv41001/ai-company/actions/runs/45326058065/job/138215820740) | Ruff đạt. 178/178 bài kiểm thử đạt, gồm phân quyền khách A/B cùng agency và RLS. Cả 13 đường nâng v1–v13 có dữ liệu lên v14, chạy lặp và kiểm tra cô lập khách đều đạt. |
| [Compose và Chromium](https://github.com/datnv41001/ai-company/actions/runs/45326058065/job/138215820324) | Mở được finding trên desktop 1280 px và mobile 390 px. Cả hai chặn phê duyệt cũ sau A → B → A. |
| [Qwen local](https://github.com/datnv41001/ai-company/actions/runs/45326058065/job/138215820774) | Director, Content và SEO thành công ngay lượt đầu (3/3). Tổng 1.032 token vào, 320 ra, 0 lượt chưa xác nhận usage, 0 micro-USD đang giữ hoặc ước tính. Một snapshot được khách mẫu duyệt. |

Artifact `role-qa-measurements.json` ghi 2 finding Content và 1 finding SEO. Digest của Content tiền nhiệm trong report SEO khớp digest đầu ra của node Content. Người QA vẫn phải duyệt đúng revision và digest trước khi chia sẻ, kể cả khi một node có 0 finding. Quyết định của khách gắn với snapshot đã chia sẻ. [Artifact trên commit merge](https://github.com/datnv41001/ai-company/actions/runs/45326058065/artifacts/14890391288) · [CI 3/3](https://github.com/datnv41001/ai-company/actions/runs/45326058065).

### Manifest, kiểm kê và rollback

[Manifest](catalog/landing-seo-v4.json) là `WF-13/landing-seo-draft@4`, có digest `f47ddd7984fc1aa9d4fe3ba325ce917b49e8cfa4d504debd1ad8d7bb58003c9a`. Ba adapter bắt buộc là `director@1`, `content@2` và `seo@3`. Hai adapter tùy chọn là `research@1` và `strategy@1`. QA của hai node mới lần lượt là `content-qa@2` và `seo-qa@2`.

| Runtime đã đo | Fingerprint trong danh sách cấp phép |
| --- | --- |
| Linux CPython 3.12.16, job Qwen của bản merge | `ac80f043fbb40efd0463a64f90db6d7829af99d64ecc5971dfd3d71c38a164a3` |
| Windows CPython 3.12.14, checkout bản merge | `dc3fae426d39398508787d5ddb74fad2612bd4bafa901485abc48b1f1a1c1d9a` |

Trên checkout Windows, đối chiếu cả 5 hợp đồng với runtime đã cấp phép thành công. Digest tương ứng là `c64cf3e0…` cho ba vai trò phiên bản 1, `033be980…` cho Content 2 và `8bf22c4a…` cho SEO 3. Runtime còn nhận các hợp đồng Content/SEO lịch sử, trong đó `seo@2` ghim `3ab7030b…`. [Fingerprint và digest đầy đủ](migrations/registry-runtime.lock.json).

Kiểm kê chỉ đọc trên ba DB dev tổng hợp `amc_company_pool_dev` (v10), `amc_diamond_dev` (v11) và `amc_parallel_dev` (v13) cho kết quả mỗi DB có 0 run pool hoạt động, 0 adapter ghim cho run hoạt động và 0 attempt mở. Lần chạy @4 được xác minh trong DB thử riêng của CI. Ba DB dev cũ vẫn ở phiên bản nêu trên.

1. Trước khi bật `@4` ở một pool khác, kiểm tra schema v14. Chạy lại truy vấn kiểm kê và lệnh Compose trong [quy trình kiểm tra từng replica](#trước-khi-kích-hoạt-một-phiên-bản-adapter) trên đúng pool. Đối chiếu adapter **và** digest cho toàn bộ run/report còn việc, kể cả run cũ, với fingerprint và adapter thực tế của các dispatcher. Kiểm tra worker và route cho campaign. Nếu thiếu replica tương thích, khôi phục image đã duyệt rồi chạy brief tổng hợp trước khi cấp grant `@4`.
2. Khi rút tính năng, chọn **Ngừng cấp mới** cho `@4` và giao brief tiếp theo qua phiên bản `@1` được campaign cấp phép. Giữ dispatcher và worker tương thích với từng phiên bản đang chạy cho tới khi run hoàn tất, report đã tiêu thụ, lease đã đóng và hold/receipt đã đối soát. Giữ các policy ghim, checkpoint, ledger và snapshot lịch sử để tiếp tục truy vết. [Công cụ xuất bản manifest trên DB thử](migrations/registry_release.py).

### Đánh giá nghiệp vụ và công việc tiếp theo

Bộ chấm mù gồm 4 brief giả lập mới với 12 ca Content và 12 ca SEO, độc lập với 16 fixture hồi quy. Có ca diễn đạt lại, phủ định, chỉ dẫn thương hiệu trong văn xuôi, trích dẫn thiếu ngữ cảnh và đối chiếu Anh–Việt. Người điều phối chỉ chuyển ZIP do lệnh đầu tạo cho reviewer. Reviewer đọc `REVIEWER.md`, ghi nhãn, rồi trả phiếu đã chốt trước khi xem báo cáo. Lệnh tạo ZIP chỉ dùng thư viện chuẩn Python.

```sh
python docs/reviews/landing-qa-eval/evaluate.py --packet --output landing-qa-blind.zip
python -m pip install -r requirements.txt
python docs/reviews/landing-qa-eval/evaluate.py --labels completed-labels.json --output independent-report.md
```

Khi tính điểm, dùng checkout này với Python 3.12.14 hoặc 3.12.16 và các dependency đã ghim tương ứng với fingerprint trong bảng. Dùng tên tệp đầu ra mới ở mỗi lần chạy. Mỗi bộ ba (ca, trường, rule) tính một lần. Báo cáo ghi TP, FP, FN, precision và recall theo role/rule cùng danh sách bất đồng. Mẫu số bằng 0 hiển thị `n/a`.

Hiện chưa có nhãn độc lập của reviewer nghiệp vụ. Theo nhãn kỹ thuật tạm của Codex, có 19 cảnh báo khớp, 14 cảnh báo thừa và 7 bị bỏ sót, tương ứng micro-precision 57,6% và micro-recall 73,1%. Ví dụ C02 là cảnh báo thừa trên một câu phủ định. B06 có ba cảnh báo thừa khi SEO tiếng Việt khớp nghĩa với bản Content tiếng Anh. Quy tắc `quote_context` của SEO chưa có ca dương theo nhãn tạm. Để nghiệm thu thương mại còn cần nhãn độc lập và đủ số ca dương cho các rule cần kết luận. [Báo cáo kỹ thuật theo rule](docs/reviews/landing-qa-eval/technical-report.md) · [Rubric chấm mù](docs/reviews/landing-qa-eval/REVIEWER.md).

Hai thiết kế kế tiếp có điều kiện nghiệm thu và rollback riêng. Một PR bổ sung tiểu quy trình Research → Strategy của WF-03. PR khác giúp vận hành phân biệt node chờ predecessor, runtime, worker, capacity hay budget. [Thiết kế và các tình huống kiểm thử](docs/POST-PR11-WORKFLOWS.md).

## Main sau PR #10 · Registry v14

[PR #10](https://github.com/datnv41001/ai-company/pull/10) đã merge vào `main` ngày 24/11/2026 tại [`d98533154ebe3f65dab3f7fb249115bc83420824`](https://github.com/datnv41001/ai-company/commit/d98533154ebe3f65dab3f7fb249115bc83420824). Hai parent lần lượt là `f283c6e9eef7054ec11d1aac20ed6971fa891499` và head được duyệt `a998ac65d8859c35642b5d678bc010bf095542ae`. Cây Git của bản merge và head trùng nhau tại `f7d2e31c6f0f450802399e0759a3721de18f2115`. Phạm vi nghiệm thu là phát triển nội bộ với PostgreSQL schema 14 và dữ liệu tổng hợp.

[CI của commit merge](https://github.com/datnv41001/ai-company/actions/runs/45322008549) đạt cả 3 job. Ruff và 156/156 bài SQLite/PostgreSQL/RLS đạt. Cả 13 đường nâng v1–v13 có dữ liệu lên v14, chạy lặp và kiểm tra cô lập khách hàng đều đạt. Chromium đạt ở 1280×850 và 390×844. [Log API và migration](https://github.com/datnv41001/ai-company/actions/runs/45322008549/job/138202530487) · [Log Docker và Chromium](https://github.com/datnv41001/ai-company/actions/runs/45322008549/job/138202530780).

Qwen local chuyển checkout ngay sau checkpoint Content. Run v1 tiếp tục với `seo@1`, giữ đúng manifest và plan digest đã ghim, dùng 994 token vào và 264 ra. Run v2 dùng `seo@2`, 1.007 token vào và 261 ra. Mỗi run hoàn thành ba attempt ngay lần đầu và có một snapshot được khách mẫu duyệt. [Job model](https://github.com/datnv41001/ai-company/actions/runs/45322008549/job/138202530811) · [Artifact chứa registry-rollout.json](https://github.com/datnv41001/ai-company/actions/runs/45322008549/artifacts/14887748205).

| Runtime đo tại bản merge | Fingerprint SHA-256 |
| --- | --- |
| CPython 3.12.16 trong job Qwen | `b73b9c3eca164532f03dd3ee3f5508ccd172e59ab0209ca079254bc786a182e9` |
| CPython 3.12.14 trên máy Windows thử | `9148f3773559f0c95c961e50db9ae8020dd3f5199cf0ae2b1de67c6a35cb112e` |

Mỗi hồ sơ cho phép digest `c64cf3e0…` của adapter v1 và `3ab7030b…` của `seo@2`. Phạm vi băm bao gồm mã runtime, catalog, migration, requirements cùng phiên bản Python và thư viện. Giao diện tĩnh và một số script nằm ngoài phạm vi này. Git và CI bảo vệ hồ sơ phát hành. Chữ ký phát hành độc lập và cảnh báo tự động khi pool thiếu adapter là hai việc còn mở. [Danh sách fingerprint và digest đầy đủ](migrations/registry-runtime.lock.json) · [Phép thử nhận diện](tests/test_adapter_fingerprint.py).

### Trước khi kích hoạt một phiên bản adapter

1. Tạm ngừng giao brief mới cho workflow liên quan. Liệt kê các run registry đang `queued` hoặc `running` và các hợp đồng chúng đã ghim theo truy vấn dưới đây. Với run có nhiều skill, dùng graph để xác định node đang chờ, node có report chưa được tiêu thụ và các bước còn lại.
2. Dùng [cấu hình pool nội bộ](docs/POOL-RUNBOOK.md) để thay những tiến trình cũ chưa kiểm tra fingerprint, sau khi xử lý các lease đang mở. Khởi động dispatcher và worker từ image đã kiểm thử. Kiểm tra **từng replica trên từng máy**. Ví dụ dưới đây đọc fingerprint và các adapter mà một dispatcher đang chạy có thể phân giải. Lặp lệnh với tên service và chỉ số tương ứng cho từng replica, kể cả `worker-one` và `worker-two`.

   ```sh
   docker compose -p amc-dev --env-file .env --env-file .env.pool -f compose.yaml -f compose.pool.yaml exec -T --index 1 dispatcher python -c "from migrations.runtime_bundle import runtime_fingerprint; from app.registry_adapters import runtimes; print(runtime_fingerprint(), {k:v.digest for k,v in runtimes().items()})"
   ```

3. Đối chiếu cặp `adapter` và `adapter_digest` từ run với kết quả trên và kiểm tra provider, timeout, route và worker sẵn sàng cho đúng campaign. Duy trì ít nhất một dispatcher tương thích trên pool phục vụ từng phiên bản còn việc. Chỉ kích hoạt phiên bản mới sau khi thay hết tiến trình cũ chưa có cơ chế kiểm tra và đã chạy thử một brief tổng hợp. Khi thiếu runtime, khôi phục image tương thích và tiếp tục từ checkpoint. Giữ dispatcher cũ **có cơ chế kiểm tra** đến khi run ghim nó kết thúc, report đã được tiêu thụ và hold đã được đối soát. Lần bàn giao này chỉ kích hoạt phiên bản mới bên trong fixture nghiệm thu.

### Kiểm kê sau merge

| Phạm vi đo riêng | Run đang chờ adapter | Khoản giữ chưa giải phóng | Snapshot khách mẫu đã duyệt |
| --- | --- | --- | --- |
| Ba pool dev local `amc_company_pool_dev` (v10), `amc_diamond_dev` (v11), `amc_parallel_dev` (v13) | 0 run pool đang hoạt động | 0 | 0 |
| Database tổng hợp ngay sau khi nâng từ v13 lên v14 và chạy lặp | 3 run pool legacy đang hoạt động, 0 run ghim registry | 1 offer chưa nhận giữ 400 micro-USD, 2 attempt đã gửi giữ tổng 700 micro-USD | 1 |
| Hai run registry trong bài Qwen của commit merge | 0, cả hai đã đến bước QA | 0 micro-USD, 0 attempt mở, usage của cả 6 lượt đã xác nhận | 2, mỗi run 1 bản |

Ba pool local được kiểm kê trong transaction chỉ đọc. Fixture migration có 3 khoản giữ tổng 1.100 micro-USD trong sổ cái thử. Số run có tổng `held + spent` lệch `reserved_microusd` là 0 ở cả bốn database local. Các khoản giữ của fixture được bảo toàn qua migration. [Fixture hai lease đã gửi](tests/registry_upgrade_fixture.py) · [Fixture offer và receipt](tests/financial_upgrade_fixture.py).

Để tái lập phép đo, chạy `python tests/check_postgres_upgrade.py --from-v13` trên một database thử trống riêng như trong [CI](.github/workflows/ci.yml). Chạy các truy vấn dưới đây bằng tài khoản vận hành trên DB thử, trong cùng một transaction. So danh sách hợp đồng của các run còn hoạt động với runtime và route ở bước trên. Trạng thái `queued` một mình chưa cho biết run đang chờ adapter, worker, ngân sách hay predecessor.

```sql
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT r.id, r.state, r.knowledge->'registry'->>'workflow' AS workflow,
       c.key AS skill, c.value->>'adapter' AS adapter,
       c.value->>'adapter_digest' AS adapter_digest
FROM workforce_runs r
CROSS JOIN LATERAL jsonb_each((r.knowledge->'registry'->'contracts')::jsonb) AS c
WHERE r.state IN ('queued', 'running')
ORDER BY r.id, c.key;

WITH balance AS (
  SELECT id, sum(held) AS amount FROM amc_ops.ledger GROUP BY id
)
SELECT a.status, count(*) AS attempts, sum(b.amount) AS held_microusd
FROM balance b JOIN amc_ops.attempts a USING (id)
WHERE b.amount > 0 GROUP BY a.status ORDER BY a.status;

SELECT count(*) AS approved_snapshots
FROM client_reviews s JOIN review_entries e
  ON (e.tenant_id, e.review_id, e.digest) = (s.tenant_id, s.id, s.digest)
WHERE e.kind = 'approved';
COMMIT;
```

### Đề xuất sau v14 · Workflow Marketing và QA theo vai trò

| Thứ tự đề xuất | Nội dung | Điều kiện đưa ra review |
| --- | --- | --- |
| 1. QA cho Content và SEO của bản nháp landing | Ghim phiên bản quy tắc theo node. Content kiểm tra CTA, nội dung đúng brief và claim có nguồn. SEO đối chiếu title, meta và search intent với đúng bản Content tiền nhiệm. Finding ghi rule, vị trí và nguồn để người QA quyết định. | Với từng role, dùng mẫu đạt, mẫu lỗi và nguồn của khách B trong cùng agency. Sửa nội dung A → B → A phải yêu cầu QA đúng revision. Chạy v1 đang dở song song với bản rule mới và đối chiếu snapshot cũ. |
| 2. Thử một tiểu quy trình của WF-03 Audit & Research | Marketing lead duyệt bộ brief tổng hợp. Research tách fact, giả thuyết và dữ liệu thiếu. Strategy nhận checkpoint Research, đề xuất KPI có đơn vị và cách đo. Director chỉ phân công các skill campaign được cấp. | Chạy một brief có đủ bằng chứng và một brief thiếu nguồn. Kiểm tra grant, thu hồi giữa hai node, retry, hold, QA người duyệt và snapshot. Ghi riêng số lượt, token và chất lượng theo rubric trên Qwen local. |
| 3. Mở rộng WF-13 và WF-11 theo đầu ra đã được duyệt | Với WF-13, đề xuất đặc tả form, tracking và giả thuyết A/B. Với WF-11, đề xuất bản audit từ tài liệu được cấp và danh sách thay đổi để người phụ trách duyệt. | Mỗi tiểu quy trình cần manifest, fingerprint đã review và E2E độc lập. Reviewer nghiệp vụ ký cho đúng phạm vi và phiên bản dựa trên fixture, CI và artifact. |

Ưu tiên vận hành đi kèm là đo thời gian chờ node/report theo phiên bản, xác định dispatcher tương thích còn hoạt động và cảnh báo khi số lượng về 0. Fixture cần phân biệt thiếu adapter với chờ ngân sách hoặc worker. Các workflow mẹ WF-13, WF-11 và bộ 37 vai trò vẫn chờ nghiệm thu thương mại theo [ma trận truy vết](docs/PR9-TRACEABILITY.md).

## Main sau PR #7 và #8 · PostgreSQL v13

Ngày 24/11/2026, main nhận lần lượt hai merge commit cho phát triển nội bộ trên dữ liệu tổng hợp.

| Mốc | Head được duyệt | Merge SHA trên main | Đường dẫn kiểm chứng |
| --- | --- | --- | --- |
| Director lập và đóng băng DAG, schema v12 | `677a0863` | `38cee8fc0da774ba4926db03966d3c2d9672c977` | [PR #7](https://github.com/datnv41001/ai-company/pull/7) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45307415696) |
| Hai lease theo node, schema v13 | `3cfe8d24` | `37f6804495b5cfcd98aa463e763e5fde0b821da1` | [PR #8](https://github.com/datnv41001/ai-company/pull/8) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45308565924) |

CI sau merge #7 đạt 3/3 job, 115/115 bài kiểm thử và 11/11 đường nâng lên v12. Sau khi đổi base #8 sang main, CI chạy lại trên candidate `89ea560353ce2479ba4fc21d1399101a8453d331`, có hai parent là merge #7 và head được duyệt của #8. Cả ba job đều đạt. Diff v12 → v13 của candidate và commit merge #8 trùng từng byte với bản đã review, gồm 20 tệp. Có thể đối chiếu bằng `git diff --binary --full-index 38cee8f 37f6804` và `git diff --binary --full-index 677a086 3cfe8d2`. [CI của candidate trên base mới](https://github.com/datnv41001/ai-company/actions/runs/45308032409).

CI trên chính merge #8 đạt 3/3 job và 124/124 bài kiểm thử. Cả 12 đường nâng PostgreSQL v1–v12 lên v13 đều chạy lại thành công trên dữ liệu mẫu. Chromium đạt ở 1280 px và 390 px. Trong phép đo hai node Content cùng run, có 197 mẫu quan sát thấy cả hai slot Qwen đang xử lý, trải dài 5,23 giây. Hai request chồng lấn 5,28 giây, dùng tổng 518 token vào và 185 token ra. Kết quả là một snapshot được khách mẫu duyệt. [Job PostgreSQL](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292737) · [Job Chromium](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292624) · [Job Qwen](https://github.com/datnv41001/ai-company/actions/runs/45308565924/job/138158292261).

Đã chạy riêng 9 ca của `tests/test_node_leases.py` từ merge #8 trên một PostgreSQL v13 dùng dữ liệu tổng hợp. Sau khi hoàn tất, truy vấn đối soát ghi nhận 27 pool run, 55 bút toán qua hai kỳ UTC, 0 run lệch số dư và 0 attempt còn mở sau khi dọn fixture.

### Sử dụng và đối soát hai lease

Migration 013 nâng PostgreSQL lên v13. Với brief mới, chọn **Director lập kế hoạch** rồi chọn **Số node tối đa cùng chạy → 2**. API nhận `{"workflow":"dynamic-v1","max_parallel_nodes":2,"budget_microusd":0}`. Cần hai worker LOGIN có route tới cùng campaign, capacity agency ít nhất 2 và đủ ngân sách. Mặc định một lease. Hai node được cấp việc khi từng node đã nhận đủ checkpoint của các bước tiền nhiệm. Màn hình tiến độ hiển thị node đang chạy và thời điểm thử lại.

Dispatcher kiểm tra đồng thời mức còn lại của run và hạn mức agency trong kỳ UTC, rồi ghi offer và khoản giữ trong cùng giao dịch. Khi hai yêu cầu mỗi bên cần 700 micro-USD trong khi chỉ còn 1.000, đúng một bên được cấp offer. Sau timeout hoặc thu hồi quyền, offer chưa nhận được nhả khoản giữ. Lượt đã gửi nhưng chưa xác nhận usage tiếp tục giữ tiền cho đến khi có receipt. Receipt phát lại phải giữ nguyên số dư. Receipt muộn hoặc hoàn tiền được hạch toán vào kỳ của attempt gốc. Để đối soát, chạy truy vấn so sánh `workforce_runs.reserved_microusd` với tổng `ledger.held + ledger.spent` trong [runbook pool](docs/POOL-RUNBOOK.md). Kết quả mong đợi là 0 run lệch số dư.

Mỗi lần cấp lease gắn với LOGIN, attempt, node, revision và deadline. Thu hồi quyền hoặc lỗi vĩnh viễn của một node bắt buộc làm mất hiệu lực các lease còn mở của run. Kết quả muộn được chặn trước khi ghi checkpoint. Join kiểm tra đủ đầu vào và chỉ ghi một bản giao trong cùng giao dịch với QA. [Quy tắc fencing và Join](docs/ADR-011-NODE-ATTEMPTS.md).

Để diễn tập trên máy khác, dùng Docker theo [runbook pool](docs/POOL-RUNBOOK.md). Chạy bài cạnh tranh trên DB thử với `python -m pytest -q tests/test_node_leases.py`. Trên DB sạch khác, chạy đủ mười hai đường nâng v1–v12 lên v13 và lặp migration. Job `workforce-model` dùng [Compose model hai slot](tests/compose_parallel_model.yaml) và [bài đo Qwen](tests/parallel_model_smoke.py). Xem lệnh dựng DB, model và cổng loopback động trong [workflow CI](.github/workflows/ci.yml). Artifact `parallel-measurements.json` chứa số lần lấy mẫu cả hai slot, thời gian chồng lấn lease và request, token thật, chi phí và số snapshot khách duyệt.

Trên máy local, 359 mẫu thấy cả hai slot Qwen xử lý cùng run, trải dài 13,55 giây. Hai lease chồng lấn 14,69 giây. Hai lượt Content dùng 518 token vào và 188 ra, đạt ngay lần đầu với chi phí local 0 micro-USD, tạo một snapshot được khách thử duyệt. Phép đo dùng proposal hai nhánh xác định trước để cô lập tính đồng thời. Phép thử Director thật và hai đồ thị do model đề xuất thuộc PR #7. Bài fake provider ban đầu dùng đồng hồ độ phân giải thấp nên báo overlap 0 trên Windows. Bài cuối dùng đồng hồ hiệu năng và barrier có độ trễ xác định.

Trước khi nâng DB có dữ liệu, sao lưu và thử khôi phục riêng, dừng nhận brief và dừng tiến trình ghi/cấp offer. Chạy migration rồi khởi động lại API, dispatcher và worker từ cùng SHA. Migration 013 giữ chế độ một lease cho run cũ, cùng với ledger, quyết định QA và snapshot đã duyệt. Khi rollback tính năng, chọn một lease cho run mới, dừng cấp offer cho các run cần rút, hoàn tất hoặc thu hồi chúng rồi xử lý các attempt đã hết hạn. Đối soát hold của những lượt đã gửi và giữ schema v13 để truy lịch sử. Muốn chạy lại binary cũ, dùng bản sao lưu tương thích đã diễn tập. [ADR-011](docs/ADR-011-NODE-ATTEMPTS.md).

## PR #7 · Director lập kế hoạch động với một lease

Mốc Director một lease được hợp nhất vào main tại `38cee8f` với schema v12. Dừng dispatcher và luồng ghi, sao lưu DB nội bộ, chạy migration 012, rồi khởi động API và worker từ cùng commit theo [runbook Docker](docs/POOL-RUNBOOK.md). PostgreSQL v12 giữ nguyên kế hoạch diamond và lịch sử của run cũ. Để quay lại, chọn linear/diamond cho brief mới, xử lý hết hoặc thu hồi các run động đang mở rồi đối soát hold. Giữ schema v12 để đọc lịch sử.

Trên agency có pool và route, chọn **Director lập kế hoạch (dynamic-v1)** khi giao brief. Với API, gửi `{"workflow":"dynamic-v1","extra_skills":["seo"],"budget_microusd":0}` để yêu cầu Content và SEO hoặc bỏ SEO nếu brief chỉ cần Content. Mở **Xem kết quả và chi phí** để xem phase, digest và dependency theo node. Planner chỉ có một task khi enqueue. Sau khi báo kết quả, server kiểm tra trước khi tạo task chuyên môn. Mỗi node có ID riêng trong run. Lý do bị từ chối và usage đã biết nằm trong journal. Khi kiểm tra nguồn cho bản giao, dùng revision và digest của QA; digest đồ thị dùng để truy lại kế hoạch.

Chạy Ruff và pytest theo mục kiểm thử bên dưới. Thêm `--from-v11` khi diễn tập nâng trên DB mẫu thứ mười một. Job Docker `workforce-model` chạy thêm `python tests/pool_model_smoke.py --docker --workflow dynamic-v1` và lưu artifact `dynamic-measurements.json`. Hai lượt thử native đầu đều từ chối 3/3 proposal ở mỗi campaign B/C. Lượt thứ nhất có 1.578 token vào và 698 ra được đo, lượt thứ hai có 2.076 vào và 747 ra. Sau khi giữ thứ tự trường schema qua mailbox JSONB, B sinh một node Content, C sinh hai node độc lập Content và SEO. Năm lượt có usage ở B/C đạt ngay lần đầu với 1.450 token vào và 352 ra. A bị thu hồi ở mỗi lượt và usage chưa xác nhận. Các thử nghiệm dùng Qwen local, chi phí 0 micro-USD. Trong brief C, phân công của model lặp lại câu mẫu cho email dù brief yêu cầu landing page. Bản kế tiếp bỏ câu phân công mẫu và kiểm tra từ khóa trên brief tổng hợp ở Qwen smoke. B dùng Content để viết email (595 token vào, 154 ra). C dùng Content để viết landing page rồi SEO nhận đúng checkpoint của trang (952 vào, 298 ra). Cả năm lượt hoàn tất ngay lần đầu và hai khách mẫu duyệt bản giao. A tiếp tục dừng khi thu hồi với usage chưa rõ.

Tại mốc v12, PostgreSQL bảo đảm tối đa một lease/run. Mốc v13 phía trên bổ sung phép thử hai lease, ngân sách, fencing, retry và Join theo [thiết kế PR #7](docs/PR7-DYNAMIC-DAG.md). [ADR-010](docs/ADR-010-DYNAMIC-PLANNER.md) · [Kiểm thử freeze và replay](tests/test_dynamic_execution.py).

## Mốc nội bộ sau PR #6 · Schema v11

Ngày 24/11/2026, [PR #6](https://github.com/datnv41001/ai-company/pull/6) đã vào `main` tại [`4bfa8cf15ee0f654f779442debb75007d74f8ec2`](https://github.com/datnv41001/ai-company/commit/4bfa8cf15ee0f654f779442debb75007d74f8ec2). Git tree của commit merge trùng với head đã kiểm toán `08178ef7afb36bc244d32fac9c536696fdf20622`.

CI trên chính commit merge đạt 3/3 job. Ruff và 102/102 bài kiểm thử đạt. Cả 10 đường nâng PostgreSQL từ v1–v10 lên v11 đều đạt khi chạy lặp lại trên dữ liệu mẫu có kiểm tra cô lập khách hàng. Chromium đạt ở 1280 × 850 và 390 × 844. Với Qwen local và workflow diamond, A dừng khi thu hồi quyền, còn một lượt chưa xác nhận usage. B và C mỗi campaign hoàn thành 5/5 node ngay lần đầu. Mười lượt có usage ghi nhận tổng 2.814 token vào và 1.047 token ra. Phạm vi nghiệm thu là phát triển nội bộ trên dữ liệu tổng hợp. [CI của commit merge](https://github.com/datnv41001/ai-company/actions/runs/45301277947).

Migration 011 nâng PostgreSQL lên v11. Với agency đã bật pool và cấp route, chọn **Mẫu workflow → Content và SEO sau Strategy (diamond-v1)** khi giao một brief mới. API nhận `{"workflow":"diamond-v1","budget_microusd":0}` tại endpoint tạo run hiện có. Mặc định `linear` tiếp tục xử lý các brief khác. Template DAG yêu cầu PostgreSQL và gồm đúng năm bước gọi model. Director viết phân công. Join là bước tổng hợp trong giao dịch, không gọi model.

Mở **Xem kết quả và chi phí** để thấy revision, node sẵn sàng, dependency còn thiếu, số lượt và khoản giữ/chi. Hai nhánh dùng chung Strategy và nhận riêng phân công của mình. Trong mỗi run có tối đa một lease đang mở. Preview được tổng hợp theo thứ tự của template; cùng nội dung node sẽ có cùng digest khi đảo thứ tự hoàn tất. Kết quả văn bản do Qwen sinh vẫn có thể thay đổi giữa các lần chạy.

Trước khi nâng volume nội bộ có dữ liệu, sao lưu, tạm dừng enqueue, API ghi và mọi dispatcher; chạy migrate rồi khởi động đồng bộ các service từ cùng SHA. Các run v10 đang có lease, checkpoint, receipt hoặc snapshot tiếp tục theo workflow ban đầu. Khi tắt tính năng, chọn tuyến tính cho brief mới, hoàn tất hoặc thu hồi run DAG và đối soát mọi hold đang mở. Giữ v11 để truy xuất lịch sử. [ADR-009](docs/ADR-009-DIRECTOR-DAG.md) · [Kiểm thử hai thứ tự hoàn thành](tests/test_diamond.py) · [Thiết lập Docker và worker LOGIN](docs/POOL-RUNBOOK.md).

## Mốc nội bộ sau PR #5 · Schema v10

Ngày 23/11/2026, [PR #5](https://github.com/datnv41001/ai-company/pull/5) đã vào `main` tại [`6657ef81364c941fe1fe13d1f92efcdd7ce334d0`](https://github.com/datnv41001/ai-company/commit/6657ef81364c941fe1fe13d1f92efcdd7ce334d0). Git tree của bản merge trùng với head đã kiểm toán `9a82526d902b525636734397676a796c3736d3b9`. CI trên chính commit merge đạt 3/3 job ngay lần đầu. Ruff và 93/93 bài SQLite/PostgreSQL đạt; cả chín đường nâng v1–v9 lên v10 đều chạy lại thành công. Chromium đạt tại 1280 × 850 và 390 × 844. Trong kịch bản Qwen local, A dừng do thu hồi quyền, B và C đạt 4/4 bước ngay lần đầu, qua QA và khách thử duyệt. [CI trên commit merge](https://github.com/datnv41001/ai-company/actions/runs/45150904549).

Trong kịch bản PostgreSQL có hạn mức run 1.000 micro-USD, tổng chi ròng cộng khoản giữ lần lượt là 700 sau timeout, 350 sau đối soát, 750 sau khi giữ thêm 400 và 350 khi offer mới hết hạn trước lúc worker nhận. Gửi receipt cho offer đó trả HTTP 409, kể cả số tiền bằng 0. Chứng từ v9 từng ghi cho offer chưa nhận vẫn còn trong lịch sử để kiểm kê. [Kiểm thử tài chính và thu hồi quyền](tests/test_pool_dispatch.py) · [Truy vấn đối chiếu sổ cái](docs/POOL-RUNBOOK.md).

Phạm vi nghiệm thu là phát triển nội bộ với dữ liệu tổng hợp và Qwen local. Đối soát nhà cung cấp trả phí, kiểm thử phục hồi dữ liệu thực tế, tải lớn và chất lượng nội dung trên brief khách thật vẫn là các việc cần nghiệm thu riêng.

Schema ở commit merge PR #5 là v10. Migration 010 tính lại số đã chi và đang giữ của từng pool run từ ledger v9. Chứng từ mới cập nhật ledger và run trong cùng giao dịch, bao gồm hoàn tiền và phí đến muộn. API trả 409 nếu offer đã đóng với sự kiện `unsent`. Xem phần đối soát trong runbook để kiểm tra số dư hoặc rà soát chứng từ cũ.

Schema v9 bổ sung danh tính PostgreSQL riêng cho worker, dispatcher, hàng đợi theo campaign và ledger ngân sách theo kỳ UTC. Quyết định kỹ thuật nằm trong [ADR-008](docs/ADR-008-COMPANY-OPERATIONS.md). Để dựng lại trên máy khác, cấp route, kiểm tra chi phí hoặc khôi phục, dùng [hướng dẫn pool Docker](docs/POOL-RUNBOOK.md). Chạy migration trước khi khởi động API từ main. Lịch sử v8 và snapshot giữ nguyên qua nâng cấp.

## 1. Lấy đúng mã trên máy mới

[PR #4](https://github.com/datnv41001/ai-company/pull/4) đã vào `main` tại `45e5c701132a5e7a6baa6fd6bf8cbacee3d5330f`, gồm bản đã review `4653dd77be67f3df6c95cd96f57ef668eaa09828`. Mốc này dùng schema 8. Trên máy mới, lấy `main` và dùng `git rev-parse HEAD` để ghi SHA khi bàn giao. CI trên chính commit merge đạt 3/3 job, 76/76 bài SQLite/PostgreSQL và 7/7 đường nâng cấp lên v8. [Log trên main](https://github.com/datnv41001/ai-company/actions/runs/45141376697).

~~~sh
git clone https://github.com/datnv41001/ai-company.git
cd ai-company
git fetch origin --prune
git switch main
git pull --ff-only
git rev-parse HEAD
git status --short --branch
~~~

Nếu tiếp tục viết code từ một SHA cụ thể, dùng `git switch -c ten-nhanh-moi SHA_DA_XAC_NHAN`. Với nhánh đang sửa dở, commit và push phần cần bàn giao trước khi sang máy khác. Một bản ZIP chỉ thể hiện thời điểm xuất. Git đồng bộ mã, migration và các quyết định nghiệp vụ; database, tài khoản, file cấu hình riêng và Docker volume nằm tại từng máy.

## 2. Chạy bằng Docker từ một checkout sạch

Cần Git, Docker Engine đang hoạt động và Compose v2. Từ thư mục gốc, chạy trong PowerShell hoặc Bash:

~~~sh
docker info
docker run --rm -v "${PWD}:/src" -w /src python:3.12-slim python scripts/init_env.py
docker compose -p amc-dev config -q
docker compose -p amc-dev up -d --build
docker compose -p amc-dev ps -a
~~~

Lệnh đầu tiên tạo file cấu hình là lệnh chạy `scripts/init_env.py`; nếu máy đã có Python có thể chạy `python scripts/init_env.py` trực tiếp. Script giữ file .env đã tồn tại. Với cấu hình cũ, kiểm tra ba biến `POSTGRES_PASSWORD`, `AMC_RUNTIME_PASSWORD`, `JWT_SECRET` đã có giá trị riêng, ngẫu nhiên. Giữ đúng mật khẩu cũ nếu tiếp tục dùng volume cũ.

Mở [giao diện](http://127.0.0.1:8000), [health](http://127.0.0.1:8000/api/health) và [hợp đồng API](http://127.0.0.1:8000/docs). Trạng thái mong đợi: service db healthy, migrate thoát với mã 0, api healthy. Đăng ký một tổ chức Agency bằng dữ liệu thử. Nếu cổng 8000 đã được dùng, đặt `AMC_HTTP_PORT=8001` trong .env trước khi chạy Compose và dùng cổng đó trên trình duyệt.

- Chẩn đoán bằng `docker compose -p amc-dev logs --tail=80 migrate api`. Docker Desktop trên Windows cần chạy và tài khoản phải có quyền truy cập Docker Engine. Đường chạy PostgreSQL native trên Windows nằm trong [README](README.md).
- Dừng bằng `docker compose -p amc-dev stop`. Khởi động lại cùng dữ liệu bằng `docker compose -p amc-dev up -d`. Giữ nguyên project name và volume. Khi đổi commit, dùng lại `up -d --build` để chạy migration tương ứng. Không dùng tùy chọn xóa volume cho DB cần giữ.
- Khi chuyển cả dữ liệu, sao lưu bằng công cụ PostgreSQL, truyền bản sao và bí mật qua kênh riêng được phép, phục hồi trên DB riêng và kiểm tra quyền bằng tài khoản runtime. Không push dữ liệu hay khóa vào Git. Cùng commit giúp đồng bộ logic; phiên bản dependency nằm trong khoảng cho phép có thể đổi khi build lại. CI ghi lại các phiên bản và image thực dùng.

## Chạy AI Workforce trên máy mới

Cần Git, Docker Compose v2 và khoảng 0,5 GB cho trọng số ngoài dung lượng Docker images. Sau khi tạo .env theo phần trên, cài model mẫu có checksum bằng một trong hai lệnh dưới đây từ thư mục repo.

~~~sh
# Python có sẵn (đã cài requirements.txt)
python scripts/fetch_workforce_model.py
# Hoặc dùng Docker, không cần Python trên host
docker run --rm -v "${PWD}:/src" -w /src python:3.12-slim sh -c "pip -q install httpx && python scripts/fetch_workforce_model.py"
~~~

Khởi động web, DB và model nội bộ. Model đọc models/workforce.gguf và chỉ lắng nghe trong mạng Compose.

~~~sh
docker compose -p amc-dev --profile local-model up -d --build db migrate api model
~~~

1. Trong agency tạo client, Brand Kit có dữ kiện sản phẩm, campaign và người nhận có grant đúng phạm vi. Dùng một tài khoản đăng ký riêng làm editor cho worker. Owner/admin mở **Điều phối Marketing AI**, chọn campaign và người giao brief. Khách đăng nhập, mở **Brief Marketing của bạn** và gửi mục tiêu, đối tượng, đề nghị cùng nguồn.
2. Thêm năm UUID vào .env: `AMC_WORKER_TENANT`, `AMC_WORKER_CLIENT`, `AMC_WORKER_BRAND`, `AMC_WORKER_CAMPAIGN`, `AMC_WORKER_OPERATOR`. Lấy qua API docs: /api/me của editor trả user ID và workspace; GET clients, brands, campaigns bằng tài khoản nội bộ trả các ID còn lại. Dùng đúng một campaign trên mỗi worker. Tài khoản editor này không được duyệt QA nội bộ.
3. Đặt `AMC_WORKFORCE_PROVIDER=local`, `AMC_WORKFORCE_MODEL=amc-local`. Với model trong Compose, dùng `AMC_LOCAL_MODEL_URL=http://model:8080/v1`. Với worker và llama.cpp cùng chạy native, dùng http://127.0.0.1:18084/v1. Có thể chạy worker native bằng `python -m app.workforce_worker` sau khi khai báo DATABASE_URL, JWT_SECRET và các biến trên. Dùng `--once` để xử lý tối đa một bước.
4. Khởi động worker khi model đã sẵn sàng. Trong giao diện, agency mở brief đã nhận, chọn thêm chuyên môn nếu cần, giữ ngân sách 0 cho local rồi chọn **Giao việc cho AI Director**. Nút **Cập nhật tiến độ** hiện trạng thái, nguồn, lượt gọi và chi phí. Các bản đã tạo chờ QA ở mục bàn giao. Sau khi QA và khách duyệt, mở chi tiết run để xem đúng bộ tài sản đã duyệt.

~~~sh
docker compose -p amc-dev --profile workforce up -d --build worker
docker compose -p amc-dev logs --tail=50 worker model
~~~

OpenAI là lựa chọn chủ động. Cấu hình `AMC_WORKFORCE_PROVIDER=openai`, model hỗ trợ structured output và giá `AMC_INPUT_RATE_MICROUSD`, `AMC_OUTPUT_RATE_MICROUSD` theo **micro-USD trên một triệu token**. Ví dụ 0,50 USD/triệu token tương ứng 500000. Tạo run có ngân sách dương phù hợp. Chỉ dùng nguồn đã được phép gửi tới nhà cung cấp. Các lần kiểm thử tự động dùng model local hoặc gateway thử.

Schema 6 khóa endpoint chiến lược cũ (HTTP 410). Khi dùng OpenAI, đặt key trong file `openai_key` tại thư mục riêng của worker. Compose mount thư mục `AMC_WORKER_SECRET_DIR` (mặc định .worker-secrets/) chỉ đọc vào worker. Với worker native, đặt `AMC_WORKER_KEY_FILE` trỏ đến file ngoài repo. Bỏ OPENAI_API_KEY khỏi cấu hình API cũ, khởi động lại dịch vụ. Tệp bí mật, DB và dữ liệu mẫu thuộc từng máy. Kiểm tra **Nguồn/cần bằng chứng** trong tiến độ và màn hình QA trước khi chia sẻ.

Thu hồi quyền xem hoặc đổi sang brand/campaign khác hủy run queued/running ngay khi giao dịch commit. Quyền được cấp lại cần brief và run mới. Năm đường nâng DB v1–v5 lên v6, hành vi với lượt gọi còn trên mạng, hạn chế chi phí và kiểm thử claims nằm ở [ADR-006](docs/ADR-006-WORKFORCE-CONTROLS.md).

[ADR-005](docs/ADR-005-AI-WORKFORCE.md) ghi ranh giới quyền, lease, retry, prompt, cách đọc chi phí, hạn chế chất lượng, bằng chứng demo và rollback schema 5. [CI](.github/workflows/ci.yml) ghi lệnh chạy suite, mười đường nâng cấp và nghiệm thu model thật bằng Compose trên database thử riêng.

## 3. Hợp đồng nghiệp vụ cổng duyệt · schema 8

Bản làm việc trả về `qa_evidence` ở cấp đầu. Sau khi lưu, đọc lại số lần lưu, digest, ruleset và các câu cần đối chiếu. Để duyệt hoặc trả lại, gửi `{"decision":"approved","expected_qa_revision":3,"expected_content_digest":"<64 ký tự hex từ bản đang xem>"}` tới POST `deliverables/{id}/review`. Số 3 trong ví dụ phải thay bằng `qa_evidence.qa_revision` của bản người QA đã xem. Mỗi lần lưu, kể cả lưu lại nguyên văn, sẽ tăng số này. Nếu server trả 412, tải lại bản và đọc lại trước khi quyết định. Bản trước v8 thiếu số lần lưu trong báo cáo cần POST `deliverables/{id}/assessment`. Bản đã giao vẫn dùng digest cũ. Hướng dẫn đối chiếu nguồn, lịch sử kỹ thuật và khôi phục ở [ADR-007](docs/ADR-007-QA-EVIDENCE-REVISION.md).


| Quy tắc | Nơi sửa khi thay đổi | Bằng chứng phải chạy |
|---|---|---|
| Người nội bộ có thể xem bản làm việc. Khách chỉ thấy hồ sơ client của mình và phiên bản đã được chia sẻ. | [Bộ lọc API](app/access.py), [policy PostgreSQL](migrations/003_delivery_policies.sql) | [Test cách ly](tests/test_client_isolation.py), [draft riêng tư](tests/test_delivery.py) |
| Lưu bản sửa hủy QA cũ và yêu cầu đang chờ trong cùng giao dịch. Người tạo và người sửa cuối không tự QA. Admin/owner chỉ chia sẻ bản đã qua QA, có preview và hạn trong tương lai. | [API nội bộ](app/main.py), [luồng bàn giao](app/delivery.py) | [Test vòng đời](tests/test_review_lifecycle.py) |
| Một request là một snapshot. SHA-256 bao gồm đúng tiêu đề và preview UTF-8. Mỗi quyết định lưu ID snapshot, digest, người, giờ, ý kiến. Bản đang chờ đóng ngay khi agency lưu bản sửa. Từ chối/yêu cầu sửa cần lý do ít nhất 5 ký tự. | [Model](app/delivery_models.py), [DDL](migrations/003_delivery_tables.sql), [ADR-003](docs/ADR-003-CLIENT-DELIVERY.md) | Test hai quyết định đồng thời, retry, sửa v1→v2, hết hạn, thu hồi |
| Quyền xem, bình luận và quyết định tách biệt. Grant có thể giới hạn đến brand/campaign trong một client. Hội đồng duyệt là những người còn quyền trong đúng nhóm đó. | PUT `/api/tenants/{tenant}/members/{user}/review-rights` | Test viewer, reviewer, rescope và token cũ |
| Duyệt nội dung chỉ ghi nhận quyết định. Thực thi hành động ra ngoài vẫn bị khóa. | [Đường execute](app/main.py) | [Test hồi quy](tests/test_api.py) |
| Giao diện hiển thị phiên bản, hạn theo giờ máy người xem, nội dung, lịch sử và hành động theo quyền. | [Cổng duyệt](app/static/reviews.js) | [Test trình duyệt desktop/mobile, cả email dài và hiển thị trên màn hình hẹp](tests/browser_delivery.py) |

**Thử một vòng bằng dữ liệu giả.** Dùng ba tài khoản khác nhau cho editor, QA/admin và khách. Các tài khoản cần đăng ký trước. Admin thêm thành viên nội bộ hoặc `client_viewer` qua POST `/api/tenants/{tenant}/members`. Với khách, gán đúng client_id và dùng PUT `review-rights` nếu người đó cần bình luận hoặc duyệt. Ví dụ body `{"can_comment":true,"can_decide":true,"brand_id":null,"campaign_id":null}` áp dụng cho hồ sơ client đã gán. Gửi lại body với cờ false thu hồi khả năng tương ứng. Tạo client → brand → campaign. Trong giao diện, editor mở **Soạn và bàn giao cho khách**, tạo bản nháp rồi gửi QA. QA đăng nhập đúng workspace, duyệt và chia sẻ kèm hạn. Khách đăng nhập ở trình duyệt riêng, chọn workspace của agency, mở phiên bản và phản hồi. Agency xem lại kết quả trong cùng danh sách bàn giao. Trong giao diện, admin mở **Quản lý người nhận và lời mời**, chọn client, brand, email và quyền, rồi tạo lời mời. Khách đăng nhập tài khoản đã đăng ký và chọn **Chấp nhận lời mời**. Agency quản lý quyền hoặc rút quyền xem ở cùng màn hình. Lời mời có hạn 7 ngày, nằm trong ứng dụng.

Danh sách bản giao tải 25 dòng mỗi lần. Nút **Xem thêm bản bàn giao** lấy trang tiếp theo. API hỗ trợ limit 1–100 và trả header X-Next-Cursor. Xem [ADR-004](docs/ADR-004-REVIEW-OPERATIONS.md) cho cursor, chính sách hủy, quyền lời mời, thiết kế nhiều client/brand và phục hồi schema 4. Test dữ liệu lớn duyệt đủ 1.001 snapshot.

Suite bao gồm [luồng và phân trang](tests/test_review_lifecycle.py), [lời mời và quyền](tests/test_recipients.py), và [thao tác giao diện](tests/browser_delivery.py). Báo cáo phản biện, các quyết định sản phẩm và điểm còn mở nằm trong [ADR-004](docs/ADR-004-REVIEW-OPERATIONS.md).

## 4. Kiểm thử và dữ liệu nâng cấp

[Workflow CI](.github/workflows/ci.yml) là lệnh tham chiếu chi tiết cho một máy Linux sạch. Job `api-tests` chạy Ruff, SQLite, HTTP với PostgreSQL thật, nâng cấp từ từng phiên bản v1–v12 có dữ liệu lên v13 và chạy lại migration. Job `compose-browser` build đúng repo bằng Compose và thao tác qua Chromium với hai kích thước. Kiểm tra job trên **đúng commit** của PR.

Khi chạy pytest nhanh với SQLite, đặt DATABASE_URL tới SQLite thử riêng, cài `requirements-dev.txt`, chạy `python -m pytest -q`. Các bài PostgreSQL bị skip trong chế độ này. Khi chạy suite đầy đủ, dùng DB trống cục bộ tên bắt đầu bằng `amc_test`, runtime role `amc_runtime`, có `AMC_TEST_PG=1` và chạy migration trước pytest. Tách mười hai DB thử trống cho `tests/check_postgres_upgrade.py`. Chạy mặc định cho v1, lần lượt thêm `--from-v2`, `--from-v3`, `--from-v4`, `--from-v5`, `--from-v6`, `--from-v7`, `--from-v8`, `--from-v9`, `--from-v10`, `--from-v11`, `--from-v12` vào mười một lượt còn lại. Với test trình duyệt, cài `requirements-browser.txt`, chạy `python -m playwright install chromium` rồi trỏ `AMC_BROWSER_TEST_URL` đến một instance loopback chỉ có dữ liệu thử. Test tạo tài khoản mẫu. Không chạy các kịch bản này trong DB đang phục vụ người dùng.

Schema v4 giữ các quyết định v3, kể cả lý do từng để trống. Schema v3 giữ bản nháp và quyền cũ trong DB; khách ngoài được backfill grant chỉ xem và có danh sách review rỗng tới lần chia sẻ đầu tiên. Không tự chuyển viewer nội bộ thành khách. [Trình chạy migration](migrations/apply.py) ghi version trong cùng giao dịch. Xem quy trình phục hồi trong [ADR-003](docs/ADR-003-CLIENT-DELIVERY.md).

## 5. Bàn giao sau mỗi thay đổi

Người hoặc AI sửa mã cập nhật **cùng PR** phần hợp đồng tương ứng trong file này. Chú thích cạnh mã cho lý do khó suy ra, chẳng hạn thứ tự khóa, ranh giới dữ liệu giữa agency/khách hoặc quy đổi thời gian. Nếu đổi schema, quyền, state machine hoặc tích hợp, ghi tradeoff và rollback trong ADR; giữ lại migration đã phát hành và thêm migration mới. Đặc tả, kế hoạch và kết quả đã được kiểm thử cần được ghi rõ trạng thái riêng.

Ghi vào PR: hành vi cũ → mới, đường vào API/UI, files chính, phiên bản schema, lệnh kiểm thử, kết quả đạt/skip, link CI, dữ liệu cần chuyển và điểm còn mở. Người nhận chạy lại thay đổi từ SHA của PR và lấy dữ liệu mẫu qua fixture. Chưa merge thì nêu tên nhánh. Khi hoàn tất một work package, cập nhật mục tiếp theo và mốc xác minh. Mẫu có ở [pull request template](.github/pull_request_template.md).

### PR #9 và bàn giao registry v14

PR #9 đã merge tại `f283c6e9eef7054ec11d1aac20ed6971fa891499`. [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45314082884) đạt cả ba job trên schema v13. [Thiết kế được duyệt](docs/PR9-AGENT-CONTRACTS-WORKFLOW-REGISTRY.md) và [ma trận 110 yêu cầu](docs/PR9-TRACEABILITY.md) là mốc đối chiếu. Nhánh triển khai PR #10 là `feature/registry-v14`. Commit RED `7aab97a` có sáu test thất bại trên PostgreSQL v13 trước migration.

1. Trên máy phát triển mới, dùng quy trình Docker ở đầu file. Chạy `docker compose up -d --build` để service migrate nhập [manifest đã review](catalog/landing-seo-v1.json) và ghi schema 14. Pipeline dùng tài khoản migration để chạy `python migrations/apply.py --publish-registry catalog/landing-seo-v1.json` khi nhập lại cùng bản hoặc phát hành manifest mới đã review. API agency chỉ kích hoạt bản đã phát hành. Mỗi adapter có digest kiểm tra khi nhập và trước offer. Cần review phiên bản mới khi đổi hợp đồng, prompt hoặc QA.
2. Cấp worker và ngân sách agency theo phần pool ở trên. Trong **Điều phối Marketing AI**, chọn campaign rồi mở **Quyền workflow của chiến dịch**. Cấp quyền cho workflow, gửi brief có nguồn với Brand Kit, chọn `WF-13/landing-seo-draft@1` và giao Director. **Xem kết quả và chi phí** hiển thị workflow, hai digest sau freeze, node, phiên bản vai trò và chi phí. API `GET/PUT /api/tenants/{tenant}/workforce/registry/{campaign}` cho phép chỉ định danh sách skill. Ba skill bắt buộc là director/content/seo. Research và Strategy có thể được cấp thêm.
3. **Ngừng cấp cho run mới** vẫn cho run đã ghim hoàn tất. **Thu hồi và dừng run đang chạy** dùng cùng khóa giao dịch PostgreSQL với freeze, offer, checkpoint và Join. Hold đã gửi chờ usage hoặc receipt. Dùng API receipt hiện có để ghi chi phí tuyệt đối, gồm refund và overage. Đọc từng attempt cùng kỳ, hold và chi phí qua báo cáo run. Các run cũ hiển thị `legacy_v13`.
4. Để kiểm tra trên database thử, dùng lệnh CI trong [workflow](.github/workflows/ci.yml). `python -m pytest -q tests/test_registry.py` với `AMC_TEST_PG=1` chạy test phân quyền, cạnh tranh, phiên bản, đối soát và QA. Chạy `python tests/check_postgres_upgrade.py --from-v13` trên một database thử trống riêng, rồi `python tests/registry_model_smoke.py` với endpoint Qwen local như CI. Artifact `registry-measurements.json` chứa graph, digest và usage. Dữ liệu nghiệm thu là fixture tổng hợp.
5. Khi cần rollback, ngừng intake mới, drain hoặc thu hồi run ghim v14, đối soát các hold đã gửi. Dùng đường vào v13 cho brief tiếp theo trên schema tương thích. Khôi phục phiên bản cũ bằng bản sao lưu đi kèm nếu cần quay lại schema cũ. WF-11, WF-13 và các vai trò vẫn chờ nghiệm thu nghiệp vụ đầy đủ.

### Chuyển phiên bản adapter trên PR #10

Bản nguồn trước chuyển giao là `bae0ddeb1df5a922c82f6d5c9a2b09e46eeee728`, schema 14. Commit test RED là `dde54703c634aee3f5fe046bbd2faec338c4d075`. Trong PostgreSQL thử, dispatcher dùng mã prompt khác từng chuyển run v1 đã hoàn tất Content sang `failed`. Một bản phát hành có trường SEO ngoài schema cũng từng được nhập thành công.

1. Triển khai dispatcher hỗ trợ đồng thời các adapter trong [bảng phiên bản thực thi](app/registry_adapters.py). Dừng và thay mọi dispatcher có mã cũ `bae0ddeb` trước khi kích hoạt v2 cho run mới. Worker inference chỉ nhận envelope đã tạo sẵn. Cả bước cấp việc lẫn bước ghi checkpoint/QA cần dispatcher đọc đúng adapter đã ghim.
2. Giữ bộ thực thi `seo@1` (digest `c64cf3e0e691a1bad191b954b07d06a28c7cd8675bb5fe8328ee0ae0e620880a`) cho run cũ. `seo@2` có prompt yêu cầu diễn đạt search intent thành truy vấn tìm kiếm, digest `3ab7030bf2a22ede6c3995821892ed91d0ac60a411a8ea89547ffb01347597e5`. Khi dispatcher thiếu phiên bản tương thích, nó nhường node hoặc báo cáo còn hiệu lực cho dispatcher khác. Giám sát run chờ, thời hạn lease và hold qua API báo cáo. Nếu cả pool thiếu adapter, khôi phục image tương thích để tiếp tục. Trước khi gỡ image cuối hỗ trợ một version, ngừng cấp mới và đợi các run đang dùng kết thúc cùng các attempt đã gửi được đối soát.
3. Publisher đối chiếu danh sách `outputs` với các trường thật trong envelope. Manifest cũ dùng kiểu từ schema của adapter. Nếu cung cấp `output_schema`, dùng JSON Schema cấu trúc do `output_schema(adapter)` trả về, gồm kiểu trường, kiểu phần tử mảng, thuộc tính bắt buộc và object đóng. Các enum của nguồn/campaign được dựng theo từng brief. Publisher đối chiếu role, skill, adapter, phiên bản và predecessor, rồi chạy compiler cho đường Content → SEO → Join trước khi ghi định nghĩa trong cùng giao dịch.
4. Chạy `python -m pytest -q tests/test_adapter_rollout.py` với môi trường PostgreSQL thử như CI. Job Qwen dùng hai checkout. Đặt `AMC_V1_SOURCE` trỏ đến checkout cũ ở SHA nêu trên và `AMC_SOURCE_SHA` là SHA mới, rồi chạy `python tests/registry_model_smoke.py` trong môi trường model của CI. Artifact `registry-rollout.json` ghi hai source SHA, hai adapter digest, binding trước chuyển giao, các attempt sau Join và snapshot đã duyệt của từng run. Workflow v2 trong phép thử chỉ được phát hành vào database tổng hợp của job.

### Nhận diện runtime của registry v14 trên máy khác

Commit RED `535a94eb7b05591cd5a52402ae2579a5a42317dc` ghi lại lỗi trên PostgreSQL. Run v1 đã xong Content. Một checkout chỉ đổi `MAX_OUTPUT` từ 640 thành 800 vẫn cấp offer SEO 800 token dưới digest v1 `c64cf3e0…`. Ba checkout khác đổi ràng buộc `Key`, hàm dự phòng token hoặc quy tắc QA cũng được nhận dưới digest cũ. Có thể tái hiện bằng `python -m pytest -q tests/test_adapter_fingerprint.py` tại commit RED, với database thử và các biến môi trường của job `api-tests`.

Schema vẫn là v14. [Hồ sơ phát hành](migrations/registry-runtime.lock.json) ghép mỗi fingerprint SHA-256 của runtime với các digest adapter mà build đó được phép thực thi. Manifest, plan digest và các bản giao lịch sử giữ nguyên. [Mã nhận diện](migrations/runtime_bundle.py) băm tên và toàn bộ nội dung tệp trong `app`, `migrations`, `catalog`, cùng hai tệp yêu cầu runtime. Bỏ qua giao diện tĩnh, cache Python và chính hồ sơ phát hành. Nội dung văn bản dùng LF để checkout Windows và Docker đồng nhất. Fingerprint bao gồm cả phiên bản CPython và phiên bản thư viện thực tế theo [danh sách constraints](requirements-registry.txt). Cùng mã này bảo vệ cả lúc cấp offer lẫn khi nhận kết quả để ghi checkpoint và QA.

1. Trên máy mới, checkout đúng SHA của PR và dùng `docker compose build`. Kiểm tra trước khi mở pool bằng `docker compose run --rm --no-deps api python -c "from migrations.runtime_bundle import runtime_fingerprint, approved_adapter_digests; print(runtime_fingerprint(), sorted(approved_adapter_digests()))"`. Docker/CI dùng CPython 3.12.16. Máy Windows đã kiểm thử dùng 3.12.14 và cùng các phiên bản thư viện trong constraints. Kết quả phải có các digest của phiên bản cần chạy. Dùng image chỉ đọc từ khi khởi động đến khi dừng tiến trình. Thay image và khởi động lại để nhận build mới.
2. Khi chuyển từ bản cũ, dừng nhận brief mới, cho attempt đang chạy hoàn tất và thay các dispatcher/worker trước khi mở intake trở lại. Các binary phát hành trước bản vá chưa có bước xác minh này. Giữ sẵn image đã kiểm thử cho những run còn ghim v1. Nếu danh sách rỗng, worker dừng trước khi nhận lease. Dispatcher nhường node và báo cáo cho bản tương thích. Theo dõi run chờ, offer, hold và receipt theo [runbook pool](docs/POOL-RUNBOOK.md).
3. Khi đổi mã hoặc thư viện, đo fingerprint trong chính image ứng viên. Review diff với nguồn đã duyệt, chạy kiểm thử chuyển giao cho từng phiên bản muốn tiếp tục hỗ trợ, rồi ghi fingerprint và danh sách digest tương ứng vào hồ sơ trong PR. Chỉ gắn lại digest cũ nếu hành vi của phiên bản đã ghim được bảo toàn. Nếu chủ ý thay đổi hành vi, phát hành adapter mới và giữ build tương thích cho run cũ. Migration và khởi động ứng dụng chỉ đọc hồ sơ. Tệp này là một phần của release được review trong Git.
4. Trên PostgreSQL thử, chạy `python -m pytest -q tests/test_adapter_fingerprint.py tests/test_adapter_rollout.py`. Các ca kiểm tra hằng số, validation, tính tiền, dự phòng token, QA, bước khởi động worker và run v1 đã xong Content. Bài Qwen hai checkout tiếp tục dùng lệnh ở mục trên. Artifact `registry-rollout.json` chứa fingerprint, phiên bản thư viện và digest trước/sau khi bàn giao. Fingerprint xác định mã ứng dụng và các phiên bản đã nêu. Model và endpoint đang chạy là đầu vào vận hành riêng của phép đo Qwen.

## PR #11 · QA theo vai trò cho bản nháp landing/SEO

Nhánh `feature/content-seo-role-qa` bắt đầu tại `4c588d8cbadc6e83da7a33e7977d12815673f663`. Hai chính sách mới dùng cho cùng tiểu quy trình landing/SEO của WF-13. [Manifest @4](catalog/landing-seo-v4.json) dùng phiên bản mới vì `@1` bất biến và các phép diễn tập v14 đã dùng `@2`, `@3`. Content dùng `content@2` với `content-qa@2`. SEO dùng `seo@3` với `seo-qa@2` và prompt search intent của `seo@2`. Việc xuất bản và cấp quyền cho campaign là hai thao tác riêng.

**Trên máy phát triển mới.** Dựng PostgreSQL và pool theo [runbook](docs/POOL-RUNBOOK.md), dùng image cùng SHA cho API, dispatcher và worker. Đối chiếu fingerprint của từng replica theo mục Registry v14 ở đầu tài liệu. Hai khóa mới trong [hồ sơ runtime](migrations/registry-runtime.lock.json) cho phép bốn digest adapter; đối chiếu `runtimes()` để biết cả tên phiên bản. Các khóa cũ chỉ nhận các digest đã duyệt cho chúng. Trong database thử, nhập manifest bằng tài khoản migration:

```sh
docker compose -p amc-dev run --rm --no-deps migrate python migrations/apply.py --publish-registry catalog/landing-seo-v4.json
```

Từ **Điều phối Marketing AI → Quyền workflow của chiến dịch**, cấp `WF-13/landing-seo-draft@4`. Chọn đúng phiên bản này khi giao brief tổng hợp. Xem **Xem kết quả và chi phí → QA đầu ra AI** để mở từng finding và nguồn đã dẫn. Người QA mở **Bàn giao và duyệt nội dung** để kiểm tra tiêu đề và nội dung của lần lưu hiện hành. Khách xem và quyết định trên snapshot đã chia sẻ.

**Phạm vi của hai báo cáo.** Trong `GET /api/tenants/{tenant}/workforce/runs/{rid}`, `checkpoints[].quality.role_qa` lưu role/policy, digest của hợp đồng, manifest, plan, output và ID node. SEO lưu cả ID và digest của đúng các checkpoint Content trên cạnh đi vào node đó. Finding ghi trường, quy tắc/phiên bản, mức độ, căn cứ, nguồn đã dẫn và trạng thái `needs_review`. Báo cáo nằm trong cùng giao dịch có fencing với checkpoint. Tại API deliverable, `qa_evidence` của bản mới có scope `delivery_revision` và vẫn đánh giá văn bản tự do theo `qa_revision` và `content_digest`. Việc sửa văn bản tạo lần đánh giá mới. Lịch sử checkpoint và snapshot đã duyệt được giữ riêng.

**Cách đọc finding.** Chính sách Content dò CTA, từ ngữ bị Brand Kit yêu cầu tránh, dấu hiệu lệch đối tượng/đề nghị và nhận định cần nguồn. SEO đối chiếu từng trường với headline/body của Content tiền nhiệm, so meta với title và đánh dấu số liệu cần xác minh. Khoảng gợi ý trong manifest là 12–70 ký tự cho title và 30–170 cho meta; thay khoảng này cần một hợp đồng đã được đánh phiên bản. So khớp từ có thể bỏ sót mâu thuẫn hoặc cảnh báo thừa khi diễn đạt bằng từ đồng nghĩa. Quy tắc Brand Kit nhận dạng chỉ dẫn minh thị kiểu `Avoid: miracle` hoặc `Tránh: …`. Một câu trùng nguồn vẫn cần người QA đọc ngữ cảnh. Reviewer chịu trách nhiệm về ý nghĩa, độ đúng của claim và quyết định duyệt.

**Tái lập nghiệm thu.** Commit RED `74e4785b9b58be0c9c28a5c4749185e781e53055` có 13 ca thất bại ở đường lưu checkpoint. Bộ nhãn cuối gồm 16 fixture, 18 finding kỳ vọng, 0 thừa và 0 thiếu theo rule trên các fixture này. Dùng `python -m pytest -q tests/test_role_qa.py` và `python -m ruff check app tests migrations scripts`. Trên PostgreSQL tổng hợp với các biến môi trường của [CI](.github/workflows/ci.yml), chạy `python -m pytest -q tests/test_role_qa_rollout.py tests/test_registry.py` rồi `python -m pytest -q`. Bài PostgreSQL thực hiện cấp/thu hồi, kiểm tra nguồn giả, hai node Content và SEO chỉ đọc một node, phân quyền A/B/C và duyệt A → B → A. Chromium có fixture giao diện riêng cho việc mở finding. Bài Qwen thật lưu `role-qa-measurements.json` với SHA, fingerprint, report của từng node, usage và snapshot khách mẫu duyệt.

**Nâng cấp và rollback.** Tiếp tục dùng schema v14 và các trường JSON checkpoint hiện có. Nhập manifest là thao tác thêm định nghĩa. Khi cần rút `@4`, chọn **Ngừng cấp mới**, giao brief tiếp theo qua `@1`, giữ runtime tương thích cho run `@4` đến khi đã drain và đối soát hold/receipt. Kiểm tra snapshot và số dư theo mục kiểm kê v14 trước khi rút image cuối. Các đầu việc tiếp theo là Research → Strategy và chẩn đoán nguyên nhân chờ trước khi tăng quy mô pool.
