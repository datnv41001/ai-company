# Làm rõ đơn vị bán khi brief Marketing bị chặn

## Quy trình nghiệp vụ

1. Mở brief nháp trong Hồ sơ doanh nghiệp, chọn **Chuẩn bị Marketing từ brief này**, chọn nhiệm vụ, hướng dẫn thương hiệu, thị trường, KPI và các nhận định. Nhấn **Kiểm tra mức sẵn sàng**.
2. Với thẻ giá có đơn vị “dịch vụ”, AMC hiện phiên bản thẻ, giá, cơ sở tính, số lượng, bậc giá, lượng tối thiểu, thuế và điều kiện. Đối chiếu chứng từ. Chủ sở hữu hoặc quản trị viên chọn đơn vị đã ghi trong chứng từ, nhập tên, vị trí, trích đoạn và xác nhận mọi điều khoản vẫn áp dụng nguyên vẹn. Khi cần quy đổi giá, thay lượng, hoặc chứng từ chưa đủ rõ, quay lại hồ sơ thương mại để bổ sung căn cứ.
3. **Lưu đề xuất điều chỉnh** tạo bốn bản nháp trong cùng giao dịch. Các bản ghi gồm chào giá, nguồn xác nhận, liên kết bằng chứng và nhận định. Khi chính sách yêu cầu người duyệt nghiệp vụ độc lập, người đó đăng nhập, chọn đúng thương hiệu, mở **Nguồn và nhận định → Duyệt đơn vị bán**, đọc điều khoản và nguồn, ghi lý do rồi xác nhận. Danh sách này chỉ hiển thị nội dung thương mại cần duyệt. Với thẻ thuộc loại được phép tự duyệt, người có quyền có thể hoàn tất ngay trong brief.
4. Tác giả mở lại brief, chọn **Tiếp tục sau khi sửa đơn vị bán**, sau đó chọn nhiệm vụ có nhãn **dùng giá đã duyệt**. AMC nạp lại lựa chọn từ máy chủ, thay đúng mã nhận định vừa duyệt và kiểm tra lại toàn bộ căn cứ. Bản giao mới dùng manifest mới. Phiên bản cũ cùng các bằng chứng và bản giao đã ghim tiếp tục truy xuất được trong lịch sử.

## Giao nhiệm vụ có ý định cụ thể

Mẫu nội bộ và mẫu gửi khách tạo hợp đồng `amc.task-intent/2`. Người giao chọn hành động mua, cách diễn đạt và, khi cần, loại thông tin người mua gửi. Ví dụ, “gửi ảnh đầu kéo để báo phí” dùng `rfq` và `photo`. “Gửi lựa chọn mẫu thêu” dùng `select_sample` và `sample_choice`. Hành động, cách diễn đạt và loại thông tin được ghim với brief và chuyển vào đầu vào của vai trò Content/SEO dưới dạng giá trị đã liệt kê trước. Bảng thuật ngữ Việt–Anh nằm trong `app/c3_actions.py`. Hợp đồng v1 và các nhiệm vụ đã chạy vẫn dùng cấu trúc đã lưu. Bản v2 cần WF-03@3 hoặc WF-13@6.

## Chạy lại trên máy mới

Từ checkout đã cài dependency thử nghiệm của AMC, chạy các lệnh sau.

```sh
python -m pytest -q tests/test_c3_clarification.py tests/test_c3_task_intent.py
python -m playwright install chromium
python -m pytest -q tests/browser_c3_clarification.py -k sqlite
```

Biến `AMC_KNOWLEDGE_EVIDENCE` chọn thư mục ảnh và báo cáo Chromium. Bài kiểm tra dùng hai tài khoản thử nghiệm qua localhost và cơ sở dữ liệu dùng riêng. Nó thu ảnh của các bước làm rõ, duyệt và tiếp tục ở 1280, 820, 390 px cho cả hai giao diện sáng/tối. Chạy job CI PostgreSQL với pool thử nghiệm để kiểm tra phân quyền và giao dịch. Các đường API nằm dưới đường dẫn Marketing của từng thương hiệu, gồm `readiness`, `clarifications/propose`, `clarifications/approve`, `clarifications` và `manifests`.

Hai mươi ca cũ lấy từ `tests/evaluation/c3/holdout-v1.json`. Ngữ liệu đã được công bố nên các ca này đo hồi quy. Bảng `TASK_ACTIONS` trong `tests/evaluation/c3/recovery_fixture.py` đối chiếu từng ID với câu CTA gốc. Đơn vị sau sửa phải có trong trích đoạn bảng giá tổng hợp. Hàm `prepare_recovered(api, case, owner, base, client, brand, campaign, project=None)` tạo nhiệm vụ, thực hiện luồng duyệt và trả manifest thật kèm ID của chào giá trước/sau, nguồn, liên kết, nhận định và thời gian máy cho từng bước. Truyền `project` bằng tên dự án Compose khi hộp thư giả lập nằm trong container.

Đặt `AMC_CORRECTION_EVIDENCE` để xuất kết quả hồi quy từng ca. Các phép đo dừng tại lúc tạo manifest. Phần đánh giá mô hình cần receipt của từng invocation, bản sinh ra và bản sau biên tập. Thời gian của người dùng nghiệp vụ cần đo riêng.
