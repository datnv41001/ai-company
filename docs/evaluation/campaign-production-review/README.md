# Từ brief đến yêu cầu có thể xử lý

**Người nhận** là trưởng Marketing cần giao một gói có thể biên tập, kiểm claim, dựng video và đối soát được với kế hoạch. Hai hồ sơ dưới đây dùng doanh nghiệp và người mua tổng hợp. Các bản gửi Sales và lịch hẹn đều ở sandbox.

| Gói | Bộ campaign và 11 hạng mục bàn giao | Bản render Studio từ đúng brief | Tờ dựng video biên tập mới |
| --- | --- | --- | --- |
| Khe Gọn, bán khay linh kiện theo hộp | [Brief sản xuất và kế hoạch đo](index-tray.md) | [Ảnh dọc](index-tray/portrait.png) · [Landing HTML](index-tray/landing.html) · [Biên nhận](index-tray/evidence.json) | [Timeline, lời thoại và hai hook](index-tray/edit.json) · [Phụ đề A](index-tray/A.vtt) · [Phụ đề B](index-tray/B.vtt) |
| Luồng Rõ, dịch vụ khảo sát kho | [Brief sản xuất và kế hoạch đo](receipt-map.md) | [Ảnh dọc](receipt-map/portrait.png) · [Landing HTML](receipt-map/landing.html) · [Biên nhận](receipt-map/evidence.json) | [Timeline, lời thoại và hai hook](receipt-map/edit.json) · [Phụ đề A](receipt-map/A.vtt) · [Phụ đề B](receipt-map/B.vtt) |

## Căn cứ chọn hành trình

Đã đối chiếu toàn bộ [37 vai trò](../../../catalog/agent_roles.json), [24 workflow](../../../catalog/workflows.json) và [sổ năng lực](../DEPARTMENT-CAPABILITY-REGISTER.md). Chọn chuỗi từ nghiên cứu và kế hoạch → brief và bản copy → dựng ảnh/landing → QA theo revision → hành động trên form → báo cáo. Chọn hai [brief đã có từ nghiên cứu trước](../../../tests/evaluation/department/briefs-v1.json) để so trên cùng công việc. Các bộ phận social, media và video có vật liệu để nhận bàn giao nhưng còn thiếu bằng chứng đóng vòng với người hành nghề.

Tệp gốc [gói campaign #49–56](https://github.com/datnv41001/ai-company/raw/d320f7fe4d0588238a84320832780e31a0c7e8d4/docs/evaluation/downloads/AMC-rendered-campaigns.zip) có SHA-256 `cedc1b9cfe73a18d85b018b03e61bfb31e4bdd1d3eebf1bd45082e22f287604f`. Các mục `content/index-tray.json` và `content/receipt-map.json` giữ research, pillars, copy đa kênh, lịch theo ngày và media. Tuy nhiên master ở `rendered/rfq` trong chính ZIP mang tên Tấm gỗ tiêu âm Mộc, master ở `rendered/appointment` là Dịch vụ kiểm tra bơm Lam. Vì vậy cần chạy Studio cho đúng hai SKU ở vòng này. Bản [kênh 7B lịch sử](../department-study/DELIVERABLES.md) còn có câu cụt ở điều kiện đơn hàng và một lời hứa hiệu quả chưa có căn cứ. Đối chứng để chấm tờ dựng là **master và caption Studio trên hai brief hiện hành**, kèm media experiment có từ archive. Người đọc có thể đối chiếu cả ba thế hệ. Giá trị MOQ 1 hộp trong nội dung lịch sử Khe Gọn thuộc revision cũ.

## Chuỗi thực thi và giới hạn

Trong lần diễn tập, helper `sqlite_channel` dựng WorkforceRun ở trạng thái chờ QA bằng fixture. Từ đó phần tạo asset, kiểm gate, API nhận quyết định QA, render, tải và đối chiếu byte, thăm landing, gửi form có consent, đọc CRM/funnel đều đi qua mã AMC. Dùng cả hai ca của `tests/test_production_studios.py`. Người ký QA là tài khoản kiểm thử riêng, chưa có người duyệt doanh nghiệp. Ảnh là artwork hình học do renderer tạo. Tờ dựng mô tả cảnh cần sản xuất bằng đạo cụ có quyền. Phiếu edit, lời thoại, đề xuất kênh và kết luận chấm do Codex biên tập; các gói Studio nguyên bản có digest riêng. Hai track VTT có thể nhập vào timeline. Chưa quay hai phim đề xuất, mua media, upload chuyển đổi hoặc nhắn khách.

| Khâu | Bằng chứng theo role hoặc workflow | Điều kiện cho bước tiếp |
| --- | --- | --- |
| Research, chiến lược, planning | WF-03/WF-13 có lần gọi role lịch sử với receipt trong [nghiên cứu phòng ban](../department-study/RESULTS.md). Kế hoạch, lịch và dữ kiện thương mại đã có trong archive. | Research lead xác minh giả thuyết người mua, brand owner duyệt positioning; chưa có khảo sát của khách thật. |
| Content, SEO, creative | WF-06, WF-07, WF-08 và WF-13 có các thành phần composer/render. Đã tạo ảnh/landing/QA cho hai SKU. Tờ dựng mới cung cấp đầu vào cụ thể cho `ai-video-storyboard`, `ai-visual-design`, `ai-creative-director` và `ai-copywriter-content-strategist`. | Binding cần nhận đúng plan + nguồn có quyền, trả timecode, thoại, quyền footage và mã revision. Không có invocation mới của bốn vai trò này. |
| Media, CRO, CRM | WF-12 có proposal thử nghiệm trong pack. WF-13, WF-14 và WF-20 có form, receipt và hành trình tiếp nhận trên fixture. Trên appointment, CTA dẫn tới đề nghị lịch; Service phải xác nhận. | `ai-performance-media-planner` và `ai-attribution-experiment-analyst` cần kiểm mapping variant tới exposure và business event trước đo; `ai-crm-lifecycle-specialist` cần consent riêng cho nurture ngoài giao dịch. |
| Đối soát, cải tiến | WF-18 đọc số có mẫu số. WF-19 có quyết định sửa một hook kèm tiêu chí dừng và một danh sách điều chưa biết. | Đo trên người mua có consent, giữ outcome mất attribution trong báo cáo, chờ người có thẩm quyền duyệt quyền tác động ngoài. |

WF-09 chưa xuất bản trong vòng này. WF-10, WF-15, WF-24 và những vai trò khác ngoài chuỗi giữ trạng thái của [register](../DEPARTMENT-CAPABILITY-REGISTER.md). Có asset cho một khâu chưa đủ điều kiện nâng cấp toàn bộ workflow.

## Tái lập trên máy khác

Từ gốc checkout, với bộ phụ thuộc phát triển của repo, chấm lại hai gói đã lưu:

```sh
python tests/evaluation/department/production_edits.py verify docs/evaluation/campaign-production-review
```

Tạo track mới vào một thư mục trống sau khi tờ dựng thay đổi:

```sh
python tests/evaluation/department/production_edits.py captions docs/evaluation/campaign-production-review/index-tray/edit.json /tmp/amc-khegon-captions
```

Để kiểm giao dịch mới, đặt `AMC_PRODUCTION_EVIDENCE` và `AMC_INTAKE_EVIDENCE` vào hai thư mục trống ở máy dev, rồi chạy `python -m pytest -q tests/test_production_studios.py -k "index-tray or receipt-map"`. Trên PowerShell gán bằng `$env:AMC_PRODUCTION_EVIDENCE` và `$env:AMC_INTAKE_EVIDENCE`. [JUnit theo SHA của lượt chạy](journeys.xml) giữ thời gian và case. ID kế hoạch, digest theo revision và định danh tổng hợp có thể khác ở lần chạy mới. Quyết định doanh nghiệp, chi phí nhân sự và hiệu quả media chưa đo.

[So sánh chất lượng trước/sau](QUALITY.md) · [Bộ tiêu chí theo từng bộ phận](SKILLS.md)
