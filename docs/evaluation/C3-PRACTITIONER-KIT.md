# Giao pilot cho hai chuyên viên Marketing

**Chỉ điều phối viên giữ ZIP tổng và thư mục DIEU-PHOI.** Mỗi chuyên viên nhận đúng một ZIP của mình ở mỗi bước. Sáu gói đã tách sẵn để điều phối viên kiểm soát thời điểm mở đáp án. Tất cả doanh nghiệp và chứng cứ dùng trong pilot là dữ liệu tổng hợp.

1. Mời hai người khác nhau có kinh nghiệm làm chiến lược, nội dung chuyển đổi hoặc SEO. Ghi lĩnh vực, số năm kinh nghiệm và xung đột lợi ích vào phiếu. Mỗi người lưu bài và thời gian riêng.
2. Gửi riêng **CV-1/1-THU-CONG.zip** và **CV-2/1-THU-CONG.zip**. Mỗi người tự làm năm brief trong thứ tự đã ghi. Chỉ chuyển bước sau khi nhận lại các bài và phiếu có thời điểm kết thúc. Chưa gửi bản có trợ lý, tài liệu phần 3, khóa hay lời nhận xét của người kia.
3. Gửi **2-CO-TRO-LY.zip** tương ứng. Mỗi người biên tập năm brief khác với những brief mình vừa tự làm. Ghi mức chấp nhận nguyên bản ngay lúc đọc, giữ bản sửa cuối và ghi thời gian thực. Với yêu cầu làm rõ, ghi rõ thông tin thiếu, số phút xử lý và việc người dùng đã có thể nhận bàn giao hay chưa.
4. Khi đã nhận lại hai bộ kết quả, gửi riêng **3-CHAM-MU.zip**. Mỗi người chấm hai bản của cả 10 brief theo thứ tự riêng. Phần đầu của danh sách có một lượt cho mỗi brief; phần sau mới đưa ra bản còn lại. Phiếu trống ở PHIEU.json và thang điểm ở BAT-DAU.md của từng gói. Người chấm ghi việc đã gặp tài liệu nào ở bước 2 hoặc 3. Hình thức bản giao vẫn có thể tạo manh mối về phiên bản.
5. Giữ nguyên hai bộ phiếu. Đối chiếu riêng các ca bất đồng theo trường, câu, nguồn và điều kiện; lưu kết luận phân xử ở bản khác. Để đo thời gian đến lúc người khác chấp nhận, điều phối viên bỏ tên tác giả khỏi bài cuối của hai phiên có đồng hồ, chuyển sang chuyên viên kia duyệt sau khi cả hai đã khóa phiếu mù, rồi bổ sung số phút QA và chờ thực tế. Nếu chỉ có tự đánh giá, ghi rõ điều này khi diễn giải thời gian và chi phí. Ghi “chưa xác định” cho dữ liệu chưa đo, bao gồm chi phí máy hoặc đơn giá còn thiếu.

## Đọc kết quả

Lưu các phiếu nhận lại dưới các đường dẫn khác nhau, ví dụ `DA-TRA/CV-1/1/PHIEU.json`. Chạy bằng Python 3.10 trở lên từ thư mục chứa DIEU-PHOI.

```sh
python -X utf8 DIEU-PHOI/doi_chieu.py DIEU-PHOI/khoa.json DA-TRA > ket-qua.json
```

Bảng chất lượng có 20 lượt chấm dự kiến cho mỗi phiên bản (hai người × mười brief). Tỷ lệ đạt lần đầu giữ cả ca chưa có bản giao trong mẫu số. Công cụ chờ đủ phiếu trước khi tính tỷ lệ. Chứng cứ tính theo số câu cần nguồn và số câu thực sự có nguồn hỗ trợ. Không lấy sự đồng thuận thay cho chứng cứ. Chi phí mỗi bản hoàn tất gồm công lao động thực làm, phí máy và phí nhà cung cấp ở tất cả các phiên được giao, kể cả khi thất bại. Quy ước này không tính thời gian chờ thụ động vào công lao động; thời gian trôi qua vẫn gồm thời gian chờ.

Mười brief quy định bao phủ năm nhóm × hai workflow, **mỗi ô chỉ có một brief**. Mỗi brief có một phiên thủ công và một phiên có trợ lý do hai người khác nhau thực hiện; vai trò đổi qua các ô. Mỗi người chấm riêng tất cả các bản, với thứ tự hai phiên bản ngược nhau giữa hai chuyên viên. Tỷ lệ tiết kiệm thời gian là phép so sánh thăm dò trên cùng brief **giữa hai người**. Để tách ảnh hưởng kinh nghiệm cá nhân theo thiết kế bắt chéo trong cùng nhóm và workflow, cần bổ sung brief tương đương ở từng ô và khóa trước khi chạy. Các chỉ tiêu 100% dữ kiện đúng, 0 lỗi nghiêm trọng, ≥95% câu cần dẫn nguồn có căn cứ, ≥80% đạt nghiệp vụ lần đầu và ≥30% giảm thời gian là mục tiêu của pilot.

## Tạo lại

Từ root của repo, dùng đúng kết quả đã lưu và seed trong khóa điều phối.

```sh
python tests/evaluation/c3/build_practitioner_pilot.py THU-MUC-KET-QUA-HAI-PHIEN-BAN THU-MUC-XUAT --seed SO_TRONG_KHOA
```

Trình tạo chỉ lấy ca 01 và 02 của từng nhóm trong holdout v1. Nó giữ cách diễn đạt và điều kiện thương mại của đầu ra, dùng dấu thay thế cho mã kỹ thuật và xuất đúng yêu cầu làm rõ khi thiếu đơn vị bán. Các trường kiểm toán máy, prompt, thông tin định tuyến và đáp án chấm tự động không được đưa vào gói giao chuyên viên.
