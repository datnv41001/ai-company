# Bắt đầu ở đây khi tiếp quản AI Marketing Company

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

**PR #9 đang chờ review thiết kế.** Nhánh `design/agent-contract-workflow-registry` xuất phát từ `main@2846c174e393acfcc47526a8da5a62fa77bc87d5`. Đọc [thiết kế hợp đồng agent và registry workflow](docs/PR9-AGENT-CONTRACTS-WORKFLOW-REGISTRY.md), sau đó đối chiếu [ma trận 49 module, 37 vai trò và 24 workflow](docs/PR9-TRACEABILITY.md). Lát cắt đề xuất là bản nháp Content + SEO cho một brief có nguồn. Người review cần chốt phạm vi WF-11, trần ngân sách của node qua các lần retry và cách xử lý thu hồi quyền. Schema đang vận hành là v13. Migration 014 và các test registry thuộc bước triển khai sau khi thiết kế được duyệt.
