# Lần chạy Workforce với hai chiến dịch mới

Phòng lab Windows, PostgreSQL schema 25, registry đã kích hoạt theo campaign, llama.cpp chạy Qwen2.5 0.5B trên loopback. SHA-256 tệp model là `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`. Mã run, mã băm prompt, token, model output thô, journal, thời gian và mã băm của runtime nằm trong [sổ lần chạy](attempts.json). Checkout trong mỗi điều kiện là HEAD lúc thu trên working tree trước commit. Dùng fingerprint để đối chiếu mã thực thi và dùng CI để xác minh checkout Git độc lập.

| Đợt | Kết quả quan sát | Run | Lần gọi model | Token vào / ra | Giây worker |
|---|---|---:|---:|---:|---:|
| 01 | Registry từ chối trước inference vì source thay đổi sau khi khóa runtime | 0 | 0 | 0 / 0 | 0 |
| 02 | WF-03 cho “Tấm gỗ tiêu âm Mộc 12” có bản nháp. Studio chặn ký vì các trường của bản biên tập chưa đủ căn cứ | 1 | 3 | 2.186 / 314 | 22,17 |
| 03 | Tên được sửa trong brief thử mới, giữ SKU MOC-12. Script đọc sai trường báo cáo QA trên cả hai campaign | 2 | 6 | 3.648 / 596 | 35,78 |
| 04 | Ba tài liệu qua đủ luồng nội bộ. Sau đó thay đổi thứ tự ghi nhận yêu cầu và tạo các bản nháp theo kênh | 3 | 9 | 5.172 / 901 | 50,34 |
| 05 | Trên runtime ghi toàn bộ yêu cầu trước khi tạo nội dung, cả ba tài liệu qua quy trình | 3 | 9 | 5.174 / 915 | 95,27 |
| 06 | Liên kết kết quả với biên nhận xếp việc C3. Biên tập từng giá trị từ model, chạy gate trên từng thay đổi trước khi ký | 3 | 9 | 5.139 / 860 | 65,78 |
| Tổng cục bộ | 12 run đã tạo được tài liệu, 9 bản giao đã được tài khoản khách tổng hợp chấp thuận trong ba đợt cuối | 12 | 36 | 21.319 / 3.586 | 269,34 |

Phí provider ghi nhận bằng 0 USD. Đây là thời gian xử lý từng run, chưa đo chi phí điện/phần cứng hoặc thời gian biên tập của người thật. Đợt 02 dùng [bản kế hoạch với tên có số](original-numeric-proposal.json). Kết quả ký bị chặn của ca này được giữ nguyên. Dữ liệu đợt 03–06 dùng tên sổ hàng tổng hợp “Tấm gỗ tiêu âm Mộc” và mã hàng MOC-12 trên brief đã duyệt riêng. Test hồi quy dựng lại ca số đứng riêng và kiểm tra rằng bộ đánh giá vẫn gắn cờ trường Studio.

## Các bản bàn giao đợt 06

| Chiến dịch | Giao việc | Bản giao cuối và dấu vết |
|---|---|---|
| Vật liệu Hải Đăng | Nhà thầu phòng thu yêu cầu báo giá theo hộp. Tấm tiêu âm được nhắc tới trong landing và kế hoạch bán hàng | [Hồ sơ đã duyệt](acoustic-panel/approved-inputs.json) · [Nội dung chiến lược và đo lường](acoustic-panel/strategy-review.json) · [Landing và SEO](acoustic-panel/landing-review.json) · [Snapshot khách, work units, kết quả sandbox và tối ưu](acoustic-panel/journey.json) |
| Kỹ thuật Sông Lam | Quản đốc nhà máy đặt lịch khảo sát bảo trì theo máy | [Hồ sơ riêng](pump-service/approved-inputs.json) · [Landing và SEO](pump-service/landing-review.json) · [Snapshot khách, tài sản và run](pump-service/journey.json) |

Trong 34 trường của ba tài liệu đã ký, có 1 trường khách xem dùng nguyên văn đầu ra model và khác phương án xác định. Tựa SEO “Tấm gỗ tiêu âm Mộc” thay cho “Tấm gỗ tiêu âm Mộc | HN”. Đây là tên sản phẩm, chưa đo chất lượng sáng tạo hay hiệu quả SEO thực tế. Có 3 giá trị model trùng với phương án xác định nên chưa thể quy đóng góp riêng cho model. 22 phương án model khác bị chặn bởi tiêu chí Studio hoặc đánh giá bằng chứng, 8 trường dùng nội dung xác định. Chẳng hạn, đề xuất định vị chỉ chứa tên sản phẩm bị gắn cờ `entity_only` và phần lý giải chứa tuyên bố chất lượng bị gắn cờ `unsupported`. Mỗi mục `field_history` ghi trường thô của worker, mã yêu cầu, giá trị ban đầu, phương án xác định, revision thử và quyết định giữ hoặc thay.

Dữ liệu từng đợt tách bốn nguồn đóng góp. Worker journal giữ chữ do Qwen thực sự trả. Bộ soạn xác định tạo bốn bản theo kênh. Tài khoản biên tập chạy bằng script thử trường do model đề xuất, đối chiếu với báo cáo bằng chứng và lưu nội dung cuối. Tài khoản QA khác đối chiếu gate, ký từng nhóm trường rồi tài khoản khách tổng hợp duyệt snapshot. Nhãn “accepted” trong phần này chỉ có nghĩa là quyết định đã được diễn tập trong sandbox. Các số đo về chất lượng, chi phí nhân sự và khả năng chấp nhận của doanh nghiệp cần practitioner pilot.

Ca RFQ ghi hai yêu cầu, một phiên có nguồn, một lead Sales đã nhận, một đơn được xác nhận, hoàn và sửa số liệu còn 130.000 VND doanh thu tổng hợp. Chi phí thực thi mô phỏng là 20.000 VND. Một yêu cầu tiếp tục thiếu attribution. Bằng chứng browser đi kèm [bộ màn hình](../ui) và [hướng dẫn tái tạo](../../../campaign-engine/PLANNER.md).
