# Bắt đầu ở đây khi tiếp quản AI Marketing Company

## PR #37 — nhiệm vụ Marketing, kiểm chứng nội dung và đánh giá chất lượng

Bản phát triển kết hợp core v24, business v3 và module nhiệm vụ C3 v1. Khi chuyển máy, dùng PostgreSQL thử nghiệm và chạy publisher trong Compose trước khi mở ứng dụng. Trên máy đã có cấu hình, giữ lại secret và khóa nhận diện hiện tại. Publisher chạy lại được. Ghi nhận mọi thay đổi qua bản nâng cấp mới để giữ lịch sử quyết định và snapshot đã bàn giao.

```bash
docker compose up -d --build
docker compose run --rm migrate python migrations/apply.py --publish-registry catalog/research-strategy-v3.json
docker compose run --rm migrate python migrations/apply.py --publish-registry catalog/landing-seo-v6.json
```

Người giao việc mở **Hồ sơ doanh nghiệp → Brief**, chọn mục tiêu, sản phẩm, tập người mua, hướng dẫn thương hiệu và điều kiện áp dụng. Solo và Business dùng workspace nội bộ. Agency giữ brief do người nhận được cấp quyền gửi. Sau khi worker hoàn tất, mở bản giao để soạn nội dung, xem từng câu kèm nguồn và lịch sử lần lưu. Hướng dẫn dành cho người vận hành gồm [cấp route nội bộ và quyền duyệt](docs/ADR-C3-INTERNAL-TASKS.md), [7 skill và cách quay về phiên bản trước](docs/C3-MARKETING-SKILLS.md) và [quyết định QA theo câu](docs/business-profile/C3-CONTENT-EVIDENCE.md).

CI chạy các release lịch sử @2/@5 qua Qwen thật trên đúng checkout. Trong artifact `pool-model-measurements-integration`, mở `c3-model-receipts` để đối chiếu SHA, weights, token, run, snapshot nguồn, draft và lần biên tập tổng hợp. Artifact `knowledge-center-journeys-integration` chứa hành trình giao việc và đối chiếu nguồn trên ba kích thước màn hình. Rà soát chuyên môn theo [protocol holdout và pilot](docs/evaluation/C3-HOLDOUT-AND-PILOT.md), [kết quả đã đo](docs/evaluation/C3-QUALITY-RESULTS.md) và [ngân sách kết nối local](docs/evaluation/C3-LOCAL-RESOURCES.md). PR #37 chờ phản biện. Commercial GA vẫn NO-GO.

## AIRC · Kiểm định theo năng lực v5

Tám ca mới so một reviewer với phản biện chéo cùng ngân sách. Có 20 invocation ký trên hai checkpoint local; kết quả chưa đủ để mở rộng. Chạy replay offline và xem các giới hạn trước khi tiếp quản. [Kết quả theo reviewer/model](engineering/airc500/joint-v5/REPORT.md) · [Lệnh kiểm và rollback](engineering/airc500/joint-v5/RUNBOOK.md).

## Nghiên cứu ứng dụng cho AMC và AIRC

Bắt đầu từ [sổ nguồn](docs/research/SOURCE_REGISTRY.md), mở [thẻ kiến thức](docs/research/KNOWLEDGE_CARDS.md), [đối chiếu với mã hiện hành](docs/research/APPLICABILITY_MATRIX.md) rồi chọn [cải tiến có tiêu chí nghiệm thu](docs/research/PRODUCT_OPPORTUNITIES.md). Đọc [các giả thuyết đã hoãn hoặc bác bỏ](docs/research/REJECTED_HYPOTHESES.md) trước khi lặp lại nghiên cứu. Công cụ engineering chạy độc lập ở [runbook Research Broker](engineering/airc500/APPLIED-RESEARCH.md). Receipt lần đầu có hai nguồn quan sát được và một nguồn bị publisher hạn chế. Có thể replay ngoại tuyến bằng mã băm trong runbook. Rollback bằng dùng phiên bản catalog/adapter trước cho đợt đọc mới, giữ lại biên nhận cũ để đối soát. C2/C3 tiếp tục theo thứ tự sản phẩm.

## C3 · Marketing từ tri thức đã duyệt

Hai release WF-03 @2 và WF-13 @5 dùng brief C2 đã ghim, kiểm tra lại căn cứ tại queue, QA và chia sẻ. [Thiết lập, chọn nguồn, chạy worker, kiểm thử và rollback](docs/business-profile/C3-MARKETING-RUNBOOK.md).

Với core v24 và giao diện Premium, chọn **Hồ sơ doanh nghiệp** → **Brief** để mở tác vụ C3 theo đúng khách hàng và thương hiệu. Màn hình **Đội ngũ AI** hiển thị tiến độ. CI chạy Chromium trên cả hai phần và thực hiện ba kiểm tra thu hồi phiên tại lúc xếp việc, duyệt QA và chia sẻ.

## PR #34 · Màn hình điều hành Marketing

Điều hướng workspace dùng URL của từng màn hình. Đường dẫn giữ workspace, thương hiệu theo dõi và chiến dịch. Khi mở liên kết, ứng dụng xác minh phiên và đối chiếu các ID với danh sách mà tài khoản được phép đọc. Khi lập kế hoạch, người dùng mở thẻ bộ phận để xem vai trò và nhiệm vụ được giao. Các lượt chạy Workforce, quyết định QA, tình trạng nguồn và số liệu kinh doanh được trình bày riêng.

Bộ kiểm thử Chromium chạy qua mục CI `compose-browser`. Artifact `premium-ui-<revision>` có ảnh thật ở 1440, 1280, 820, 390 và 320 CSS px, các cặp trước/sau và `ui-acceptance.json`. Ảnh trước được lấy từ Chromium tại commit `0953285c1c6a70a5c473effb5a69501500e717b5`. Hàm kiểm thử đối chiếu SHA-256 của ảnh trước khi ghép mỗi cặp. [Thiết kế và nghiệm thu](docs/AMC-DESIGN-SYSTEM.md)

Chạy bằng `python tests/browser_premium_ui.py` với `AMC_BROWSER_TEST_URL`, hộp thư phát triển, PostgreSQL thử nghiệm và Chromium đã cài như CI. `AMC_PREMIUM_EVIDENCE` chọn thư mục đầu ra. Các thao tác tài khoản, lịch sử Back/Forward, quyền bị thu hẹp và QA tiếp tục đi qua API đã nghiệm thu. Khi cần quay lại giao diện trước, hoàn nguyên commit tinh chỉnh bằng một PR mới. Thay đổi này chỉ tác động đến ứng dụng và bộ kiểm thử giao diện.


## Trung tâm điều hành và chuẩn giao diện

Mốc nền là PR #32 tại `068b85170cf47106c8d08a8c573548e3f530647c`. Từ tài khoản nhân sự, chọn workspace để mở **Trung tâm điều hành**, chọn chiến dịch và đối chiếu bước kế hoạch với nhiệm vụ, bộ phận, bản giao và lượt xử lý Workforce. Menu **Hồ sơ doanh nghiệp** mở C2. Công tắc **Giao diện** hỗ trợ hệ thống, sáng và tối. [Hợp đồng dữ liệu, component và quy tắc nghiệm thu](docs/AMC-DESIGN-SYSTEM.md)

Dùng Compose và tài khoản tổng hợp theo hướng dẫn Docker bên dưới. Chạy browser test trong job Chromium với `python tests/browser_premium_ui.py` và các biến môi trường của workflow. Kiểm tra cả ảnh, số đo và nguồn API trên cùng SHA. Để rollback riêng giao diện, dùng lại image API đã build ở SHA nền cùng publisher và DB core v22, module doanh nghiệp v3. Thay đổi giao diện này chỉ đọc các endpoint hiện hữu. [Job kiểm thử](.github/workflows/ci.yml)

## Publisher kết hợp C2 và A1

Core v24 kết hợp business module v3 với phiên thiết bị A1. Publisher kiểm tra hai định nghĩa SQL thực tế, quyền thực thi, liên tục quota và các khóa A1 trước khi commit. Hai đường nâng từ C2 v22 và A1 v23 dùng đúng mã đã duyệt và dữ liệu tổng hợp. Khi chuyển máy, làm theo [runbook publisher, kiểm thử và khôi phục](docs/COMBINED-C2-A1.md). Các mục bên dưới lưu hợp đồng lịch sử từng nhánh.

## C2.5 · Mục tiêu thật cấp công ty và liên kết thương hiệu, chiến dịch

Chạy publisher module `amc_business` v3 trên core v22. Chọn **Mục tiêu chung doanh nghiệp** để lập cùng một mục tiêu cho nhiều thương hiệu của một khách hàng. API và giao diện dùng ID phiên bản, CAS và lịch sử quyết định khi cha được thay thế hoặc thu hồi. [Các bước dùng, nâng cấp và ca chạy lại](docs/business-profile/C2-OBJECTIVES-RUNBOOK.md)

## Business Knowledge Center · review tích hợp

[Mở bản bàn giao C2](docs/business-profile/C2-REVIEW-HANDOFF.md) để chạy trên máy mới, kiểm tra luồng từ hồ sơ đến brief, tải ảnh và đối chiếu commit, CI, giới hạn migration.

## C2.4 · Nguồn và nhận định Marketing

Trong hồ sơ thương hiệu, mở **Nguồn và nhận định** để ghi nguồn, chọn locator, so sánh câu và điều kiện, kiểm quyền chuyên môn, duyệt, xử lý tranh chấp và xem ảnh hưởng. Câu công khai dùng được qua nguồn hạn chế được tính trên server tại lúc đọc. Editor chỉ nhận phần được phép xem. Publisher cài predicate riêng trong `amc_business`, không tăng version core hoặc sidecar hồ sơ. Kiểm lại API, Chromium desktop/mobile và ranh giới kiểm chứng theo [runbook C2.4](docs/business-profile/C2-CLAIM-DESK.md).

## C2 · Danh mục thương mại, audience và mục tiêu

Nhánh `feature/business-knowledge-catalog` xuất phát từ PR #27. Mở Hồ sơ doanh nghiệp, chọn đúng client và brand, mở Danh mục, điều khoản và mục tiêu. Mã SKU/thị trường, giá theo tiền tệ quen dùng, giả thuyết audience và KPI có số liệu còn thiếu đi qua revision, CAS và quyền C1. Chạy publisher để cập nhật `amc_business` v2. Scope sản phẩm hiện tại, ca chạy lại, giới hạn dữ liệu và rollback được ghi trong [runbook danh mục](docs/business-profile/C2-CATALOG-RUNBOOK.md).

## C2 · Hồ sơ chung và brief nội bộ

Increment đầu tiên của C2.1/C2.5 trên C1 `c847f910` cho phép lưu một phần bốn field theo doanh nghiệp, kế thừa/ghi đè/để trống theo thương hiệu và tạo brief cá nhân khi chưa đủ thông tin. Publisher cài `amc_business` v1 bên cạnh core v22. Core 023 dành cho Identity A1. Chạy Compose rồi đối chiếu hai brand, thử lại lệnh sau mất phản hồi và đọc brief sau khi hồ sơ gốc đổi. PostgreSQL native 16.16 và SQLite đã qua năm ca API đầu tiên. Bộ điều phối Marketing và nghiệm thu thương mại giữ gate riêng. [Hợp đồng, quyền, chạy kiểm thử và rollback trên máy mới](docs/business-profile/C2-WORKSPACE-RUNBOOK.md)
## A1 · Phiên thiết bị, phụ thuộc Business Profile C1

Draft A1 dành migration 023 sau C1 v22. Người dùng có thể xem thiết bị, xác thực lại, refresh và thu hồi phiên. Khi tiếp quản, kiểm tra hai thứ tự commit trên PostgreSQL, diễn tập restore, chuyển riêng ba loại khóa và xác nhận vẫn ký được append C1. Thử nghiệm Keycloak chạy trong lab độc lập. [API, lệnh chạy, rollback và giới hạn](docs/DEVICE-SESSIONS-A1.md)

A1-P1-01 sửa luồng refresh của hai tab. Browser gửi SID đang hiển thị, PostgreSQL đối chiếu trước rotation. Cookie grant theo SID giữ response đến muộn của A tách khỏi phiên B. Khi nâng từ draft cũ hãy đăng nhập lại. Kiểm bằng `tests/test_device_sessions.py` và `tests/browser_device_context.py` trên dữ liệu tổng hợp. [Hợp đồng native, cách chạy và backlog Identity](docs/DEVICE-SESSIONS-A1.md)

## AIRC · Research Broker công khai và holdout năng lực v4

Trên nền main sau PR #23 `5dc4ebc73c9423f360d63287d52350e2ef21a31a`, tooling engineering thu thập các trích đoạn Marketing công khai đã duyệt, ghi cả các nguồn bị chặn, và so sánh cùng holdout có/không có packet. Chạy `python engineering/airc500/research_release.py` trong venv engineering trên máy mới. [Runbook, phạm vi quyền và rollback](engineering/airc500/PUBLIC-RESEARCH.md) · [Phép đo đã ghim](engineering/airc500/research-v4/REPORT.md).

## Business Profile C1 · backend v22 đang review nội bộ

Sau phản biện trên `b9edc99`, C1 so khớp bí danh Hà Nội, TP.HCM và Đà Nẵng ở selector tồn kho, điều khoản và giá. Có thể có đơn vừa bán lẻ vừa trả trước. Hai chính sách áp dụng đồng thời cho đơn đó cần được đối chiếu. Hãy chạy lại publisher kể cả khi hàm SQL kiểm tồn kho đã tồn tại. API kiểm dấu SHA-256 của phiên bản quy tắc. [Danh mục và các ca hồi quy](tests/test_knowledge_scope_aliases.py)

Bản sửa sau phản biện PR #22 đã đồng bộ với `main@5dc4ebc73c9423f360d63287d52350e2ef21a31a`. Trên database v22 hiện hữu, chạy lại publisher trước khi khởi động API. Người tiếp quản có thể dùng cùng fixture để kiểm tra câu công khai cần người duyệt đủ chuyên môn và trường hợp hai nguồn tồn kho, bảo hành hoặc thanh toán mâu thuẫn. Hai ca này là điều kiện review lại C1. C2/C3 và Commercial GA tiếp tục theo gate riêng. [Cách chạy và đối chiếu kết quả](docs/business-profile/C1-RUNBOOK.md#kiểm-tra-lại-hai-phản-biện-của-pr-22)

Nhánh `feature/business-profile-knowledge-v22` tích hợp main `16fea3d45`. Staff có thể ghi hồ sơ, SKU, offer và chứng cứ, tự duyệt dữ kiện thông thường hoặc yêu cầu người thứ hai đủ quyền. API tạo snapshot và cấp receipt nội bộ cho queue/QA/share. Local PostgreSQL 16.16 và SQLite đã đạt 29 ca C1, gồm tranh chấp thật, hết hạn, idempotency và quyền đọc nguồn. Mốc tiếp là giao diện C2, adapter WF-03/WF-13 C3 và nghiệm thu nghiệp vụ. Commercial GA giữ NO-GO. [Lệnh Docker, API, ma trận nghiệm thu và rollback](docs/business-profile/C1-RUNBOOK.md) · [SHA và CI của các mốc đã hợp nhất](docs/business-profile/INTEGRATION-BASE.md)

## Thiết kế phiên đăng nhập và khôi phục sau PR #19

Đề xuất SAA-02 mô tả thu hồi phiên trên nhiều worker, đổi refresh grant, recovery trong cooldown, chuyển khóa duy trì quota, so sánh Keycloak/Auth0 với credential local và ca nghiệm thu cho sáu rủi ro. Tài liệu giữ hợp đồng đăng ký HTTP 202 của v21. Hạng mục triển khai đầu tiên là xem và thu hồi phiên trên hai thiết bị với PostgreSQL runtime bị giới hạn. [Quyết định, quy trình kiểm thử và rollback](docs/IDENTITY-SESSION-RECOVERY.md)

## AIRC · Hợp nhất verifier và nghiên cứu ngữ nghĩa v3

Trên main sau PR #20 `16fea3d45aff62dc4ba80243fcf0791627ffb90f`, schema sản phẩm v21. Chạy `python engineering/airc500/union_release.py` để tái dựng toàn bộ phép đo từ archive đã ghim. [Phương pháp, rollback và hướng dẫn máy mới](engineering/airc500/UNION-STUDY.md) · [Kết quả và giới hạn](engineering/airc500/evidence/union-v3/REPORT.md).

## AIRC · Kiểm định chất lượng v2 và runtime

Từ main `bdc2441914478b918ea96e861aeb21f2d61655cd` (schema AMC v20), công cụ dùng kế hoạch pin, bằng chứng ký và đối chứng năm cấu hình. Trên máy mới chạy `python -m unittest discover -s engineering/airc500 -p "test_*.py" -v` trong venv engineering. [Phép đo và cách replay](engineering/airc500/QUALITY-EVALUATION.md) · [Kết quả và public pins](engineering/airc500/evidence/quality-v2/README.md) · [So hai checkpoint local](engineering/airc500/stronger/README.md) · [Giới hạn trust và intake](engineering/airc500/RUNTIME-HARDENING.md) · [Docker probe Linux](engineering/airc500/SANDBOX-CONTAINER.md). Commercial GA NO-GO, nguồn repository thực tiếp tục HOLD.

## Giới hạn đăng ký, đăng nhập, xác minh và lời mời · Đang review nội bộ

Nhánh `feature/identity-abuse-prevention` tách từ main sau PR #17 (`bdc24419`). Schema đề xuất v21 bổ sung policy và bộ đếm theo cửa sổ. API đăng ký trả 202; ứng dụng đăng nhập riêng trước bước xác minh. [Hợp đồng, quota, chạy lại và khôi phục](docs/IDENTITY-ADMISSION.md). Đợt diễn tập dùng database tổng hợp riêng. PR #16 và #17 đã hợp nhất trên main v20. [CI main sau #17](https://github.com/datnv41001/ai-company/actions/runs/45421423514).

## AIRC-500 · Thiết kế công cụ review nội bộ

Từ mốc `ece8ecc84b4938900821ff85403bb5b8243534c6`, catalog engineering có 500 hồ sơ và 12 discipline. Trên máy mới chạy `python engineering/airc500/catalog.py` từ gốc repo. [Đề xuất kiến trúc, hợp đồng, lệnh kiểm thử và backlog pilot](engineering/airc500/README.md). Mốc thiết kế ban đầu là `c1eda054`; commercial GA giữ NO-GO. Runtime AMC vẫn dùng schema v18 tại mốc trên.

**Pilot kế tiếp trên cùng nhánh.** [Quy trình chạy lại Qwen và kiểm chữ ký](engineering/airc500/PILOT.md) · [Hồ sơ thực thi và quality metrics](engineering/airc500/evidence/qwen-marketing-01/REPORT.md). Chỉ dùng Git fixture Marketing tổng hợp. PR #16 đã merge tại `49cbc0709388101c4ff6254d901e62e70a17a512` (tree `dbff352337ee9ded2721af712da3e290dba5d7be` trùng integration đã duyệt, schema v20). [CI sau merge #16](https://github.com/datnv41001/ai-company/actions/runs/45419903493). Phạm vi PR #17 là công cụ engineering thử nghiệm trên fixture tổng hợp. Giai đoạn tiếp theo cần đánh giá chất lượng theo từng vòng, kế hoạch coverage bất biến và giới hạn hạ tầng trước khi mở rộng.

## PR #16 · Tạo tài khoản và tham gia qua lời mời

PR #15 đã merge vào main tại `ece8ecc84b4938900821ff85403bb5b8243534c6`, CI sau merge đạt 3/3 job. [CI của main](https://github.com/datnv41001/ai-company/actions/runs/45363202327).

PR #16 phát triển từ commit này. Nhánh `feature/invitation-first-onboarding` dùng schema v20 với PostgreSQL 16.6 trong Docker Compose. Từ checkout của nhánh, chạy `python scripts/init_env.py` rồi `docker compose -p amc-onboarding up -d --build` với database thử riêng. Mở ứng dụng ở cổng `AMC_HTTP_PORT` (mặc định 8000). Khi dùng địa chỉ khác máy local, cấu hình `AMC_PUBLIC_ORIGIN` bằng URL gốc mà người nhận dùng để mở ứng dụng. [Thiết kế, kiểm thử và khôi phục](docs/PR16-ONBOARDING.md).

Đăng ký qua giao diện chỉ tạo tài khoản. Sau xác minh, người dùng chọn tạo workspace hoặc xem và chấp nhận quyền được mời. Owner/Admin có thể mời địa chỉ chưa đăng ký và gửi lại để thay link cũ. Hộp thư tổng hợp riêng dùng thư mục theo SHA-256 của email chuẩn hóa. Mã xác minh nằm trong các tệp `*.txt` trực tiếp của thư mục này. Link nằm trong `invitations/<invitation-id>.txt`. Chỉ đọc thư của tài khoản thử nghiệm trong terminal riêng. Giữ bản sao v18 cùng khóa ký để khôi phục. Ba pool v10/v11/v13 dùng phiên bản đang vận hành.

**Review vòng 2.** Migration 020 bổ sung khóa vòng đời theo workspace và email chuẩn hóa, đồng bộ cấp/gửi lại/nhận/thu hồi, đồng thời đóng lời mời cũ khi xóa membership. Khi nâng từ v19, sao lưu riêng DB, giữ khóa signer và chạy migrator trước API. Chạy lại ca cạnh tranh PostgreSQL bằng `python -m pytest -q tests/test_recipient_lifecycle.py` theo cấu hình CI. Job Chromium xuất ảnh `resend-{1280,390}-{stale,accepted}.png`. [Kiểm thử, backlog phục hồi và rollback](docs/PR16-ONBOARDING.md#recipient-lifecycle-v20).

## PR #15 · Xác minh email và nhận lời mời workspace

Nhánh `feature/verified-workspace-invitations` phát triển từ `d81df0be`. Compose chạy PostgreSQL **16.6**. Schema ứng dụng **v18** bổ sung tên thương hiệu và chiến dịch vào lời mời. Khi dùng bản v17 đã review tại `df48ef26`, chạy migrator để nâng cấp trước khi khởi động API mới. Commercial GA vẫn NO-GO. Xem [hướng dẫn vận hành và nghiệm thu](docs/PR15-IDENTITY.md) và [CI trên head và bản tích hợp thử](https://github.com/datnv41001/ai-company/pull/15/checks).

Trước khi chấp nhận, người nhận thấy tên và mã phạm vi, quyền bình luận, quyền quyết định và thời hạn. Đường nâng từ v16 hỗ trợ cả database đã cài pgcrypto trong schema khác. Có thể chạy lại các ca phân xử tranh khóa và kiểm tra chữ ký bằng `python -m pytest -q tests/test_verified_identity.py` trong môi trường PostgreSQL tổng hợp được cấu hình như job `api-tests`.

Người tiếp quản dùng cùng `JWT_SECRET` cho migrator và API. Chủ workspace mới xác minh email trước khi có quyền. Owner/Admin mời người dùng qua mục **Quản lý người nhận và lời mời**. Mỗi người nhận đăng nhập, xác minh và tự chấp nhận. Ca kiểm thử phải thực hiện đủ các bước này. Trên ba pool cũ vẫn dùng đúng binary và schema v10/v11/v13 của từng pool.

## PR #14 trên main · 24/11/2026

**Đánh giá bằng AI mô phỏng đã hoàn tất. Nghiệm thu nghiệp vụ bởi con người đang chờ. Commercial GA giữ trạng thái NO-GO.** Phạm vi đã duyệt là lưu hồ sơ đánh giá nội bộ và công cụ tính lại kết quả. [Quyết định tích hợp PR #14](https://github.com/datnv41001/ai-company/pull/14).

| Mốc Git | SHA |
| --- | --- |
| Merge commit trên `main` | `0bfb839aacebbf638f683133d0da68651cadaf3e` |
| Parent 1 · base đã kiểm toán | `cce821d0f2c27f0296dab1772da7fc3af0ab14b0` |
| Parent 2 · head đã duyệt | `f459f5004ba7a2bc7fe265070621c16e2b9ea251` |
| Git tree của cả merge và head | `dbb2e046aa76e967d6b64d7692f92ba8ec63a677` |

CI push trên **commit merge** đạt 3/3 job. Ruff và 187/187 bài kiểm thử đạt, gồm PostgreSQL/RLS. Đủ 15/15 đường nâng có dữ liệu từ v1–v15 lên v16, kể cả chạy lặp. Ca riêng cho v16 thiếu 015 xác nhận migrator và API từ chối khởi động, giữ nguyên ledger, lease và snapshot đã duyệt. Chromium đạt ở 1280 px và 390 px. WF-03 và WF-13 hoàn tất với Qwen local. [CI merge #45347807436](https://github.com/datnv41001/ai-company/actions/runs/45347807436) · [CI push trước merge](https://github.com/datnv41001/ai-company/actions/runs/45345375086) · [CI PR trước merge](https://github.com/datnv41001/ai-company/actions/runs/45345414108).

Schema của bản merge vẫn là **PostgreSQL v16**. So với parent 1, Git tree của `app/`, `migrations/` và `catalog/` giống hệt. Kết quả đối chiếu bao gồm QA policy v2 và `migrations/registry-runtime.lock.json`. Trạng thái các pool dev cũ được ghi ở mục PR #13 bên dưới.

**Content/SEO.** Trên 24 ca, so với 40 nhãn **do AI phân xử**, QA v2 khớp 18, báo thừa 15 và bỏ sót 22. Precision **54,5%**, recall **45,0%**. Đa số Qwen ở ngưỡng 5/9 khớp 0, thừa 15, bỏ sót 40. Các lượt này dùng chung một checkpoint. Kết quả chưa đủ tin cậy để giao cho hội đồng AI quyền tự duyệt. [Báo cáo và cách tính](docs/reviews/ai-panel-20261124/README.md).

**Ca G02.** Nguồn cho phép chạm thấu kính bản sao và nêu bản gốc nằm sau kính. Bản viết quảng bá việc chạm bản gốc. Chỉ P178 có nhãn `body_copy · claim_evidence` trong phiếu, đồng thời chọn **13/14** cặp hợp lệ. Lời giải thích nhận xét cách diễn đạt ưu đãi, bỏ qua mâu thuẫn về hiện vật. Việc phiếu chứa nhãn này chưa chứng minh model hiểu claim. [Phiếu P178 và nguồn đối chiếu](docs/reviews/ai-panel-20261124/opinions.md#g02).

**Strategy WF-03.** Giữ finding gắn với digest đầu ra của từng run. Trong run đầu, hai finding về đơn vị cùng chỉ vào một trường. Research còn suy diễn độ phù hợp với sinh viên từ nguồn chỉ mô tả sổ A5 và số trang. Khi review, cần đối chiếu giả thuyết với dữ kiện trước khi dùng làm căn cứ cho Strategy. [Thẩm định và bằng chứng](docs/reviews/ai-panel-20261124/strategy.md).

| Run WF-03 | SHA-256 đầu ra Strategy | Finding gắn với bản đó |
| --- | --- | --- |
| Head `4a089239` · `6e2bf58c-f05f-40ed-a1c7-2b522d4a34d1` | `f14be3bf0884a845052e35beed6c55ba8f8fd8a2913012c1293c5d39c9bb42a1` | 5 · `verify_unit`, `verify_measurement_method`, `verify_measurement_window`, `verify_ratio_unit`, `baseline_evidence` |
| Merge `0ce9e1ea` · `88aa51f7-bdea-49c7-abe3-3e3b9aa69913` | `6ab88d781cb270785b8fc84d2132e44a5c84aca88f8a8160b4430dabc2cbd25c` | 3 · `verify_unit`, `verify_ratio_unit`, `baseline_evidence` |
| [Merge PR #14 `0bfb839a`](https://github.com/datnv41001/ai-company/actions/runs/45347807436/artifacts/14898673885) · `2c04ef0d-6286-4dab-ad5e-d83b0fb0604e` | `74cbe1718335821337cbca0ec0eb5480ac1c117fd9fdce41f049c16e38063264` | 5 · `verify_measurement_method`, `verify_success_metric`, `verify_measurement_window`, `verify_ratio_unit`, `baseline_evidence` |

Trên checkout của merge, hai lệnh sau đã xác minh 216 phiếu lưu sẵn và tái tạo toàn bộ điểm cùng nội dung nhận xét. Đây là bước kiểm chứng offline riêng với ba job CI. Với PowerShell, chạy từ thư mục gốc sau khi cài dependencies của dự án.

```sh
python docs/reviews/ai-panel-20261124/panel.py --validate-only
python docs/reviews/ai-panel-20261124/score.py --output scores-replay.json --opinions opinions-replay.md
```

Mốc tiếp theo là kiểm toán bản merge này. Verified Identity & Workspace Invitation Acceptance (SAA-02) là ứng viên để chốt phạm vi sau kiểm toán.

## Mốc Scheduler Wait Diagnostics trên main · 24/11/2026

[PR #13](https://github.com/datnv41001/ai-company/pull/13) đã merge vào `main` tại `0ce9e1ea20d64f75aa62161166bc9b798bffa94b`. Hai parent là `df8466d317645fbd34064406b24edabbe89033f6` và head đã duyệt `4a089239b7b4038969558dde6c902313ecf7bcb8`. Merge và head cùng Git tree `a9f5d7bf41594cba4dee3d3993f933e103cff7b4`. Mốc kỹ thuật đã hoàn tất cho phát triển nội bộ với PostgreSQL **v16**. [CI trên commit merge](https://github.com/datnv41001/ai-company/actions/runs/45342029520).

| Bằng chứng trên commit merge | Kết quả |
| --- | --- |
| [Ruff, API, PostgreSQL và RLS](https://github.com/datnv41001/ai-company/actions/runs/45342029520/job/138267704157) | 187/187 bài test. Đủ 15/15 đường nâng có dữ liệu từ v1–v15 lên v16 và chạy lặp. Ca riêng xác nhận API và migrator từ chối v16 thiếu 015, bảo toàn lease, ledger và snapshot. |
| [Chromium qua Docker Compose](https://github.com/datnv41001/ai-company/actions/runs/45342029520/job/138267704644) | WF-03, WF-13, chẩn đoán, QA và bản bàn giao ở 1280 px và 390 px. |
| [Ledger WF-03](https://github.com/datnv41001/ai-company/actions/runs/45342029520/artifacts/14897210860) | Với ba trần tổng hợp 263/264/265 micro-USD, offer lần lượt 0/1/1, giữ 0/264/264, chi 0. |
| [Qwen và fingerprint](https://github.com/datnv41001/ai-company/actions/runs/45342029520/artifacts/14896013846) | WF-03 có 4 lượt (1 `invalid_source`, sau đó thành công) và 3 finding Strategy trên bản sinh lại. WF-13 đạt 3/3. Mỗi workflow có một snapshot được khách mẫu duyệt, 0 usage chưa xác nhận và 0 khoản giữ cuối. |

Hai runtime đã được đo trên cây mã tích hợp. Windows CPython 3.12.14 có fingerprint `d300bafe3f36ed9948565d206899786d0b0e74d1273ad01435ca7907649d60ef`. CI Linux CPython 3.12.16 có fingerprint `8e7cf1dc7fe4960c0b3cd876d4a497c76a075022f809266f66b86a94087a49c0`. [Danh sách đầy đủ](migrations/registry-runtime.lock.json) giữ cả tám fingerprint lịch sử cùng các digest adapter đã duyệt. Kiểm tra image thực chạy bằng `python -c "from migrations.runtime_bundle import runtime_fingerprint; print(runtime_fingerprint())"`.

### Kiểm tra trước khi dùng chẩn đoán trên một pool dev khác

Đối chiếu danh sách replica trong cấu hình triển khai với LOGIN của từng dispatcher dành cho **database đích**, kể cả replica đang tắt. Với Compose mẫu, `scripts/init_pool.py` cấp `amc_ops_dispatch` cho một replica. Mỗi replica bổ sung cần LOGIN riêng. Khai báo toàn bộ danh sách bằng lệnh inventory bên dưới. Trong `psql` trên database v16 đích, dùng tài khoản vận hành có quyền đọc các bảng, đặt `wanted` bằng danh sách LOGIN phân cách bởi dấu phẩy, không có khoảng trắng hoặc tên trùng. Ví dụ cho pool mẫu:

```sql
\set wanted amc_ops_dispatch
BEGIN READ ONLY;
WITH wanted(login) AS (
  SELECT unnest(string_to_array(:'wanted', ','))::name
), roster(login) AS (
  SELECT unnest(expected) FROM amc_ops.dispatcher_inventory
), sessions AS (
  SELECT a.usename AS login, a.pid
  FROM pg_stat_activity a JOIN pg_auth_members m ON m.member = a.usesysid
  WHERE a.datname = current_database() AND m.roleid = 'amc_dispatch'::regrole
), names AS (
  SELECT login FROM wanted UNION SELECT login FROM roster UNION SELECT login FROM sessions
)
SELECT n.login, w.login IS NOT NULL AS expected, r.login IS NOT NULL AS registered,
       count(s.pid) AS sessions, count(h.pid) AS fresh,
       array_agg(DISTINCT h.capabilities->>'fingerprint') FILTER (WHERE h.pid IS NOT NULL) AS builds
FROM names n LEFT JOIN wanted w USING (login) LEFT JOIN roster r USING (login)
LEFT JOIN sessions s USING (login)
LEFT JOIN amc_ops.pool_heartbeats h ON (h.login,h.pid) = (s.login,s.pid)
  AND h.kind = 'dispatcher' AND h.observed_at > statement_timestamp() - interval '15 seconds'
GROUP BY n.login, w.login, r.login ORDER BY n.login;
COMMIT;
```

Mỗi LOGIN trong cấu hình phải có `expected` và `registered` cùng đúng, có ít nhất một phiên, mọi phiên có heartbeat mới và fingerprint trong lock. Kiểm tra cả LOGIN xuất hiện ngoài cấu hình lẫn replica dự kiến chưa kết nối. Nếu thiếu, hiển thị `telemetry_unknown`, đối chiếu cấu hình, inventory và heartbeat trước khi kết luận về adapter. Kết quả là một lần quan sát. Offer thực còn phụ thuộc khóa và ngân sách tại thời điểm scheduler cấp việc.

Trên PostgreSQL v16 thử riêng với hai dispatcher LOGIN, truy vấn trên đã nhận diện lần lượt LOGIN thiếu trong inventory, phiên thiếu heartbeat, đủ hai LOGIN và cả hai phiên đã ngắt. Ba DB dev có sẵn trên máy được kiểm tra trong transaction chỉ đọc. `amc_company_pool_dev`, `amc_diamond_dev`, `amc_parallel_dev` lần lượt ở v10, v11, v13. Mỗi DB có một phiên dispatcher và chưa có bảng inventory v16. Mỗi DB có 0 attempt đang mở, tổng held và spent bằng 0, 0 run lệch ledger và 0 snapshot khách duyệt. Việc bật diagnostics trên các pool đó cần một lần nâng cấp và kiểm kê riêng.

**Đối soát và rollback.** Trước khi đổi image hoặc rút một adapter, ghi lại run đang ghim, attempt còn lease, số dư ledger và các snapshot đã duyệt (ID, version, digest, quyết định). Dừng nhận việc mới, cho các dispatcher tương thích xử lý report còn lại, đối chiếu `reserved_microusd` với tổng `held + spent` theo run. Kiểm lại chính danh sách snapshot sau thao tác. Xem [truy vấn đối soát](docs/POOL-RUNBOOK.md#đối-soát). Khi cần rút tính năng, tạm dừng pool dev và giữ DB v16 để truy lịch sử. Để quay về binary cũ, thử phục hồi backup đúng schema vào DB riêng, đối soát thay đổi kể từ backup trước khi chuyển kết nối. Với v16 riêng thiếu 015, áp dụng hướng dẫn khôi phục ở phần tích hợp bên dưới.

**Nghiệm thu nghiệp vụ.** Bộ chấm mù bao gồm 12 ca Content và 12 ca SEO. [Kết quả review AI, phân xử từng ca và thẩm định Strategy](docs/reviews/ai-panel-20261124/README.md). Nhóm hiện dùng reviewer AI mô phỏng theo yêu cầu của chủ dự án. Phiếu có nguồn gốc AI được lưu riêng với điểm số, lý do và bất đồng. Năm finding Strategy trong lần chạy trên head `4a089239` cần đối chiếu đơn vị, phương pháp đo, kỳ đo, cách biểu thị tỷ lệ và số liệu nền. Bản snapshot đã duyệt trong CI là fixture kỹ thuật. Kết quả nghiệp vụ chỉ áp dụng cho các ca đã xem.


## Tích hợp PR #12 và #13 trên máy phát triển

PR #12 đã vào main tại `df8466d317645fbd34064406b24edabbe89033f6`, cùng Git tree với head đã duyệt `b69d9b45`. [CI trên commit merge](https://github.com/datnv41001/ai-company/actions/runs/45338563269). Đây là mốc trung gian trước PR #13. Commit merge của PR #12 dùng schema 15 và là base đã kiểm của PR #13.

Trên máy phát triển mới, chạy `python scripts/init_env.py`, rồi `docker compose up -d --build` và kiểm tra `docker compose logs migrate`. Migrator giữ khóa trước khi đọc lịch sử và chạy SQL cùng marker trong một transaction. DB ở v14 chạy 015 rồi 016, DB ở v15 chỉ chạy 016. Chạy lại `docker compose run --rm migrate` phải giữ nguyên marker, registry, snapshot, lease và ledger.

Nếu gặp `missing migration 015` trên DB dev đã chạy v16 riêng, dừng các service ghi và lưu bản sao DB hiện tại để đối soát. Khôi phục backup trước 016 vào **database dev riêng**, chạy migrator của nhánh này rồi so lại release, run, lease, ledger và snapshot với bản sao. Dữ liệu phát sinh sau backup cần được đối soát riêng trước khi chuyển kết nối. Nếu thiếu backup và cần giữ dữ liệu, giữ nguyên DB gốc để lập phương án phục hồi. Việc chèn tay marker 015 sẽ bỏ qua SQL tạo hợp đồng WF-03.

Trên PostgreSQL tổng hợp với cùng môi trường như job `api-tests`, chạy `python -m pytest -q tests/test_wait_diagnostics.py tests/test_wf03_budget.py`. Đặt `AMC_WF03_HOLD_EVIDENCE` thành thư mục đích để lưu hai biên ngân sách và dòng ledger thật. Mỗi lệnh `python tests/check_postgres_upgrade.py --from-v14`, `--from-v15` hoặc `--from-isolated-v16` cần một database kiểm thử trống riêng. CI cũng diễn tập lại từ v1–v13. Job `workforce-model` ghi snapshot chẩn đoán cho WF-13 và WF-03 khi chạy Qwen local. Xem các artifact `wf03-director-ledger` và `pool-model-measurements` trên chính run tương ứng với head của PR.

### Kết quả ngưỡng ngân sách WF-03

Ở commit tích hợp RED `8bed9cb`, chẩn đoán dùng planner cũ để tính 385 micro-USD, trong khi PostgreSQL cấp offer và ghi một khoản giữ 264 cho request của `director@2`. Trên fixture giá tổng hợp, thử ba trần 263, 264, 265 micro-USD. Trần 263 phải trả `budget_insufficient`, có 0 offer và giữ 0. Ở 264 và 265, scheduler phải cấp một offer và ledger ghi `held=264`, `spent=0`. Bài test cũng so toàn bộ JSON của request đã cấp với request do adapter đã ghim tạo ra. Các con số này mô tả fixture dùng kiểm thử.

## Review Scheduler Wait Diagnostics

Schema 16 bổ sung inventory, heartbeat và snapshot chẩn đoán sau migration 015 của WF-03.

Trong DB dev, khởi động Compose và cấp các LOGIN riêng theo [runbook pool](docs/POOL-RUNBOOK.md). Khai báo danh sách đầy đủ dispatcher của **database này** bằng tài khoản migrate. Với cấu hình mẫu có đúng một dispatcher, chạy lệnh sau sau khi đã tạo LOGIN.

```sh
docker compose run --rm migrate python scripts/provision_pool.py inventory amc_ops_dispatch
```

Mỗi replica dùng LOGIN riêng. Truyền tên của tất cả replica vào lệnh inventory khi thay đổi pool. Dispatcher và worker tự báo heartbeat khoảng 3 giây/lần cùng fingerprint và capability. Dữ liệu tối đa 15 giây tuổi mới được dùng để kết luận thiếu adapter. Phiên dispatcher còn kết nối nhưng thiếu heartbeat, LOGIN dự kiến vắng mặt hoặc chưa khai báo danh sách cho kết quả `telemetry_unknown`. Worker bận được nhận diện qua lease dù không poll trong lúc suy luận. Khi bộ dựng yêu cầu của dispatcher khác fingerprint với API, phép tính ngân sách được đánh dấu chưa đủ dữ liệu.

Owner/admin mở **Điều phối Marketing AI → Xem kết quả và chi phí → Xem lý do node chờ**. API `GET /api/tenants/{tenant}/workforce/runs/{run}/wait-diagnostics` đọc một snapshot PostgreSQL cho các node cùng run/revision. Trường `candidate` đối chiếu tập ứng viên SQL của scheduler. Bước cấp offer còn đối chiếu runtime, ngân sách node/run/agency và lease dưới khóa scheduler. Một report có thể chờ adapter sau khi worker đã gửi. Giao diện trả thời điểm quan sát để nhận biết dữ liệu đã cũ. Client A/B và tài khoản tenant khác không có quyền đọc chẩn đoán.

RED tại `47f47cd` cho thấy API trả 404 cho quản trị viên. Chạy `python -m pytest -q tests/test_wait_diagnostics.py` với DB tổng hợp và môi trường PostgreSQL trong CI. Có ca READ ONLY, so ứng viên với offer thực, heartbeat hết hạn, report còn giữ, nhiều lý do đồng thời và thu hồi quyền qua suite chung. Job model ghi `wait-diagnostics-measurements.json` trong lần chạy Qwen có snapshot khách mẫu duyệt. Khi rút, tắt truy cập vào chẩn đoán và trả về image tương thích sau khi drain. Giữ bảng telemetry trong schema 16 để tiếp tục đối chiếu. Thay đổi inventory và heartbeat chỉ ghi bảng vận hành riêng.

## Review WF-03 · Research → Strategy

Nhánh độc lập từ `3af08b75b661e1d1681a5825939f7ce8656746b8` bổ sung schema 15 và định nghĩa `WF-03/research-strategy-draft@1`. Ba hợp đồng bắt buộc là director, research và strategy phiên bản 2. Manifest ghim đầu ra Strategy. Director viết hai chỉ dẫn riêng cho brief. Server nối Research → Strategy rồi kiểm tra và đóng băng DAG theo hợp đồng. Backend dùng đúng checkpoint Research của cạnh trực tiếp để ghi bằng chứng. Chỉ nội dung Strategy được trình dưới dạng đề xuất. Số liệu nền cần khớp nguồn riêng đã dẫn. Người QA kiểm tra ngữ nghĩa, digest và revision trước khi chia sẻ snapshot. Các nhận xét chỉ áp dụng cho bản nháp nội bộ.

Trên DB dev riêng, chạy Compose rồi nhập bản phát hành với `docker compose run --rm migrate python migrations/apply.py --publish-registry catalog/research-strategy-v1.json`. Cấp workflow theo campaign ở màn hình điều phối. Khi rút, ngừng cấp mới, giữ dispatcher tương thích đến khi hết report và đã đối soát hold. Kiểm kê trước khi gỡ image. Dùng schema 15 để truy lịch sử. Diễn tập khôi phục trên bản sao khi cần quay về binary/schema 14.

RED có tại `8b0801d`. Chạy `python -m pytest -q tests/test_research_strategy.py` trên PostgreSQL tổng hợp với biến môi trường của CI. Job model lưu `research-strategy-measurements.json`. Workflow CI chạy Chromium ở hai kích thước và nâng lặp 14 đường từ DB có dữ liệu. Reviewer nên thử tráo nguồn và thu hồi Strategy ngay sau Research rồi kiểm tra snapshot và ledger.

[Bộ ZIP nguyên bản cho hai reviewer chấm riêng](docs/reviews/landing-qa-blind-20261124.zip) có SHA-256 `0ca12b9ce5e4b044e7be869ab247fe05eab74079f13856c0f44c1b311199fe36`. Hai reviewer chỉ nhận ZIP này. Người tổng hợp lưu hai phiếu có cùng cases_digest, lập phiếu phân xử có lý do cho từng bất đồng rồi chạy công cụ tính điểm trên phiếu đã chốt. Sau khi nhận đủ hai phiếu, chạy `python docs/reviews/landing-qa-eval/adjudicate.py A.json B.json --reviewer REVIEWER_ID --output consensus.json`. Lệnh kiểm tra danh tính phân biệt và digest bộ đề rồi giữ nguyên hai ý kiến ở ca bất đồng. Người phân xử điền findings cuối, lý do trong note và đánh dấu reviewed trước khi chạy `evaluate.py --labels consensus.json --output independent-report.md`. Điểm nghiệp vụ đang chờ hai phiếu.

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

## Business Profile & Brand Intelligence · increment Marketing đề xuất

Để tiếp quản C2 sau vòng duyệt C1, bắt đầu từ [hồ sơ doanh nghiệp và năm luồng nghiệm thu](docs/business-profile/C2-WORKSPACE.md). Thiết kế dùng scope công ty theo client, giữ override của từng brand và cho Solo tạo brief nháp khi còn thiếu dữ kiện. [C3](docs/business-profile/C3-KNOWLEDGE-PROJECTION.md) mô tả projection và ba ranh giới kiểm tra trước khi kích hoạt adapter mới. Chỉ ghi nhận một luồng C2 đạt khi có lần chạy trình duyệt thật với API PostgreSQL ở đúng commit.

Sau khi đồng bộ schema v20 từ `49cbc070`, C0 có [sáu quyết định, snapshot ví dụ và lệnh kiểm tra](docs/business-profile/README.md), [kế hoạch C1](docs/business-profile/C1-PLAN.md) và [năm tình huống C2/C4](docs/business-profile/C2-C4-ACCEPTANCE.md). Từ thư mục gốc chạy `python -m unittest discover -s docs/business-profile -p test_c0.py -v`. Chờ review độc lập C0 trước PR C1. Kiểm số migration còn trống trên main khi chuẩn bị tích hợp, kể cả nhánh Identity đang đề xuất. Commercial GA vẫn NO-GO.
