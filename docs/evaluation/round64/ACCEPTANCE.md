# Hồ sơ đối chiếu 18 điều kiện

Bảng này dẫn tới phép thử và dữ liệu cần mở. Kết quả thực tế của từng lần chạy nằm trong JUnit ở gói bằng chứng của draft PR.

| Điều kiện | Kiểm và biên nhận |
| --- | --- |
| 1–2. Claim sai/đúng với ID nguồn thật | `BASELINE-63.json` ghi nhận lỗi ở worker và hai lần QA chặn. `lineage/baseline.json` chạy lại trên candidate. `lineage/lineage.json` giữ đề xuất và câu sửa trong một commission. |
| 3–4. Paraphrase, chủ thể và giới hạn mẫu | Đối chiếu paraphrase với phán quyết có mandate và span của đúng trường. Trích sai chứa cùng source handle hoặc chọn nguồn của một nhận định khác phải giữ việc. Năng lực hiểu ngữ nghĩa của người duyệt được giả lập bằng quyết định có chủ đích. |
| 5–6. Đổi người quyết định hoặc quan sát | Hồ sơ `negative-cases.json` và `placement.json` kiểm buyer ngoài brief. Trong `lineage.json`, sửa tình huống quan sát và duyệt lại tạo phương án nội dung khác cho cùng sản phẩm. |
| 7–8. Hai nguồn dẫn tới hướng khác nhau hoặc thiếu nguồn | Reviewer có thể ghi nhận mâu thuẫn/chưa đủ căn cứ. Hệ thống giữ việc, lưu lý do, người xử lý và receipt. Việc nhận diện hai nguồn trái chiều cần phán đoán chuyên môn. |
| 9. Kênh hợp lệ, tài sản cũ sai placement | `placement.json` đối chiếu từ chối asset web với lệnh soạn mới cho thẻ tại quầy trên cùng commission. |
| 10–13. Thu hồi và thay đổi sau QA | Rút nguồn, rút mandate, hạ quyền, sửa Research, sửa Strategy. Kiểm lại từ phiên người nhận và người ký; các lệnh cũ hết hiệu lực. Kiểm điều kiện kênh theo placement trên manifest và revision. |
| 14. Hai client cùng agency | `client-scope.json` ghi bốn yêu cầu ở hai scope dù campaign cùng tên. Luồng in-house dương và phép thử client âm sử dụng workspace riêng. |
| 15. Stale, replay và mất hồi đáp | `authority.json` ghi biên nhận của lần gửi lại, từ chối sửa khác trên cùng revision và HTTP 412 khi revision đổi. Chromium kiểm lỗi và giữ dữ liệu người dùng vừa nhập. |
| 16–17. Quyền thực thi và dữ kiện tới Content | Đối chiếu số bản ghi trước/sau ở `lineage.json`, bản trả riêng cho Content và câu chữ sản phẩm. Kiểm trường downstream đã lọc; bản nháp cần QA riêng trước khi phát hành. |
| 18. Lịch sử và release | Suite API đầy đủ gồm kiểm fingerprint, release và replay lịch sử. Đối chiếu tree head/trial, lịch sử registry và JUnit trên cả ba checkout. |

## Những lần chạy chưa đạt trong quá trình phát triển

- Một probe PostgreSQL dùng vị trí F1/F3 như thể đó là ID nguồn toàn cục. Khi manifest mới gán handle khác, ca kiểm lấy nhầm dữ kiện. Fixture cuối tra theo tuyên bố nguồn và đối chiếu span, revision, locator của đúng commission. Phản chứng đổi nhầm nguồn vẫn là một ca bắt buộc.
- Chromium từng hoàn thành các assertion và ghi ảnh nhưng thất bại ở bước dừng server thử nghiệm. Đã sửa khâu đóng kết nối và chạy lại từ đầu. Chỉ ảnh và JUnit thuộc cùng lượt thành công cuối được dùng để nghiệm thu.
- Trong lúc hoàn thiện backend, migration trên DB thử nghiệm đã từ chối fingerprint trung gian. Khóa runtime cuối giữ lịch sử adapter và chỉ bổ sung các môi trường đã đối chiếu.
- Các lần kiểm PostgreSQL dùng worker trả lời tất định để điều khiển từng lỗi. Token ghi ở journal fixture là giá trị mô phỏng. Số liệu model thật cần đọc từ artifact Qwen của đúng job, tách khỏi lineage trên.
