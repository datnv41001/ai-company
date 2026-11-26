# Nghiệm thu nội bộ · Content đến kết quả tiếp nhận

**Bắt đầu ở đây.** Người làm Content nhận một brief có dữ kiện đã ký, bàn giao thông điệp cho người dựng và nhận lại quyết định QA trên đúng bản. Studio tạo gói phân phối minh họa nối storyboard với landing đã duyệt và ghi lại đường đi của yêu cầu mua trong sandbox. Mục tiêu nghiệm thu là biết bản nào tạo ra tài sản nào và ai được phép dùng tài sản đó. Việc người mua thật có phản hồi tốt hơn cần phép thử riêng.

## 1. Tích hợp đã được duyệt

PR #59 ở head `01295a7eaf8a4650c417df4f9dbcba751addc7c0` được merge vào main `4140563a89539acd19f1a7d5a16662c8dec5f6af`. Hai parent lần lượt là `1c40ad3185ac49415c3f555bb5b6406e2cdd8cb1` và head trên. Cây sau merge và trial `3e1e2d722351a1871f35439c9bdb2f2d50c4211b` cùng bằng `00f5639d05f5250bd7a491c28f787b784c386a03`. Người duyệt chấp thuận tích hợp WF-08 opt-in trong môi trường phát triển nội bộ. [PR được duyệt](https://github.com/datnv41001/ai-company/pull/59) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45796758300)

## 2. Xử lý từng phản biện

| ID | Đầu ra để kiểm | Phạm vi |
| --- | --- | --- |
| R59-01 | Bản @2 có checkpoint của `ai-copywriter-content-strategist`, digest bàn giao cho storyboard, và một dòng cho mỗi nghĩa vụ của brief. | Ngôn ngữ có kiểm soát cho purpose, style, requirements và acceptance; phần chưa hiểu cần chủ brief làm rõ. [Các mẫu đã hỗ trợ](../../WF08-CONTENT-HANDOFF.md) |
| R59-02 | Người có quyền sửa bản hiện tại bằng hook, lời đọc/caption có kiểm soát, chỉ dẫn hình, thứ tự cảnh, timeline và note nội bộ. | Revision mới và QA mới. Điều kiện thương mại, qualifier và quyền có nguồn. [Payload và quy tắc](../wf08-storyboard/EDITORIAL-AND-HOOK-TRIALS.md) |
| R59-03 | Biên nhận so cam kết trước/sau. Chế độ hook-only giữ thân, thời gian, visual, CTA, offer, landing và phân phối; thay đổi nhiều biến được phân loại ở chế độ editorial. | Thiết kế offline; distribution pin được kiểm tại thời điểm khóa. Cần ký lại gói có chứa bản mới trước khi dùng. |
| R59-04 | Từ một run có thật trong PostgreSQL đến edition, preview ký độc lập, file landing, visit, submission, CRM và phép đọc measurement. | Mỗi tác vụ kiểm lại manifest, QA và scope. Hai run của Studio và Video có ID riêng, dùng chung bộ nguồn có version. Storyboard nội bộ giữ giới hạn portal. |
| R59-05 | Dispatcher tự tái tính trên envelope đã ghim. Xung đột dữ kiện/policy dừng để sửa nguồn. Sai digest checkpoint dừng để điều tra. Worker báo từ chối trên đầu vào hợp lệ chỉ gây lỗi output có thể thử lại. | Trần retry, lease và cơ chế xử lý transport/model của pool còn hiệu lực. Ledger giải phóng hold đúng một lần; không tạo deliverable cho run terminal. [Journal ba lần thử lịch sử](../wf08-storyboard/failed-policy-conflict.json) · [Test mailbox và ledger](../../../tests/test_video_storyboard.py) |

## 3. Lần theo một hành trình

1. Chủ brief nộp task, ghim business brief, brand, quyền và claim vào manifest. Registry chạy đúng version do admin kích hoạt trong campaign.
2. Dispatcher cấp lease trong PostgreSQL. Với @2, Director giao Content, Content tạo `handoff_json`, storyboard xác minh digest của checkpoint đó trước khi tạo shot list và phụ đề.
3. Worker nộp checkpoint và tài liệu đang chờ QA. Editor sửa trên revision/digest đã xem. Người QA có thẩm quyền duyệt đúng nội dung và nguồn hiện hành.
4. Studio có một landing đã được duyệt. Chủ gói yêu cầu dựng preview từ đúng bản storyboard. Server kiểm các revision nguồn dùng chung, hai run, manifest, plan, quyền, QA và hash file. Một người khác ký preview.
5. Cùng ID distribution đi vào visit và submission. Hồ sơ Marketing/CRM nhận đúng thông tin gửi form. Measurement tổng hợp sự kiện của plan. Receipt ghi từng ID/digest để có thể đi ngược chuỗi. [Ca PostgreSQL từ API](../../../tests/test_storyboard_distribution.py)

## 4–6. Bản giao và brief mới

Khe Gọn cung cấp ca RFQ cũ. Mép Giấy là brief tổng hợp mới cho một thẻ so màu ở nhà in, với đối tượng mua và yêu cầu báo giá riêng. So sánh cả hai brief RFQ và giữ nguyên sản phẩm ở phép thử thứ hai để cô lập ảnh hưởng của purpose/style. Ca có yêu cầu thu âm phải hiện `unsupported`; điều kiện cần xác nhận phải hiện `clarify` và chặn QA. Nguồn giá và qualifier chỉ đi từ manifest. [Dữ liệu thử, Content và các trạng thái QA](../../../tests/test_storyboard_brief.py)

Giữ riêng brief, checkpoint Content, storyboard thô, bản đã sửa, revision, digest, người QA và media bytes. Artifact CI `connected-review-head` hoặc `connected-review-integration` có ba thư mục `content`, `edition` và `journey`. Trong hồ sơ journey, mở `preview.webm`, `captions.vtt` và `landing.html` tại chỗ. Mở `receipt.json` để kiểm trạng thái của cùng lần chạy. So ID trong một bộ hồ sơ; khi chạy lại database sẽ cấp ID mới.

## 7–9. Giới hạn, nghiên cứu, chi phí

Adapter là bộ soạn tất định. Animatic minh họa dọc 540×960, 1 fps, không tiếng. Chưa xác nhận footage thật, hiệu quả creative, năng lực lãnh đạo Marketing tổng quát hay mức chất lượng cho ngành bất kỳ. Khe Gọn có `primary_measurement=null`; funnel vẫn là `approved_plan_lifetime`. Proposal phân bổ 21 ngày và follow-up 7 ngày chưa chạy. [Định nghĩa RFQ và nguồn](MEASUREMENT.md)

Nguồn nghiên cứu gồm ABCD, TikTok, kiểm soát biến, feedback theo phiên bản và giấy phép Remotion được ghim. Quyết định là dùng renderer hiện có, tách ý tưởng khỏi claim, và kiểm bằng snapshot đúng revision. Hybrid chỉ ở mức đề xuất. [Sổ nghiên cứu](../../research/CONNECTED-CREATIVE.md)

Có 0 practitioner tham gia và 0 quyết định nhận việc thật. Chi phí model và traffic cho runtime tổng hợp bằng 0. Công người, thiết bị và giá thành đầy đủ trên một việc được người dùng nhận chưa đo. [Nhiệm vụ nhỏ và phiếu ghi thời gian/chi phí](PRACTITIONER.md)

## 10. Chạy lại trên máy khác và thẩm định tiếp

Dùng môi trường PostgreSQL cục bộ và runtime lock đúng checkout theo [handoff Docker](../../../HANDOFF.md) và [cài registry](../wf08-storyboard/RUNTIME.md). Các lệnh test dưới đây cần database dev `amc_test*` trên loopback, migrator và role runtime RLS như job `api-tests` trong [CI](../../../.github/workflows/ci.yml). Registry @2 phải được publish từ `catalog/video-storyboard-v2.json`. CI chỉ chạy các job đã có của dự án; lượt model trong CI là smoke kỹ thuật riêng.

```sh
python -m pytest -q tests/test_storyboard_brief.py tests/test_storyboard_editions.py tests/test_storyboard_distribution.py tests/test_video_storyboard.py
```

Có thể đặt `AMC_BRIEF_EVIDENCE`, `AMC_STORYBOARD_EDITION_EVIDENCE`, `AMC_CONNECTED_EVIDENCE` và `AMC_STORYBOARD_EVIDENCE` đến các thư mục đầu ra mới để lưu từng bộ. Với SQLite, các ca cần mailbox thật sẽ được bỏ qua. Trước khi quay lui, dừng nhận nhiệm vụ @2 và hoàn tất các lease bằng runtime tương thích; giữ registry, ledger, journal, receipt và bản đã QA để kiểm toán.

Reviewer có thể bắt đầu bằng ba câu hỏi. Một yêu cầu lạ đã được để mở đúng lúc chưa? Có truy từ CRM về đúng file preview và QA khi hai khách cùng một agency dùng cùng một mô tả sản phẩm không? Người dựng thực tế cần sửa bao nhiêu phút trước khi nhận việc? Hai câu đầu có ca kỹ thuật và nguồn để đối chiếu. Câu cuối cần người hành nghề. Quyết định roadmap tiếp theo dựa trên lỗi nghiệp vụ và công chỉnh sửa thực tế, giữ V1 ở 49 module, 37 vai trò, 24 workflow mẹ. Production và Commercial GA vẫn **NO-GO**.
