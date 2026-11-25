# Chất lượng Marketing trên holdout C3 v1

Báo cáo đọc đầu ra thực của Qwen 0.5B trên dữ liệu tổng hợp cho năm nhóm người dùng. Số lần workflow chạy thành công cho biết hệ thống tạo được bản nháp. Chất lượng lần đầu và thời gian biên tập cần đánh giá trên chính bản giao. [Phương pháp, bộ brief và pilot](C3-HOLDOUT-AND-PILOT.md)

## Đánh giá nghiệp vụ tham khảo của AI

Mẫu cố định trước gồm ca 01 và 02 của mỗi nhóm. Người đánh giá AI đã biết phiên bản, có thể đọc cả checkpoint gốc và bản qua renderer. Mỗi dòng dưới đây ghi một khiếm khuyết đủ để cần biên tập; việc chấm lại phiên bản mới dùng cùng năm tiêu chí chiến lược hoặc sáu thành phần trang đích trong protocol. Kết quả chấm AI chỉ phục vụ nghiên cứu nội bộ.

| Ca | Bản lịch sử @2 hoặc @5 trên `6a2d65f3` |
| --- | --- |
| Agency 01, WF-03 | Với hộp trà AGH-101, trường định vị chỉ là tên sản phẩm. Khuyến nghị và phép đo dừng ở lời dẫn “thực hiện các bước sau”, thiếu bước tiếp theo. Phần A/B và KPI hữu ích do renderer điền. |
| Agency 02, WF-13 | Bản thiệp giấy tự thêm số hotline và lời đảm bảo chất lượng. Hồ sơ chỉ duyệt bề mặt nhám cùng điều kiện thương mại. Mục ý định tìm kiếm chỉ nêu nhóm đại lý. |
| Inhouse 01, WF-03 | Phần nghiên cứu lặp yêu cầu khảo sát và tên học xưởng. Định vị chỉ ghi tên lớp đóng sách. Kế hoạch đo của model chưa mô tả sự kiện hoặc cách loại trùng. |
| Inhouse 02, WF-13 | CTA cho lớp ký họa yêu cầu “Lập trình chương trình”. Meta description lặp tên thương hiệu bị sửa sai và kết thúc giữa câu. |
| Materials 01, WF-03 | Mẫu đá mài có phép đếm yêu cầu xác nhận trong 21 ngày. Bốn trường nghiên cứu lặp cùng giả thuyết về bề mặt mờ; định vị và lý do chọn kênh còn thiếu. |
| Materials 02, WF-13 | SEO title nhắc đúng loại nẹp nhôm. Giá trị, lợi ích và CTA cùng là nhận xét khách có thể tìm hiểu giá. Mục ý định tìm kiếm chỉ ghi tên xưởng. |
| Seller 01, WF-03 | Định vị túi vải tự thêm khuyến mãi rồi lặp các từ ngoài ngữ cảnh. Phép đếm yêu cầu đúng với brief; khuyến nghị chưa thiết kế được thử nghiệm cụ thể. |
| Seller 02, WF-13 | Giá trị đề xuất dùng đơn giá tiếng Anh. CTA chỉ mô tả kệ ba tầng. Phần ý định tìm kiếm ghi “Khách mua lẻ”, còn bỏ ngỏ quyết định chọn kệ cho phòng trọ. |
| Service 01, WF-03 | Mẫu bảo trì quạt xác định được sự kiện cần đếm, nhưng nội dung nghiên cứu lặp lại cùng giả thuyết. Định vị chỉ nêu tên dịch vụ. Đơn vị mua cụ thể bị hiển thị thành “suất dịch vụ”. |
| Service 02, WF-13 | Mục SEO đề cập dịch vụ giặt rèm và địa bàn. CTA diễn đạt việc xử lý yêu cầu từ phía doanh nghiệp; người dùng vẫn cần tự tìm cách gửi ảnh để khảo sát. |

Đối với mười bản trên, AI đánh giá **0/10 có thể nhận dùng ngay**. Thông tin thương mại được renderer khôi phục ở phần trên có thể đúng, trong khi nội dung do model viết thêm ở CTA hoặc SEO vẫn sai. Đây là hai lớp cần kiểm tra riêng.

## Cách kiểm tra bằng máy

```bash
python tests/evaluation/c3/summarize_qualification.py --arm reference=/path/holdout-reference --arm projected=/path/holdout-paired/projected --arm improved=/path/holdout-paired/improved --out c3-quality-summary.json
```

Công cụ đối chiếu SHA-256 của brief và nội dung, SKU đi cùng tên sản phẩm, giá và tiền tệ đọc được, đơn vị bán, thuế, MOQ, bậc giá và điều kiện nguyên văn. Nó phát hiện một số mẫu số điện thoại hoặc cam kết kinh doanh không có trong brief và phân biệt nhận định do cổng ứng dụng phân loại với kiểm tra độc lập. Các mẫu chữ chỉ giúp chọn câu cần đọc lại. Câu có thể hàm ý sai dù không chứa từ khóa và điều kiện xuất hiện ở một đoạn chưa chứng minh cho câu ở đoạn khác.

Tệp JSON đếm các lần gọi model có receipt, bản nháp thật, bản cần làm rõ, ca thiếu receipt, token và thời gian sinh bản. Mọi ca được giao đều thuộc mẫu số 50. Chỉ tính độ trễ sinh nội dung khi có lời gọi model. Khoảng biến thiên giữa các brief khác nhau không phải phép đo độ ổn định trên cùng một brief. Phí nhà cung cấp bằng 0 với inference local. Chi phí máy và nhân công cho mỗi bản được chuyên viên chấp nhận chưa xác định.

## Giới hạn

Không có phiếu của chuyên viên Marketing độc lập, bản chấm thời gian thủ công hoặc chi phí lao động đối chứng. SLA nghiệp vụ, mức giảm 30% tổng thời gian và ngưỡng ≥80% được chấp nhận lần đầu vẫn cần pilot. Kết quả ở môi trường nội bộ giữ trạng thái Commercial GA NO-GO.
