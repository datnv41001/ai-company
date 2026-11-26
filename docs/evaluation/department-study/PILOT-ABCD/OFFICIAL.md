# Cấp và chấm pilot bốn nhánh

Người điều phối cấp bộ mới cho hai brief tổng hợp được phép sử dụng, một RFQ và một dịch vụ đặt lịch. Marketing thực hiện công việc, reviewer chấm bản đầu và bản giao, Sales hoặc Service quyết định có sử dụng bản giao hay không. Nhánh D có thêm người QA sản xuất độc lập. Các alias, khóa phân công, bài chấm và nguyên văn tài sản công khai của vòng trước là fixture minh họa.

## 1. Chuẩn bị ngoài Git

Dùng Python 3.12. Chọn một ổ/thư mục riêng của người điều phối, kiểm soát tài khoản truy cập, bản sao và thời hạn lưu. Lưu danh tính và consent thực tế riêng, cấp **một** mã giả chữ thường cho mỗi người. Chỉ dùng mã đó trong study. Một mã chỉ được làm một loại vai trò xuyên suốt study. Xác minh danh tính thuộc về những người độc lập qua quy trình của đơn vị tổ chức.

Tạo `materials/rfq/` và `materials/appointment/`, mỗi thư mục có `brief.md`, `control.md` và `ai.md`. Hai bản ứng viên là văn bản UTF-8 ẩn nhãn đã khóa theo brief mới, có nguồn hợp lệ và chi phí tạo bản đầu có thể đối soát. Giữ chứng từ nguồn với người điều phối. Nhánh A bắt đầu từ trắng, B nhận control, C và D nhận cùng byte AI cho mỗi brief. Quy trình không gọi model. Người tổ chức cần ghi nhận nếu đã cho một người xem brief/ứng viên trước, phân công A trước khi lộ ứng viên hoặc bố trí nhân sự riêng.

Lập `materials/roster.json`. Hai khóa ngoài là `rfq` và `appointment`. Trong mỗi khóa, tạo **đủ bốn** mục `manual`, `control`, `ai_assisted`, `ai_plus_independent_qa`. Mỗi mục ánh xạ `marketer`, `independent_reviewer`, `sales_or_owner` tới ba mã người riêng. D bổ sung mã thứ tư ở `production_qa`. Lệnh từ gốc repo dưới đây dùng các đường dẫn minh họa. Thay bằng đường dẫn thực trên máy được ủy quyền.

```sh
python tests/evaluation/department/official_pilot.py issue /private/study/vault /private/study/materials
```

Lưu **digest thiết kế in ra** vào bản ghi do một người thứ hai kiểm soát trước khi giao việc. Mỗi lệnh sau nhận digest đó qua `--lock`. Kho khóa mới từ chối ghi đè, nằm ngoài Git, dùng thư mục mode 0700 trên POSIX và ACL dành cho người tạo cùng SYSTEM trên Windows. Giữ tệp `design.json` trong vault. Nó khóa tám work order, phân công, rubric, brief, byte đầu vào và mã chấm riêng của từng stage. Người điều phối giao riêng `<vault>/<work-id>/producer.zip` tới đúng một người làm Marketing. Chỉ ZIP này được dùng ở khâu sản xuất. Các tập kết xuất cho người chấm nằm trong thư mục riêng giới hạn đúng người nhận.

## 2. Ghi lại đúng bản trước khi sửa

Điều phối viên là người ghi tuần tự vào vault. Mỗi lần `capture` đóng một phiên bản bất biến qua CLI và trả `card, revision, sha256`. Người gửi và người nhận giữ bản độc lập của receipt và phiếu trả về. Dùng time log của pilot để tách riêng thời gian chờ chấm, sửa, sản xuất và QA.

```sh
python tests/evaluation/department/official_pilot.py capture /private/study/vault --lock LOCK WORK initial /private/work/first.md
python tests/evaluation/department/official_pilot.py packet /private/study/vault --lock LOCK WORK initial /private/reviewer/CARD.zip
python tests/evaluation/department/official_pilot.py grade /private/study/vault --lock LOCK WORK /private/returns/first-grade.json
```

Thay `WORK` bằng work order của người điều phối và `CARD` bằng giá trị `card` của phiên bản vừa chụp. Chỉ phát ZIP đúng người chấm. Nó có `artifact.md`, `brief.md`, rubric, reference và mẫu phiếu của đúng vai trò. Reviewer điền actor code, consent, nhận xét, rubric có dẫn chứng, `accepted` và `unblinded` trên **chính bản đầu**, gửi riêng cho người điều phối. Bản đầu dùng revision 1. Với B/C/D, byte phải khớp draft đã khóa khi cấp; với A phải giữ bản viết tay đầu tiên. Lệnh grade chỉ cho chốt một lần. Editor bắt đầu sửa sau khi phiếu này đã chốt.

Chụp bản chuẩn bị giao ở stage `edited` (revision 2) nếu có biên tập hoặc trong mọi ca D. Dùng lệnh `packet` như trên với `--role marketer`; phiếu ghi `decision: submitted`, lý do và đúng reference. Ở D phát gói stage này riêng cho `production_qa`. Chụp bản cuối tại `delivered` (revision 3). Một bản được giữ nguyên vẫn có reference riêng. Ở D, phát thêm packet `delivered --role production_qa` trước khi chuyển ra người nhận. Người QA trả input reference của revision 2, output reference của revision 3, `decision: approved` khi đủ điều kiện, actor code, consent, lý do phát hiện/sửa hoặc lý do giữ nguyên, giây QA và chi phí có chứng từ. Hoãn bàn giao nếu người QA trả về. Ghi công các lần thử. Stage dùng một lần, nên nếu cần sửa sau khi đã khóa byte cuối, lưu nguyên lần đó, ghi việc chưa hoàn thành và cấp lượt mới khi được phép.

Ở khâu cuối dùng `packet ... WORK delivered /private/<recipient>/CARD.zip --role ROLE` cho từng người trong ba vai trò đã khóa. Mỗi người chỉ nhận phiếu vai trò của mình, đánh giá đúng bản cuối. Điền đầy đủ rubric và dẫn chứng với reviewer, quyết định sử dụng và tính hữu ích với Sales/Service, thời gian và chi phí theo vai trò. Phí bằng 0 phải có căn cứ. Cost chưa đo để null.

## 3. Đối soát thiết kế và chi phí

Sao chép `vault/outcomes-template.json` vào một tệp riêng. Giữ đủ cả tám khóa. Từng mục có một trong bốn trạng thái:

- `completed` có `observations` là ba phiếu cuối nguyên gốc, `edited_decision` nếu có revision 2 và `production_qa` cho D. Một bản đã bị Sales từ chối vẫn ở trạng thái này, với `business_accepted=false`.
- `failed` có lý do và một khoản `cost` riêng cho lần sản xuất thất bại trước bàn giao. Dùng các trường `labor_vnd,model_vnd,compute_vnd,tools_vnd,other_vnd,receipt_refs,includes_failed_attempts`. Nhân công tính cả QA có phát sinh. Con số thiếu được giữ là chưa biết.
- `pending` ghi lý do cùng những receipt đã có cho công việc còn dang dở. Nếu dừng ở khâu QA sau khi chụp bản dự kiến giao, giữ nguyên các phiên bản và ghi trạng thái thực tế, kể cả khi chưa có quyết định của Sales.
- `unblinded` ghi lý do khi người nhận đã biết nhánh. Lưu bản cũ vào lịch sử, không thay thế lặng lẽ một quan sát bất lợi. Một người chưa từng xem dữ liệu có thể được tuyển cho vòng mới với thiết kế và alias mới.

```sh
python tests/evaluation/department/official_pilot.py report /private/study/vault --lock LOCK /private/returns/outcomes.json --out /private/study/vault/report-01.json
```

Phép tính theo nhánh gồm chi phí của mọi việc được giao, kể cả việc bị từ chối và thất bại, chia cho số việc được doanh nghiệp chấp nhận. Khi còn ca chưa xác minh, thiếu chi phí hoặc mẫu số bằng 0, kết quả là null. Con số first-pass dựa trên phiếu gắn với revision 1. Bản báo cáo chi tiết chỉ ghi vào file mới trong vault. Giới hạn người được xem số liệu từng nhánh cho đến khi đã nhận đủ phiếu.

## 4. Phát hiện lộ nhãn, phục hồi và giới hạn

Thiết kế mới `official-department-pilot/2` cấp phiếu theo đúng vai trò. Marketer và QA sản xuất nhánh D khai `treatment_exposure=within_assignment` khi chỉ biết phương pháp mình được giao, kể cả khi tự tạo hoặc trực tiếp kiểm bản giao. Khai `outside_assignment` khi thấy khóa phân nhánh, biết phân công khác ngoài phạm vi hoặc làm lộ nhãn cho người phải chấm mù. Reviewer độc lập và Sales/Service vẫn khai `unblinded` trên phiếu của họ. Khai báo của QA sản xuất nằm trên quyết định liên kết hai revision. Thiếu khai báo thì chưa thể tổng hợp ca hoàn tất. Sự cố ở bất kỳ vai trò nào loại quyết định khỏi kết quả chấm và giữ lại ca trong số đã phân công.

Vault khóa theo thiết kế v1 tiếp tục cấp và đọc mẫu v1. Giữ nguyên cờ `unblinded` mà người tham gia đã nộp và giữ biên nhận cũ. Dùng thiết kế v2 cho vòng mới.

Trước khi phát, kiểm tra cả nội dung, nguồn hoặc liên kết, mẫu từ vựng quen thuộc, prompt còn sót và tên tệp. CLI loại metadata ngoài văn bản, từ chối một số chuỗi lộ nhánh, byte fixture công khai và tên ZIP có nhãn do người điều phối tự đặt. Kiểm tra thủ công nguồn sở hữu, PII và bí mật trước khi nhận file. Hỏi người chấm riêng về tiếp xúc trước và khả năng nhận dạng, lưu suy đoán và căn cứ **trước** khi giải mã. Khi người được phân công chấm mù nhận ra nhánh, họ khai `unblinded=true`. Người điều phối ghi sự cố ngay khi phát hiện bằng lệnh dưới đây.

```sh
python tests/evaluation/department/official_pilot.py incident /private/study/vault --lock LOCK WORK "Nguoi cham da thay bang anh xa; phieu da duoc cach ly"
```

C và D có cùng byte bản đầu theo thiết kế. Mã chấm mới và tên file sạch vẫn có thể để một reviewer nhận ra cặp qua câu chữ hoặc digest. Khi xếp lịch, giao hai gói trong cùng brief cho hai người chấm first-pass khác nhau, chỉ gửi từng gói riêng. Nếu một reviewer đã nhìn thấy cả hai và nhận ra bản lặp, ghi việc nhận dạng cùng mức chắc chắn trước khi mở khóa, đánh dấu incident ở **cả hai work order** và loại cặp này khỏi so sánh chấm mù. Giữ đủ hồ sơ và chi phí của cả hai trong báo cáo. Ghi nhận tương tự nếu người nhận bản cuối đã thấy bảng phân công hoặc bản đầu có thể nhận dạng.

Tạm dừng phát gói liên quan, ghi rõ ai đã thấy loại thông tin nào bằng mã giả, bảo toàn hồ sơ và tách ca bị lộ khỏi kết luận. Sự cố đã ghi vẫn triệt tiêu kết quả dù sau đó phiếu khai chưa lộ. Byte và mã tham chiếu không chứng minh một người thật đã đọc nội dung, ký nhận, sử dụng một danh tính duy nhất hay tác giả đã nộp ngay lần viết đầu. Custodian có quyền hệ điều hành vẫn có thể sửa đồng thời nội dung cùng receipt. Digest khóa do người thứ hai giữ phát hiện thay thiết kế. Thu nhận consent và phiếu qua kênh xác thực riêng, đối chiếu với bản receipt lưu độc lập ở từng mốc; hash không phải chữ ký cá nhân.

Sao lưu vault **và** receipt ngoài vault vào kho riêng có kiểm soát. Khi khôi phục, dùng bản sao đọc thử, digest đã escrow, `report` và receipt gốc để xác minh đủ tám việc trước khi cho tiếp tục ghi. Nếu không xác minh được, giữ nguyên hồ sơ cũ như bằng chứng không hoàn chỉnh. Công cụ và file riêng có thể ngừng sử dụng độc lập với ứng dụng. Quy trình này chỉ được kiểm thử bằng dữ liệu tổng hợp. Số practitioner và số chấp nhận thật ở đợt bàn giao hiện tại đều bằng 0.

[Tái chạy các ca âm và chi phí](../../../../tests/test_department_official_pilot.py) · [Hướng dẫn lịch sử và fixture](README.md)


## Biên bản diễn tập tổng hợp ngày 26/11/2026

Trên source đã review `c5c6329599a66fd2dc6011428e7ab8eed9208df4`, người kiểm định chạy scorer gốc với một work order control. Ba phiếu cùng trỏ byte bản giao, chỉ có `delivered.artifact`, không lưu bản đầu. Kết quả trả `first_pass_accepted=true` và mẫu cấp phát bằng 1. Điều đó tái hiện đúng khoảng trống về lineage và thiết kế.

Với CLI chính thức trên Windows/Python 3.12.14, diễn tập `issue` rồi `report` trên hai brief tổng hợp mới, ngoài checkout, cho 8 việc đã cấp, 8 đang chờ, 0 accepted và 0 nhánh có ước tính chi phí trên bản được chấp nhận. Không lưu khóa diễn tập trong repository. Bộ hồi quy gồm bốn ca tích hợp mới và năm ca tương thích cũ; 9/9 đạt. Chạy tại gốc repo:

```sh
python -m pytest -q tests/test_department_official_pilot.py tests/test_department_four_arm.py tests/test_department_pilot.py
```

Người review có thể thay byte bản đầu sau khi giữ lại receipt, đổi revision trên phiếu đầu sang revision bản giao, xóa một work order ở design lẫn ở bảng kết quả, gỡ phiếu QA của D, hoặc bỏ trống chi phí của lần thất bại. Các regression kiểm từng trường hợp ở đúng khâu nhận, chấm hoặc đối soát. Đây là kiểm định công cụ, chưa đo giá trị Marketing từ người sử dụng.

## Mời người hành nghề

Dùng [thư mời riêng và hướng dẫn consent](INVITATION.md). Người điều phối điền thời gian, thù lao, nơi lưu, hạn xóa và đầu mối rút quyền trước khi mời. Tách thư mời khỏi khóa phân bổ và tài liệu chấm mù. Trạng thái vòng chuẩn bị là chưa gửi thư, chưa tuyển và chưa cấp một quyết định nghiệm thu thật.

## Điều phối và quyết định sau lời mời

1. Xác nhận người tham gia có kinh nghiệm phù hợp, đủ consent, điều kiện thù lao đã duyệt và khả năng giữ riêng tài liệu. Tạo một alias riêng tư, gán một loại vai trò xuyên suốt. Người đánh giá độc lập và người nhận cuối nhận gói ẩn treatment. Nếu một người đã biết brief phải ghi nhận và xử lý thứ tự hoặc phân công theo runbook. Tuyển theo số vai trò có thật. Khi thiếu người, giữ việc ở trạng thái chờ.
2. Giữ bản đồng ý, điều kiện sử dụng, chi phí và liên hệ trong kho riêng. Không đưa thư đã điền vào Git. Tạo brief và ứng viên mới được phép dùng, khóa tám work order, giữ digest ở người thứ hai. Chỉ gửi gói riêng theo vai trò. [Quy trình issue/capture/grade/report v2](OFFICIAL.md)
3. Chấm bản đầu trước biên tập. Ghi đúng revision, căn cứ claim, người nhận, độ rõ của hành động và lý do trả lại. Ghi từng lần sửa, lỗi nghiêm trọng, giờ thực làm, thời gian chờ, phí dịch vụ, công QA. Sales/Service quyết định có sử dụng bản cuối ở revision nào. Từ chối, hết hạn, lộ nhãn và việc dang dở vẫn vào báo cáo.
4. Báo cáo từng nhánh A/B/C/D, tách RFQ và lịch hẹn. Đếm việc được ủy quyền chấp nhận, tỷ lệ bản đầu đạt, chất lượng theo rubric và chi phí đầy đủ trên việc được dùng. Mẫu số bằng 0 hoặc thiếu chi phí thì ghi **chưa xác định**. Một phiếu của AI chỉ là bằng chứng kỹ thuật. [Định nghĩa đơn vị giá trị](../../../PRODUCT_MISSION.md)

## Sau #58 · bố trí người nhận cho công việc storyboard

Giữ nguyên bốn nhánh đã khóa ở v2. Điều phối viên chỉ dùng lịch, tên và mức thù lao riêng đã được Product Owner cho phép. Chuẩn bị một editor nhận tờ dựng, một người Sales/Service đối chiếu hành động khách, một người duyệt brand/claim có thẩm quyền; chỉ gán người thật sau khi họ chấp thuận. Lưu công sửa và lý do trả lại. Nếu dùng output worker mới làm treatment, ghi rõ adapter và số lượt inference; khóa treatment và tiêu chí trước khi phát phiếu mới. Giữ bản do người làm và bản Codex biên tập ở điều kiện đã đăng ký. Thư mời vẫn là bản nháp. Không tái dùng alias, brief công khai hoặc phiếu đã chấm.

Người đọc phải nói lại giá/đơn vị, quyền dùng hình, trạng thái sau submit và chọn một cảnh có thể tự dựng. Thu riêng độ đầy đủ, số claim có nguồn, độ chính xác nghiệp vụ, phút sửa và lần xin thêm dữ kiện. Lưu bản đầu, bản sau sửa, quyết định người nhận và chi phí. Khi chưa có consent, số người tham gia và Business-accepted Marketing Work Units đều là 0; thời gian kỹ thuật không đại diện chi phí nhân sự. [Phạm vi đo](../../workforce-video/MEASUREMENT.md)
