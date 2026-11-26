# Đánh giá một gói công việc Marketing từ brief đến bản giao

Đợt đối chứng tiếp theo dùng 84 câu đối chiếu điều khoản và 24 sản phẩm viết thuộc sáu nhiệm vụ Marketing. Có thể kiểm tra từng lời gọi, quy tắc chấm và chi phí đã quan sát trong [hồ sơ đánh giá độc lập](advisory/RESULTS.md).

**Giữ Commercial GA ở mức NO-GO.** Trên hai brief B2B mới, Qwen 7B tạo được vài đề xuất có ích ở bản đầu. Khi đi hết luồng biên tập và QA hiện hành, cả bốn tài liệu chiến lược/landing của nhánh này đều quay về câu chữ của bộ soạn xác định. Bản social cho khay bị cụt ngay phần điều kiện đơn hàng. Hai mẫu social và ad của dịch vụ lặp nguyên văn một lời hứa tăng hiệu quả thiếu căn cứ. Hai ca chưa cho thấy lợi ích đủ để mặc định dùng 7B. [Hai bộ tài liệu thực tế sau biên tập](DELIVERABLES.md) · [Đối chiếu từng nguyên bản trong archive](DEPARTMENT-RECEIPTS.zip)

## Thiết kế và các lần chạy

Khóa brief và rubric tại `06c4da2b` trước inference. Khe Gọn bán khay theo hộp cho tổ trưởng lắp ráp; nguồn xác nhận **vách ngăn** có thể tháo ở mẫu tiêu chuẩn. Luồng Rõ nhận lịch khảo sát kho; kết quả cam kết là **sơ đồ luồng nhận hàng trong phạm vi một buổi**. Đối chứng xác định và ba nhánh Qwen 2.5 Instruct đều dùng đúng projection đã duyệt cho từng ca. Mỗi nhánh model đi qua hai workflow trên PostgreSQL với vai Director/Research/Strategy và Director/Content/SEO; một lần gọi riêng sinh social/ad từ hai kết quả. Creative brief và lịch 21 ngày do bộ soạn xác định cung cấp trong cả bốn nhánh. Lời gọi theo kênh chỉ phục vụ nghiên cứu. [Đăng ký trước](PROTOCOL.md) · [Cách tái lập](RUNBOOK.md)

14/14 bộ so sánh theo ca/vai có system prompt, schema và tham số giống nhau trên ba model. 6/14 request đầu giống nhau hoàn toàn. Tám request khác nhau ở dữ liệu trung gian do model trước sinh ra. Các nhánh có cùng runtime AMC, bản llama.cpp, seed 42, nhiệt độ 0, bốn luồng CPU và context 8.192. Trọng số GGUF được kiểm SHA-256. Nhánh 0.5B và hai nhánh sau chạy trên hai runner khác nhau cùng cấu hình khai báo. [Manifest và điều kiện đo](RECEIPTS.json)

| Nhánh | Lần gọi hoàn tất | Token vào / ra | Giây chạy hai ca | Giây khởi tạo | CPU giây | RAM đỉnh container GiB |
|---|---:|---:|---:|---:|---:|---:|
| Đối chứng xác định | 0 | 0 / 0 | Chỉ đo rebuild | — | — | — |
| 0.5B | 14 | 9.667 / 1.783 | 116,52 | 17,10 | 399,41 | 0,36 |
| 1.5B | 14 | 9.662 / 1.653 | 149,45 | 10,80 | 546,58 | 1,24 |
| 7B | 14 | 9.607 / 1.915 | 675,73 | 38,34 | 2.547,62 | 4,15 |

Trong cohort hoàn tất, 12 workflow trả tài liệu ngay lần đầu. 36 lần gọi theo vai và sáu lần gọi theo kênh có biên nhận, tổng 28.936 token vào và 5.351 token ra. 12 snapshot được tài khoản fixture duyệt sau biên tập theo script. Tám gói có đủ mục ở cả hai thời điểm. Ước lượng chi phí provider bằng 0 USD. Chi phí máy/điện, lương, thời gian thực hành và giá mỗi gói được người có thẩm quyền chấp thuận đều chưa đo được. Bản dựng lại offline của đối chứng mất 2,41 ms và 1,05 ms theo thứ tự hai brief; chỉ đo thao tác soạn trong Python, loại khởi tạo, database và con người. CPU timer của hai lệnh ngắn trả về 0. Không dùng số này để so tốc độ end-to-end. [Run đã hoàn tất](https://github.com/datnv41001/ai-company/actions/runs/45728814303)

Lần thử hạ tầng đầu dừng trước inference vì thiếu thư mục cache. Lần kế tiếp đã đo xong 0.5B, sau đó phiên đăng nhập fixture hết hạn khi đọc kết quả 7B. Container 7B lần đó dùng 928,88 CPU giây, RAM đỉnh 3.941.756.928 byte và 26,41 giây khởi tạo. Số lần gọi và token của phần 7B gián đoạn chưa khôi phục được. Cộng riêng phần tài nguyên này khi dự toán toàn nghiên cứu. Lần tiếp tục dùng lại gói 0.5B có kiểm digest, xác nhận cả thứ tự nguồn F1/F2, giữ phép đăng nhập thường và checkpoint từng lần gọi mới. [Lần khởi động](https://github.com/datnv41001/ai-company/actions/runs/45726782238) · [Lần gián đoạn](https://github.com/datnv41001/ai-company/actions/runs/45727062233) · [Archive gốc](FIRST-STUDY.zip)

## Nội dung nào đi tới bản giao

| Trường của WF-03/WF-13 trên cả hai ca | 0.5B | 1.5B | 7B |
|---|---:|---:|---:|
| Khác đối chứng, giữ nguyên văn từ invocation | 1 | 0 | 0 |
| Khác đối chứng, gate/biên tập chọn lại đối chứng | 32 | 34 | 33 |
| Bộ soạn sinh trực tiếp | 14 | 14 | 14 |
| Model trùng đối chứng | 5 | 4 | 5 |

Trong 156 trường được đối chiếu, tiêu đề SEO 0.5B **“Khay chia linh kiện Khe Gọn”** là trường duy nhất khác đối chứng được giữ nguyên văn, bỏ hậu tố “| HN”. Có đề xuất đúng một phần bị thay toàn trường. Ví dụ đề xuất đo RFQ của 7B nhận diện số hộp, địa bàn và thời điểm; 7B vẫn mất gần 5,8 lần thời gian của 0.5B trong hai ca. Cần tối ưu cách nhận từng mệnh đề có nguồn và tính hữu dụng trước khi đổi model mặc định. Sáu bộ social/ad lưu riêng sau WF, giữ nguyên để người đọc thấy chất lượng thực, đang ở trạng thái `research_candidate_unreviewed`. [Receipt trước/sau của từng trường](DEPARTMENT-RECEIPTS.zip)

## Chấm nghiệp vụ trên cả gói

Người chấm bảng này là AI kỹ thuật phụ trách nghiên cứu, đã thấy tên nhánh. Các cột điểm đều theo cùng thứ tự **người mua, định vị, chiến lược, landing, SEO, social, ad, đo lường**. Mỗi số từ 0–2 theo rubric đăng ký trước. Đối chiếu cả kế hoạch chung và tài liệu giao. Trong ca dịch vụ, kế hoạch gốc nêu đúng tỷ lệ lịch xác nhận/đề nghị khảo sát, còn phép đo giao khách sau QA lại lấy lượt vào trang làm mẫu số. Lỗi xuyên tài liệu đó chặn sử dụng KPI dù có QA kỹ thuật. Tổng điểm chỉ để nhận biết phần phải sửa; một lỗi trọng yếu vẫn chặn giao.

| Brief / nhánh | Bản đầu, tám điểm | Sau biên tập, tám điểm | Bằng chứng và điều cần sửa |
|---|---|---|---|
| Khay / đối chứng | 2 1 1 1 1 1 1 2 | 2 1 1 1 1 1 1 2 | Câu hỏi “Trong lần mua gần nhất” dùng được cho phỏng vấn. Rationale chọn web vì được duyệt, chưa có lý do tiếp cận người mua. CTA “Yêu cầu báo giá” bỏ ba trường RFQ. Social/ad chỉ nhắc tên sản phẩm. |
| Khay / 0.5B | 1 0 1 0 0 0 0 0 | 2 1 1 1 1 0 0 2 | Đổi bộ phận tháo rời thành cả khay. Phương pháp đo liệt kê “11 ngày, 21 ngày, 1 tháng, 1 năm”. Social chép “Đây là một bài mạng xã hội và một mẫu quảng cáo”; ad cụt. Tiêu đề SEO cuối gọn hơn, mất dấu hiệu địa bàn. |
| Khay / 1.5B | 1 0 1 0 0 0 0 0 | 2 1 1 1 1 0 0 2 | “designed to be reusable” và “giá ưu đãi” vượt nguồn; điều kiện mua lẫn chữ Hán. Social/ad lặp ưu đãi và không viết hết câu. |
| Khay / 7B | 2 1 1 1 1 0 1 2 | 2 1 1 1 1 0 1 2 | Có câu hỏi mua vách ngăn tháo rời, RFQ có ba trường và mẫu số. Copy hứa quản lý hiệu quả; social đứt ở “Đơn tối nhỏ:”. Ad ghi đúng giá, đơn vị, thuế, số lượng tối thiểu và xác nhận; còn thiếu hướng dẫn điền RFQ. |
| Khảo sát / đối chứng | 2 1 1 1 1 1 1 0 | 2 1 1 1 1 1 1 0 | “quy cách có thể đối chiếu” quá chung cho dịch vụ; CTA “Đặt lịch” thiếu địa điểm và ca. Sales sẽ dùng sai mẫu số nếu chỉ đọc tài liệu được giao. |
| Khảo sát / 0.5B | 0 0 1 1 0 0 1 0 | 2 1 1 1 1 0 1 0 | Phương pháp đo lặp “web”; SEO chỉ “appointment”. Ad có câu “Đặt lịch, ghi địa điểm và ca nhận hàng cần quan sát”, thích hợp hơn bản kiểm soát ở điểm này. Còn thiếu điều kiện xác nhận số lượng và pha tiếng Anh. |
| Khảo sát / 1.5B | 1 0 0 0 0 0 0 0 | 2 1 1 1 1 0 0 0 | “nhận 760.000 VND” khiến người mua hiểu họ được trả tiền. Định vị có mảnh “reception and”; social và ad trùng câu đảo chiều giá. Lỗi vẫn có trong hai mẫu nghiên cứu sau QA. |
| Khảo sát / 7B | 1 0 0 0 0 1 0 1 | 2 1 1 1 1 1 0 0 | “đề xuất tạo điểm chờ” đảo nghĩa vấn đề cần khảo sát, gán căn cứ cho khảo sát chưa có; SEO lẫn “您”. Phần đầu phép đo đúng tử/mẫu và xử lý hủy nhưng câu sau lặp, đứt. Social bằng ad và cùng hứa tăng hiệu quả. |

Bản biên tập xác định sửa nhiều trường về đúng giá, đơn vị và phạm vi, đồng thời làm mất vài đề xuất đúng hơn về đo lường. Cần kiểm tra ý nghĩa **sau biên tập** và tính nhất quán giữa plan, strategy, trang và các kênh. Cả hai creative brief chỉ nêu chủ thể, CTA, giọng điệu và kiểm quyền hình. Lịch phân vai ở ngày 7/14/21 hữu ích để giao việc, chưa chứa ảnh, kết quả xuất bản hoặc tín hiệu thị trường.

Một AI engineering khác đọc trích đoạn bản đầu của ca dịch vụ, khóa tài liệu trước khi mở nhãn (SHA-256 `a52bf26cf2a1795ad17a3a792d462fa9e07ffc74898ef5d84334e3614942682d` trên Windows CRLF, `acb6e861627b491c5e288d3c51225d314d149f223e48e0c32c05f95de8d4d0c1` với LF của Git). P-104d21d1 là đối chứng, P-ea9ff1ea là 7B, P-6a0368af là 0.5B và P-1bde29a0 là 1.5B. Người đọc đề nghị biên tập cả bốn; lỗi mẫu số của đối chứng, CTA đủ thông tin của 0.5B và hướng thanh toán sai của 1.5B có ý nghĩa trực tiếp với người nhận. [Nhận xét đã khóa](BLIND-SERVICE-REVIEW.md)

## Quyết định và bước nghiệm thu

1. Giữ điều kiện QA, ký revision và phê duyệt con người. Thêm ca đối chứng kiểm ai trả tiền cho ai, phạm vi bộ phận/sản phẩm, trạng thái giả thuyết và cùng tử số/mẫu số qua từng tài liệu. Cần kiểm toàn câu ở mọi vị trí có giá hoặc lời hứa.
2. Ưu tiên sửa CTA theo hành động mua và viết rõ các thông tin cần thu, tách hook social khỏi message ad, phát hiện nội dung cụt/lặp. Đo lại trên brief chưa từng dùng với trọng số và chính sách sửa đã khóa. [Độ bao phủ V1](V1-COVERAGE.md)
3. Pilot thực hành cần một người làm Marketing, một reviewer và một Sales/owner có đồng thuận. Chưa có người tham gia, bản làm tay, số phút thực tế, đơn vị kinh doanh được chấp thuận hoặc doanh thu quan sát. Hai gói ZIP cho phép chạy ngay trên dữ liệu tổng hợp và tính lại khi có phiếu. [Hướng dẫn và công thức chi phí](PILOT.md) · [Tác vụ thủ công](PILOT-KIT/01-manual.zip) · [Ứng viên ẩn nhãn](PILOT-KIT/02-candidates.zip)
