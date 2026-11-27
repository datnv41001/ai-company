# Vòng #63 · Một quyết định Marketing từ nhiều nguồn

## Base và phạm vi

PR #62 đã merge nội bộ vào main tại `6a11bf4d97e7d1be1f5e0da1d503a54eabd15ad1`. Hai parent là `2daa715d` và `365cdbbf`; tree `3b8b429a5b0da890a81fbec5cf41e7a3ae6a9942` trùng candidate và trial đã duyệt. [Chứng nhận main, JUnit và migration](MAIN-62.json) · [Bằng chứng #62 được giữ theo commit](https://github.com/datnv41001/ai-company/tree/ff842385fdef3b21007a9d4ed51d368de5ed0620/docs/evaluation/round62-verification)

Marketing lead giao việc tìm hướng nội dung cho một sản phẩm vật lý và một lớp học dịch vụ. Người phụ trách Content cần biết sẽ phác thảo tài sản nào, cho ai, dựa trên dữ kiện nào và ai sẽ duyệt. Đầu ra vòng này là bản làm việc ngoại tuyến chạy được trên dữ liệu tổng hợp. Người dùng thực chưa nghiệm thu.

## Baseline có những bằng chứng nào?

- **WF-03 @3 có receipt Qwen thực.** Trong ca vật liệu trên trial #62, Research @4 ghi phân khúc là “Hà Nội”. Câu hỏi lặp lại giả thuyết nhà thầu ưu tiên tính số thùng và phí giao. Strategy @4 dùng cùng một câu cho hành động đo và cách đo. Hai nguồn F1/F2 chứa giá, phạm vi và quy cách đóng gói. Chưa có quan sát người mua trong hai nguồn này để xác nhận ưu tiên đó. Bản ghi dừng ở `awaiting_qa`. Đây là giới hạn của một ca. [Checkpoint, đầu ra, digest và artifact gốc](ARCHIVED-WF03.json)
- **Retry là smoke khác.** Các lượt head và integration #62 có `invalid_source` ở lần đầu của Strategy trong smoke gắn WF-03 @1. Lần sau thành công. Receipt không cho biết nguyên nhân của giá trị sai. Code cũ trong `app/research_strategy.py` và các implementation C3 @4 phải được kiểm riêng. [Smoke và hằng workflow](../../../tests/test_research_strategy.py) · [Adapter @4](../../../app/c3_skill_library.py)
- **Thử thách kiểm soát được trên brief mới.** Hai fixture có câu trả lời decoder cố định; runner gọi request, validator và staff composer đã phát hành. Một checkpoint có thể ghi ưu tiên theo dõi nhân viên và dẫn đúng ID của quan sát tách lô hàng. Bước kiểm hợp đồng chấp nhận câu đó. Người biên tập phải đọc lại nguồn, giới hạn mẫu và bằng chứng trái chiều. Thử nghiệm đo khả năng phát hiện ở các bước đã gọi; quyết định của người QA cuối chưa được đo. [Release bất biến](../../../catalog/research-strategy-v3.json) · [Runner và fixture](../../../scripts/strategy_study.py)

## Quyết định thiết kế

Dùng hai checkpoint @4 trên cùng brief để tạo bản làm việc theo nguồn. Đối chiếu ở cấp revision, quyền sử dụng, đối tượng quan sát, tình huống mua, ngày hiệu lực và cutoff. Lưu đoạn trích để người đọc kiểm lại. Quyết định có thể là đề xuất nội bộ, cần thêm dữ kiện, có bằng chứng xung đột hoặc cần làm rõ brief.

Các lựa chọn, loại hành động quan sát và giới hạn nguồn do người biên tập mô tả trong dữ liệu tổng hợp mở. Kết quả đo toàn bộ quy trình đã mã hóa; khả năng đọc hiểu văn bản tự do, tự khám phá phương án và đóng góp riêng của mô hình cần thí nghiệm khác. Nhận định vượt đoạn trích cần người đọc xác minh. [Phương pháp nghiên cứu và rubric](METHODS.md) · [Projection](../../../scripts/strategy_workpaper.py)

Giữ lát cắt ngoại tuyến vì release @3 ghim schema, mã adapter và bộ phương pháp. Đường tạo manifest hiện có yêu cầu những lựa chọn như kênh và KPI; quyết định giữ trống chúng cần hợp đồng có version và authority riêng trước khi nối runtime. Vòng này thêm runner, projection, fixture, kiểm thử và bước CI xuất evidence. Registry, ledger, quyền, writer, QA, migration, snapshot và WF‑08 giữ bản đã nghiệm thu. [Manifest hiện hữu](../../../app/c3_projection.py) · [Bộ artifact C3](../../../app/c3_assets.py)

## Đọc bản giao và so đối chứng

Từ checkout đã cài `requirements-dev.txt` trên Python phiên bản của CI:

```shell
python -m scripts.strategy_study --output study-review
python -m pytest -q
ruff check app tests migrations scripts
```

Mở `study-review/index.json`. Mỗi hàng ghi digest gói nguồn, kết quả và digest của hai tệp. `before.json` có ngữ cảnh gửi từng role, checkpoint và nội dung staff. `after.json` có ma trận nguồn dưới Research, phương án và điều kiện dưới Strategy. Content đọc `WORK-ORDER.md` trong cùng thư mục để nhận việc hoặc thấy lý do chờ. Mỗi lần xuất dùng thư mục đích mới. CI xuất cùng cấu trúc vào `strategy-study-head` và `strategy-study-integration`.

Trên chín tình huống mở, một ca đủ căn cứ lập bản nháp chờ duyệt, năm ca có hướng chiến lược có điều kiện nhưng chưa giao Content và ba ca giữ cả lựa chọn. Đây là số ca trong bộ đối chứng, chưa đo tỷ lệ thành công trên khách hàng thực. Bộ targeted trên Windows/PostgreSQL đạt 27/27, gồm cả các ca hiện hữu về thu hồi nguồn, runtime/QA, snapshot và từ chối manifest bị đổi dưới cùng số version. [So sánh và tiêu chí từng ca](PAIRED-STUDY.md)

| Ca cần mở | Quyết định người nhận kiểm |
|---|---|
| `route-shift` | Kiểm hướng sơ đồ hai khung ca bàn giao, wording về khay chia lô thụ động, nguồn quan sát và vai trò duyệt |
| `route-storekeeper`, `route-corrected-observation` | Đổi người quyết định hoặc sửa đúng một quan sát; so sự thay đổi sang kiểm kê |
| `route-disagreement` | Hai hành vi trái chiều; so lý do giữ việc với các nguồn độc lập |
| `route-withdrawn-channel-expired-measure` | Tách quyết định về đối tượng/thông điệp khỏi quyền dùng kênh và khả năng đo |
| `studio-first-visit` | Kiểm bản nháp hướng dẫn chuẩn bị trước lớp, vật dụng có thể nêu và bước duyệt |
| `studio-clarify`, `studio-unrepresented` | So thiếu brief với trường hợp có quan sát nhưng ngoài phân khúc |
| `studio-foreign-record` | Cùng kết luận hợp lệ khi thêm nguồn thuộc client khác; nội dung ngoài scope phải vắng trong bản bàn giao |

## Quyền, kiểm thử, chi phí và rollback

CLI chỉ replay các fixture tổng hợp trong repository. Các bộ lọc của workpaper bảo vệ tính nhất quán trong thí nghiệm này; quyền đọc dữ liệu live vẫn cần cơ chế thực thi của runtime. Hành vi production về role, revision, QA, ledger và recovery được hồi quy qua các suite hiện có trên PostgreSQL. Đo coverage từng ca và xem cả thử nghiệm bị bác bỏ trong [hồ sơ phản biện](CHALLENGE.md). Để rollback prototype, ngừng chạy runner hoặc revert thay đổi qua review. Không có migration cần đảo.

Phê duyệt Qwen chỉ cho CI chuẩn. Bảng số liệu đi kèm bằng chứng của draft phân biệt token riêng pool smoke và thời gian toàn job; chi phí GitHub Actions là unknown. Development fixture, kiểm đối chứng và workpaper không gọi inference. Chưa đo giờ người biên tập, doanh thu hay hiệu quả chuyển đổi.

## Việc còn cần đúng người quyết định

- **Product Owner và trưởng Marketing** quyết định có đưa thử nghiệm sang release nội bộ mới khi có quyền dùng nguồn thật, hợp đồng mã hóa quan sát và người nhận công việc. Chưa có quota load cho AMC-R60-03.
- **O-09** chờ custodian/vault và kiểm tương đương thông tin quan sát giữa các nhánh trước khi khóa. Cohort 12 họ/24 thẻ chưa niêm phong, chưa chạy. AMC-R62-01/02 được ghi vào backlog với điều kiện xử lý. [Sổ cơ hội và điều kiện đóng](../../research/PRODUCT_OPPORTUNITIES.md)
- **Practitioner** vẫn có 0 công việc được doanh nghiệp nghiệm thu; chi phí đầy đủ trên mỗi việc được nghiệm thu là `null`. Ước lượng 875–1.510 phút cho tám work order chưa được đo. [Pilot v2](../round62/PILOT-DECISION.md)

Reviewer có thể bắt đầu bằng cách đổi người ra quyết định, thu hồi quyền một nguồn, hoặc thêm quan sát mâu thuẫn, rồi kiểm cả hướng thông điệp và tài sản mà Content thực sự nhận. Dừng trước merge. Production và Commercial GA **NO-GO**.
