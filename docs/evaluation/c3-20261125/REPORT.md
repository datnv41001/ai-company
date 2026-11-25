# Đánh giá bản giao Marketing ngày 25/11/2026

Ba mươi bản giao thực, gồm mười mục tiêu–workflow cho mỗi phiên bản. Năm doanh nghiệp đều là hồ sơ tổng hợp. Bản legacy được dùng làm đối chứng chung cho cả hai lần. Mỗi lần tạo bản giao đi qua dispatcher, worker và API PostgreSQL. Mỗi điểm dựa trên đánh giá bản khách nhìn thấy. Hai lượt chấm theo thiết kế ghép cặp trên cùng năm ca, có thể nhận ra phiên bản từ cấu trúc tài liệu.

| Kết quả trên 10 bản | Workflow cũ | C3 ban đầu | C3 sau sửa |
| --- | ---: | ---: | ---: |
| Dữ kiện | 4 | 8 | 10 |
| Phạm vi và điều kiện | 0 | 5 | 6 |
| Nguồn | 0 | 4 | 6 |
| Hành động người mua | 6 | 1 | 6 |
| Chuyên môn Marketing | 0 | 0 | 1 |
| Tránh tuyên bố thiếu căn cứ | 7 | 5 | 7 |
| Đạt cả sáu tiêu chí ngay lần đầu | 0 | 0 | 0 |
| Hoàn tất kỹ thuật ngay lần đầu | 9 | 10 | 10 |
| Token vào | 16928 | 13614 | 14371 |
| Token ra | 4371 | 2844 | 3130 |
| Lượt gọi model | 31 | 30 | 30 |
| Lượt thiếu số token | 0 | 0 | 0 |
| Trung vị giây/workflow | 25.29 | 19.77 | 20.92 |
| Phí nhà cung cấp USD | 0 | 0 | 0 |

## Điều kiện và cách đọc

Hai workflow nhận cùng mục tiêu tiếng Việt và cùng bộ dữ kiện gốc. Legacy nhận dữ kiện qua brief. C3 nhận các revision đã duyệt qua manifest theo vai trò. Phần hệ thống biểu diễn lại giá và qualifier là xử lý tất định. Các câu do model tạo hiện riêng trong raw output. Số giây có cả thời gian dispatch, suy luận và ghi kết quả. Mỗi ô chỉ chạy một lần ở seed 42. Chi phí điện và thời gian biên tập của con người chưa được đo. Hai đợt dùng cùng máy và weights, có tải nền khác nhau.

Hai người chấm là agent AI, mỗi agent phụ trách một workflow. Điểm first-pass nghiệp vụ yêu cầu đạt cả sáu tiêu chí trước biên tập. Chuẩn chấm, ca gốc và phương pháp chạy lại nằm trong [bộ evaluation](../../../tests/evaluation/c3/SCORING.md). Đợt thứ hai dùng lại đối chứng có cùng run ID. Kết quả chưa có kiểm định từ khách hàng hoặc bộ holdout mới.

## Bản giao và bằng chứng

| Ca | Workflow | Cũ | C3 ban đầu | C3 sau sửa |
| --- | --- | --- | --- | --- |
| seller | WF-03 | [2/6](legacy/seller-WF-03.md) | [4/6](first/seller-WF-03.md) | [5/6](revised/seller-WF-03.md) |
| seller | WF-13 | [3/6](legacy/seller-WF-13.md) | [2/6](first/seller-WF-13.md) | [3/6](revised/seller-WF-13.md) |
| materials | WF-03 | [1/6](legacy/materials-WF-03.md) | [3/6](first/materials-WF-03.md) | [4/6](revised/materials-WF-03.md) |
| materials | WF-13 | [3/6](legacy/materials-WF-13.md) | [3/6](first/materials-WF-13.md) | [5/6](revised/materials-WF-13.md) |
| service | WF-03 | [2/6](legacy/service-WF-03.md) | [2/6](first/service-WF-03.md) | [3/6](revised/service-WF-03.md) |
| service | WF-13 | [1/6](legacy/service-WF-13.md) | [0/6](first/service-WF-13.md) | [2/6](revised/service-WF-13.md) |
| agency | WF-03 | [1/6](legacy/agency-WF-03.md) | [4/6](first/agency-WF-03.md) | [4/6](revised/agency-WF-03.md) |
| agency | WF-13 | [2/6](legacy/agency-WF-13.md) | [2/6](first/agency-WF-13.md) | [5/6](revised/agency-WF-13.md) |
| inhouse | WF-03 | [1/6](legacy/inhouse-WF-03.md) | [3/6](first/inhouse-WF-03.md) | [3/6](revised/inhouse-WF-03.md) |
| inhouse | WF-13 | [1/6](legacy/inhouse-WF-13.md) | [0/6](first/inhouse-WF-13.md) | [2/6](revised/inhouse-WF-13.md) |

Giá trị ghi trong ô là số tiêu chí đạt. Mở mỗi ô để đọc nguyên văn bản giao. [Nhận xét từng bản, mã run, digest và raw output](receipts.json). [SHA source, weights và fixture giữa ba nhánh](conditions.json).

## Những điểm cần biên tập

Ca gạch GB-6060 sau sửa giữ giá tham khảo 210.000 VND/m², thuế, ngưỡng 50 m² và ngoại lệ vận chuyển, thi công. Lời mời gửi số lượng và địa điểm có thể dùng để yêu cầu báo giá. Nhưng model còn đặt câu về ngoại lệ vận chuyển vào trường CTA và dùng mục tiêu của bên bán làm tiêu đề SEO. Trong bản chiến lược, một chuỗi số tiền lặp lại ở trường kế hoạch đo không diễn đạt một phép đo.

Ở hai ca dịch vụ, đơn vị chung «suất dịch vụ» làm mất ý nghĩa máy/người của brief. Phiếu AN-1 cũng chỉ ra việc mở rộng phạm vi từ Hải Châu ra cả Đà Nẵng. Ở ca áo mưa, một bản chiến lược gắn được đặc điểm phản quang với thử nghiệm thông điệp và đơn MN-L đã thanh toán trong 28 ngày. Phải đọc cả nội dung do hệ thống kết xuất lẫn đề xuất của model để nhận ra khác biệt.

Model dùng chung là Qwen2.5-0.5B-Instruct (metadata của GGUF), qua llama.cpp build b12649-1f8baae28. Source runtime C3 sau sửa là 230380a. Các guard bổ sung sau đó được test riêng, hai manifest catalog và code adapter đã được đối chiếu cùng byte. Hệ thống sửa cách diễn đạt, thêm gợi ý hành động theo kênh và loại dòng sao chép mục tiêu nội bộ. Điều này chưa đạt ngưỡng biên tập chuyên nghiệp. Mẫu đã được dùng để phát hiện lỗi và sửa, nên điểm sau sửa là trên bộ phát triển.

## Quyết định nội bộ

Giữ bước đối chiếu nguồn và QA do người có thẩm quyền thực hiện. Bản giao đang ở trạng thái chờ QA. Lần thử tiếp theo cần tập brief mới do người làm Marketing xây dựng, chấm riêng chất lượng SEO/chiến lược và ghi thời gian biên tập theo tác vụ trước khi mở pilot khách hàng. Commercial GA NO-GO.
