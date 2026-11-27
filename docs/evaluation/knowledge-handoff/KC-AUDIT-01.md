# AMC-KC-AUDIT-01 · Kiểm toán tri thức và bàn giao dự án

**27/11/2026 · Trình Independent Review.** Người kiểm là Codex trong worktree tài liệu tách từ main #63, dùng PowerShell, Git, GitHub CLI và Python trên Windows. Kết quả kỹ thuật áp dụng cho đúng cây. Phép tiếp quản bởi AI mới cần receipt riêng. Production **NO-GO**, Commercial GA **NO-GO**.

## Main và candidate

| Đối tượng | Phép kiểm và kết quả |
|---|---|
| Main | `053410d161b15285a1ef264f853d4920a3d559e1`, tree `a63361c7673ada6121117028f92aebcb3b8aecd1`. #63 đã merge, CI 3/3, 727 đạt và 2 skip, nâng 22 đường tới v26, restore 34 bảng. |
| Draft #64 | `a0c43a15dbcec783a859c4c525fec2671206483c`, tree `1c6779ae574d0cd2efd5c8f8798162a7438a0b52`. Head chưa thuộc main. Trial `80fa77de08afbe0b308fd56ddf3738fbf0b2938d` có cùng tree. CI cuối 9/9 qua push, PR head và trial; mỗi API job 767 đạt, 2 skip. Cần quyết định Independent Reviewer trên head này. |
| Negative results | R64-01 có bản sửa staff v2 để reviewer kiểm. R64-02 vẫn mở: bốn thao tác chuyển tự nhiên thành công, hai đối chứng trạng thái/thời gian trả 409. Chromium Storyboard từng timeout ở trial; lần chạy lại riêng API integration trên cùng tree đạt. Không coi lần chạy lại là phép tái hiện lỗi Sales. |
| Evidence | Proof commit `f4f0d990e7841e52173b1f733f2f6649db6ad1c5`. ZIP gồm 69 mục, 2.818.353 byte, SHA-256 `82a1c5c452b7573bb37e024a1a0792d896f163f2eb934e3150dca8da2de4d292`. |

Các URL job/run, PR và head đầy đủ nằm trong [biên nhận đối chiếu](KC-AUDIT-01-REFS.json). Báo cáo CI dùng log và JUnit của lần chạy đã có. [Bằng chứng cố định của #64](https://github.com/datnv41001/ai-company/blob/f4f0d990e7841e52173b1f733f2f6649db6ad1c5/docs/evaluation/round64-closure-proof/START-HERE.md)

## Bảy phát hiện và nơi chịu trách nhiệm

Đường dẫn và dòng ở cột đầu áp dụng cho main `053410d161b15285a1ef264f853d4920a3d559e1` trước bản sửa. Mỗi hàng chỉ tới nơi tiếp tục cập nhật sau audit.

| ID và vị trí gốc | Hiện trạng và rủi ro | Xử lý, chủ sở hữu |
|---|---|---|
| AMC-KC-01 · `HANDOFF.md:3`, `docs/KNOWLEDGE_MAP.md:3`, `docs/IMPLEMENTATION_STATUS.md:11` | Người mới gặp công việc vòng trước trước khi biết head nào đã vào main. | Đã đặt một điểm vào [HANDOFF](../../../HANDOFF.md); knowledge map và status trỏ về đó. Maintainer kiểm lại Git/CI khi đổi head. |
| AMC-KC-02 · `docs/PRODUCT_SPEC_V1.md:269`, `docs/ADR-001-OWN-SaaS-CORE.md:3` | Stack ở đặc tả là đề xuất; người đọc có thể lập kế hoạch thay implementation đang hoạt động. | Đã ghép từng lớp với entry point, phạm vi và giới hạn tại mục 10, từng pha với bằng chứng tại mục 14 [đặc tả](../../PRODUCT_SPEC_V1.md). Chief Product Architect giữ ADR; đổi kiến trúc cần quyết định riêng. |
| AMC-KC-03 · `docs/IMPLEMENTATION_STATUS.md:23` | Tám trạng thái chưa có đối chiếu với L0–L6; dễ đọc “tích hợp” thành nghiệm thu bởi khách hàng. | Đã ghi ánh xạ và điều kiện ở [từ điển trạng thái](../../IMPLEMENTATION_STATUS.md). Marketing Domain Expert chịu trách nhiệm bằng chứng practitioner; reviewer kiểm phạm vi. |
| AMC-KC-04 · `docs/SECURITY_AND_GA_BLOCKERS.md:22` và `:50` | Checklist phát hành và danh sách test có thể làm người đọc hiểu sai control đã triển khai hoặc đóng gate sớm. | Đã chỉ ra mã/test nội bộ, bằng chứng khôi phục và phần môi trường đích còn thiếu ở [security gates](../../SECURITY_AND_GA_BLOCKERS.md). Security/operations owner xuất trình chứng cứ trước quyết định release. |
| AMC-KC-05 · `docs/PRODUCT_SPEC_V1.md:394`, `AGENTS.md:13`, `.github/pull_request_template.md:18` | Decision Log ghi D-009–014 theo thời điểm. Chưa có bảng phân vai bốn chuyên môn và cách đọc trạng thái review lịch sử. | Đã giữ quyết định cũ, ghi thẩm quyền và cách sinh task tại [AGENTS](../../../AGENTS.md), nhãn provenance tại mục 17, năm verdict tại [mẫu PR](../../../.github/pull_request_template.md). Product Owner quyết định thay đổi charter; Independent Reviewer chấm đúng cây. |
| AMC-KC-06 · `docs/IMPLEMENTATION_STATUS.md:36`, `HANDOFF.md:43` | Năm PR vẫn OPEN dù head đã thuộc ancestry main. Danh sách PR mở dễ dẫn tới merge lặp hoặc hiểu đó là năm thay đổi chưa tích hợp. | Đã kiểm từng head bằng Git và so trạng thái GitHub. Xem bảng sau. Việc đóng PR và lưu lý do thuộc maintainer khi có quyền. |
| AMC-KC-07 · `AGENTS.md:13`, `.github/workflows/ci.yml:313`, `docs/evaluation/round62/BENCHMARK.md:3` | Một job Qwen có thật hoặc protocol cũ có thể bị đọc thành ngân sách dài hạn. | [Ma trận quyền](../../../AGENTS.md) yêu cầu kiểm scope/fixture/giới hạn/retry theo từng lượt. Owner ngân sách và dữ liệu duyệt ngoại lệ; AI Agent Architect lưu receipt. O-09 còn chờ custodian và vault riêng. |

## Ancestry và trạng thái hành chính

| PR | Head kiểm bằng Git | GitHub | Head là ancestor của main #63 |
|---|---|---|---|
| #50 | `104af78ba2475973404c1043706042595b3b97bf` | OPEN | Có |
| #51 | `a5909321ed012c6ea99fcc0fdfadceb3c334c3ca` | OPEN | Có |
| #52 | `95aed621381c782114b18521d2b2d58eb17a7828` | OPEN | Có |
| #54 | `eff86cda2f99dd10244dc8127451e941bb546a3c` | OPEN | Có |
| #55 | `1202b4321ecd452d3b4bb2373a65b780c63e24f9` | OPEN | Có |

Đối chứng #53 và #63 là MERGED/ancestor; #64 là OPEN/draft và không thuộc ancestry main. Maintainer có thể ghi lý do lịch sử nếu Product Owner yêu cầu thu dọn PR.

## Kiểm kê nguồn, quyết định và giới hạn

[Bản đồ nguồn chính thức](../../KNOWLEDGE_MAP.md) chỉ nơi cập nhật từng loại tri thức, gồm cả ADR, catalog, giấy phép, research, evaluation và vận hành. [Ma trận thẩm quyền](../../../AGENTS.md) và [sổ quyết định](../../PRODUCT_SPEC_V1.md) quy định cách ghi người quyết định và phạm vi.

| Nguồn | Điều nguồn xác lập | Ranh giới |
|---|---|---|
| Yêu cầu chủ dự án AMC-KC-AUDIT-01, SHA-256 `593429f7392694c3262ed976b99b5b3a1e09cec93044cc2d2cc67c8ca7eac3ad` | CONFIRMED: 49/37/24, bốn vai trò chuyên môn, phạm vi audit và điểm dừng. | Phần phân vai là diễn giải vận hành. Nguyên văn một phiên bản MASTER DIRECTIVE độc lập chưa được xác thực (UNKNOWN). |
| Bản continuity do dự án lưu ngày 27/11, SHA-256 `d006f7d4f93c846cc3b5289f3d8eca9767eca227bbfd8261a5eece48e195e72f` | `AMC_MASTER_CONTINUITY_2026-11-27.md` dòng 27 mô tả bảy lớp; 1433–1459 ghi thứ tự đề xuất P00–P12; 1678–1690 ghi nghĩa L0–L6. | Bản lưu chứa nhiều mốc thời gian. Roadmap tham chiếu là PROPOSED; thứ tự hoặc chiến lược model mới chỉ thành ACCEPTED khi có quyết định của owner. Không cần bản lưu riêng để đọc các mapping trong repo. |
| Git, CI, JUnit và evidence ở bảng đầu | VERIFIED trên SHA và fixture nêu rõ. Main tích hợp #63. | Quyết định merge, xác nhận nghiệp vụ, production và Commercial GA tách biệt. |
| Cold drill #53 | Có transcript và smoke lịch sử cho head #53. | Không dùng làm kết quả AI mới của cây audit. [Phiên lịch sử](FINAL-53.md) |

Chưa có quyết định mới cho paid inference, benchmark, thay stack, quyền dữ liệu, production hay GA. Nếu cần xác nhận nguyên văn directive cũ, Product Owner cung cấp phiên bản đã duyệt hoặc phê chuẩn bản diễn giải. Việc chỉ định custodian/vault O-09 thuộc chủ dữ liệu. R64-02 thuộc Independent Reviewer và owner nghiệp vụ tại phiên bản được trình.

## Tái lập và rollback

[Biên nhận checkout sạch, smoke và giới hạn phép thử độc lập](KC-AUDIT-01-DRILL.md). Verdict cho tiêu chí AI mới là **NOT_VERIFIABLE**; audit dừng tại Independent Review.

1. Ghi `git status --short --branch`, `git rev-parse HEAD` và `git rev-parse "HEAD^{tree}"`. Đối chiếu main và head trong biên nhận bằng `gh pr view 64 --json state,isDraft,headRefOid,baseRefOid` và `gh api repos/datnv41001/ai-company/git/ref/heads/main`.
2. Với từng PR thành phần, chạy `git merge-base --is-ancestor <head> 053410d161b15285a1ef264f853d4920a3d559e1`. Mã thoát 0 xác nhận quan hệ Git. Trạng thái OPEN/MERGED lấy riêng bằng GitHub CLI.
3. Kiểm file thay đổi bằng `git diff --name-status 053410d161b15285a1ef264f853d4920a3d559e1 HEAD`, rồi `git diff --check 053410d161b15285a1ef264f853d4920a3d559e1 HEAD`. Xem scope diff, biên nhận và giới hạn trong gói đi kèm. Không phát sinh lượt model hoặc CI mới cho các kiểm tra tĩnh.
4. Nếu cần rút bản tài liệu đã tích hợp, maintainer revert các commit audit theo thứ tự mới nhất trước trên nhánh sửa tài liệu, kiểm lại diff và liên kết, gửi review. Giữ nguyên main sản phẩm, quyết định cũ và proof commit #64 làm mốc đối chiếu.
