# Thẩm định nghiệp vụ Research → Strategy

**Kết luận của người đánh giá AI.** Cả 5 cảnh báo Strategy đều có căn cứ trong bản ghi thử nghiệm. Có 4 điểm cần sửa vì hai cảnh báo cùng chỉ vào trường `unit`. Đội cửa hàng chưa thể tính KPI hay xác định mức cải thiện từ bản nháp này.

Brief nhắm đến “University students”, đưa ra lời mời “See the notebook in store” và yêu cầu “Research the supplied notebook evidence and propose a measurable strategy for students.” Thẻ sản phẩm chỉ ghi “A5 notebook with 80 lined pages”. Báo cáo dùng dữ liệu tổng hợp trong fixture và các đoạn bằng chứng của lần chạy `6e2bf58c-f05f-40ed-a1c7-2b522d4a34d1`. Không suy luận số liệu kinh doanh thực tế.

| Cảnh báo Strategy | Bằng chứng nguyên văn | Đánh giá, tác động và cách sửa |
|---|---|---|
| `verify_unit` | “Measurable KPI” | Xác nhận. Người đọc chưa biết một giá trị như 5 mang đơn vị gì. Ghi đơn vị rõ ràng, ví dụ % cho tỷ lệ sinh viên nhận lời xem sổ. |
| `verify_measurement_method` | “measurable KPI” | Xác nhận. Hai cửa hàng có thể đếm lượt mời và lượt xem theo cách khác nhau. Chốt sự kiện, nguồn ghi nhận, khóa đếm và quy tắc ghép sự kiện trước khi thu thập. |
| `verify_measurement_window` | “time window” | Xác nhận. Người lập báo cáo có thể chọn những ngày khác nhau và cho kết quả khác nhau. Ghi ngày đầu, ngày cuối, múi giờ và thời điểm khóa số liệu. |
| `verify_ratio_unit` | “Measurable KPI” | Xác nhận. Một tỷ số 0,20 có thể được hiển thị là 20% khi nhân 100. Cùng lỗi trường đơn vị với dòng đầu, nhưng cần kiểm tra thêm công thức có khớp thang hiển thị và tử số có thuộc mẫu số. |
| `baseline_evidence` | “The brand A's A5 notebook for A” | Xác nhận. Mô tả sản phẩm không chứa số đo, kỳ gốc hay nguồn đo. Ghi “chưa đo” cho đường cơ sở. Chỉ tính chênh lệch sau khi có tử số và mẫu số của một kỳ so sánh cùng cách đo. |

**Ảnh hưởng của Research.** Trường `observed_fact` viết “The brand A's A5 notebook for A is not suitable for students.” Thẻ sản phẩm chỉ chứng minh khổ A5 và 80 trang có dòng kẻ. Brief cho biết nhóm dự kiến tiếp cận, còn mức độ phù hợp với nhu cầu ghi chép vẫn là câu hỏi mở. Bỏ nhận định về độ phù hợp khỏi phần quan sát. Có thể hỏi sinh viên sau khi xem sổ về khổ giấy và số trang trước khi dùng các thuộc tính này làm thông điệp định vị.

## Một KPI có thể giao cho cửa hàng đo thử

**Giả định minh họa.** Đo tỷ lệ sinh viên được mời tại cửa hàng và thực sự xem mẫu sổ A5 trong cùng lượt ghé. Chỉ số này trả lời liệu người đã được mời có xem sản phẩm. Sự kiện, nguồn và ngày dưới đây đều là đề xuất.

- **Công thức và đơn vị.** Mẫu số là số mã lượt ghé duy nhất có sự kiện `a5_invited` của khách tự xác nhận là sinh viên. Tử số là số mã trong mẫu số có thêm sự kiện `a5_viewed` sau lời mời, khi nhân viên trực tiếp quan sát khách mở sổ mẫu. KPI = 100 × tử số / mẫu số, đơn vị %. Đếm mỗi mã một lần cho mỗi tập. Khi mẫu số bằng 0, ghi “không tính được”.
- **Kỳ đo.** Gán mỗi lượt vào ngày nhận lời mời tại cửa hàng thử nghiệm. Đo từ ngày 01/12 đến hết ngày 07/12/2026 theo giờ Bangkok (UTC+7). Chốt sau khi đóng cửa ngày 07/12 và các lượt ghé hôm đó kết thúc.
- **Nguồn mẫu.** Nhân viên ghi hai sự kiện vào cùng nhật ký trình diễn A5. Mỗi dòng gồm mã cửa hàng, mã lượt ghé ẩn danh, thời điểm, cờ sinh viên và tên sự kiện. Dùng cặp mã cửa hàng và mã lượt ghé để ghép lời mời với lượt xem.
- **Đường cơ sở và mục tiêu.** Nếu có nhật ký đủ trường, tính cùng công thức cho ngày 24–30/11/2026 tại cùng cửa hàng, với cùng điều kiện mời. Hiện trạng trong hồ sơ là “chưa đo”. Có thể đặt mục tiêu sau khi thu kỳ gốc và duyệt trước kỳ thử. Khi so sánh hai tỷ lệ %, báo cáo chênh lệch bằng điểm phần trăm.

**Nguồn đối chiếu.** Bản QA trên head đã duyệt có digest Strategy `f14be3bf0884a845052e35beed6c55ba8f8fd8a2913012c1293c5d39c9bb42a1`. Digest của Research tiền nhiệm là `bfc35fafd5d53a2418d487dd1b49f839db90dadef4bfa8fcc5fceac58d812c9f`. Nguồn brief và thẻ sản phẩm đến từ `tests/test_workforce.py::DATA`, `tests/test_registry.py::registry_brief` và `tests/test_research_strategy.py::start_research`. [Artifact của head, tệp research-strategy-measurements.json](https://github.com/datnv41001/ai-company/actions/runs/45339595268/artifacts/14895817750).

**Lần sinh lại trên main.** Cùng Git tree, Qwen sinh một đề xuất khác với digest `6ab88d781cb270785b8fc84d2132e44a5c84aca88f8a8160b4430dabc2cbd25c`. Trong lần này QA ghi ba finding gồm `verify_unit`, `verify_ratio_unit` và `baseline_evidence`. Việc số lượng cảnh báo giảm từ năm xuống ba qua hai đầu ra khác nhau chưa chứng minh chất lượng được cải thiện. [Artifact của merge](https://github.com/datnv41001/ai-company/actions/runs/45342029520/artifacts/14896013846).
