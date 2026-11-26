# Nghiệm thu bản ghép quản trị và sản phẩm

Main được đối chiếu ở `380be3eb70a41424c6d45318b0b1890fa950970a`. PR #53 tiếp tục mở tại `56a120cac4bb3f77a4e1fc6fe93298cc838121ea`. PR #55 có bản sửa sản phẩm ở `1202b4321ecd452d3b4bb2373a65b780c63e24f9`. PR #56 dùng head `5b5e3ae625dddecf98fddfd063b0cb3855eb6fb2`, GitHub ghép thử với main thành `017dc485c1e9660d2d7b33289d839ae0c4da6281`, tree cả hai là `46fc7eaffa03c78f738d64a35a1e5dc13a794072`. [Các finding và bàn giao 15 mục](https://github.com/datnv41001/ai-company/blob/5b5e3ae625dddecf98fddfd063b0cb3855eb6fb2/docs/evaluation/department-review/ROUND-53-55.md)

| Nhánh | CI push | CI PR trên head và bản ghép | JUnit bản ghép |
|---|---|---|---|
| #55 | [3 job](https://github.com/datnv41001/ai-company/actions/runs/45767448820) | [6 job](https://github.com/datnv41001/ai-company/actions/runs/45767454580) | [602 đạt, 2 skip](https://github.com/datnv41001/ai-company/actions/runs/45767454580/artifacts/15093596417) |
| #56 | [3 job](https://github.com/datnv41001/ai-company/actions/runs/45767448748) | [6 job](https://github.com/datnv41001/ai-company/actions/runs/45767455106) | [602 đạt, 2 skip](https://github.com/datnv41001/ai-company/actions/runs/45767455106/artifacts/15093053039) |

Các số đếm trên thuộc mỗi bản checkout. CI đã kiểm 22 đường nâng cấp có dữ liệu v1–v22 tới v26, lặp migration và so khớp 34 bảng khi khôi phục độc lập. Hai biến thể SQLite bỏ qua kiểm tra đặc thù PostgreSQL có hai ca PostgreSQL tương ứng đạt. Job matched-model tùy chọn giới hạn theo tên nhánh qualification trong workflow. [Metadata, SHA, parent, từng job và lý do skip](ci.json)

Đường nâng bổ sung cùng schema v26 dùng đúng publisher tiền nhiệm #55. Trên bản ghép, 48 hàng journal giữ nguyên sau hai lượt publisher, và API cũ đọc lại biên nhận trên bản pg_restore. Workflow nghiên cứu riêng [Matched department comparison](https://github.com/datnv41001/ai-company/actions/runs/45767455102) bỏ qua theo điều kiện nhánh research/full-workflow-qualification. Các job Workforce bắt buộc chạy trên cả head lẫn integration. [Runbook](https://github.com/datnv41001/ai-company/blob/5b5e3ae625dddecf98fddfd063b0cb3855eb6fb2/docs/evaluation/business-intake/CONSULTATION.md)

Trên tree cuối, 26 kiểm thử Windows với PostgreSQL cục bộ/fixture liên quan đạt. CI bản ghép có biên nhận tư vấn thực thi trên SQLite và PostgreSQL, sáu ảnh Sales ở 390/820/1280 px và hai theme. [Danh sách Windows](windows-native.json) · [Biên nhận và hash](consultation-ci.json) · [File intake từ CI](https://github.com/datnv41001/ai-company/actions/runs/45767455106/artifacts/15092464883) · [Chromium từ CI](https://github.com/datnv41001/ai-company/actions/runs/45767455106/artifacts/15092174343)

Phiên tiếp quản mới trên đúng head #53 tự chọn lệnh và test. Bản xuất sạch đạt 12/12 test SQLite, API health 200. [Lệnh, log, kết quả và giới hạn](https://github.com/datnv41001/ai-company/blob/5b5e3ae625dddecf98fddfd063b0cb3855eb6fb2/docs/evaluation/knowledge-handoff/FINAL-53.md)

Phí provider mới bằng 0. Số người hành nghề tham gia là 0. Production và Commercial GA vẫn **NO-GO**.
