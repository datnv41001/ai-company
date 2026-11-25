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

## So sánh trên cùng phiên bản phần mềm

Hai cấu hình chạy trên commit `08cc65b4de4ae637d3a3bbd70b7e1e0eb6128f32`, cùng Qwen 0.5B, weights `74a4da8c…`, llama.cpp `b12649-1f8baae28` và cùng holdout. Cấu hình mới thay đồng thời skill, hợp đồng nhập liệu và renderer. Thí nghiệm này đo tác động gộp của các thay đổi đó. Điểm dưới đây do AI đọc trực tiếp mười cặp 01/02 đã chọn trước.

| Chỉ số trên 10 brief đại diện | WF-03@2 / WF-13@5 | WF-03@3 / WF-13@6 |
| --- | ---: | ---: |
| Bản nháp đã lưu qua API ngay lần đầu | 10 | 6 |
| Cần làm rõ đơn vị bán trước khi gọi model | 0 | 4 |
| Lượt gọi model | 30 | 18 |
| Token vào / ra | 15.273 / 3.367 | 11.577 / 1.656 |
| Có tên sản phẩm và SKU, giá trích được khớp tiền tệ và giá trị | 10/10 nháp | 6/6 nháp |
| Ghi đúng đơn vị bán của brief cùng MOQ và bậc giá | 6/10 nháp | 6/6 nháp |
| Bản xem trước chứa nhãn công việc nội bộ | 10/10 nháp | 0/6 nháp |
| AI thấy bản đầu đủ để người làm Marketing nhận dùng | 0/10 brief | 0/10 brief |

Cả sáu nháp mới đều cần sửa nghiệp vụ. Bốn ca còn lại chưa có bản giao. Hai nhóm dịch vụ và lớp học dùng chung mã giá `service`, trong khi brief viết rõ “lượt” hoặc “người”. Cấu hình mới yêu cầu sửa bản giá đã được phê duyệt. Mỗi bản cần làm rõ vẫn tính vào mười brief được giao. Số token giảm một phần do bốn ca dừng sớm.

| Ca | Nhận xét sau đối chiếu hai lần chạy trên cùng commit |
| --- | --- |
| Agency 01 | Cả hai chiến lược còn thiếu định vị riêng. Bản mới xác định được hành động đăng ký bộ mẫu và loại trùng trong 21 ngày; giả thuyết chỉ nhắc lại nhu cầu kiểm tra nắp gập, chưa đề xuất biến thử hay kết quả kỳ vọng. Trường phân khúc chỉ ghi địa bàn Hải Phòng. |
| Agency 02 | Bản cũ đưa ra hotline và email ngoài nguồn. Bản mới bỏ các kênh liên hệ đó và có CTA “Đặt mẫu”, nhưng brief yêu cầu xin bảng màu. Tiêu đề chỉ ghi nhóm đại lý. Phần lợi ích lặp đơn giá bằng tiếng Anh mà thiếu điều kiện tại chính câu đó. |
| Inhouse 01 | Bản cũ biến giả thuyết về học viên thành khẳng định đã có người đăng ký lớp. Bản mới dừng ở khâu phê duyệt đơn vị học phí. |
| Inhouse 02 | Bản cũ đưa lệnh lập trình vào CTA. Bản mới hỏi lại đơn vị giá trước khi lập nội dung ghi danh. |
| Materials 01 | Bản cũ lặp giả thuyết về mặt đá và thiếu lý do chọn kênh. Bản mới chọn đúng trang báo giá nhưng chép câu hướng dẫn “Nêu điều kiện áp dụng và bước tiếp theo cho đúng người mua” vào cả hành động lẫn phương pháp đo. |
| Materials 02 | Tiêu đề mới nêu đúng sản phẩm và Hà Nội. Bản cũ có CTA xem báo giá; CTA mới chỉ ghi “Đội hoàn thiện công trình tại Hà Nội”. Mục search intent cũng chỉ nêu đối tượng thay vì nhu cầu báo giá theo chiều dài. |
| Seller 01 | Bản mới ghi rõ hành động đặt túi, nhưng định vị, giả thuyết và cơ sở quyết định đều lặp nhu cầu xác nhận vải nâu. Phương pháp đo của model chỉ ghi tùy yêu cầu và thời gian đặt hàng. |
| Seller 02 | Bản cũ nêu được kệ sách và lựa chọn ba tầng, nhưng CTA mới chỉ là mô tả. Bản nâng cấp đưa thông báo “Điều chỉnh giá thành công” vào cả tiêu đề trang và SEO title; brief không cung cấp sự kiện điều chỉnh giá. |
| Service 01 | Bản cũ hiển thị “suất dịch vụ” cho giá bảo trì quạt. Bản mới yêu cầu đơn vị bán đã được phê duyệt và chưa sinh bản chiến lược. |
| Service 02 | Bản cũ lặp mục tiêu gửi ảnh rèm ở CTA và đưa việc thiết kế/sản xuất sản phẩm vào mô tả SEO dịch vụ. Bản mới dừng trước khi sinh trang đích. |

Ba bản chiến lược mới hoàn thành có tổng cộng 15 đoạn tiêu đề và preview được cổng ứng dụng đánh dấu verified. Tài liệu chiến lược, ghi chú nghiên cứu và phép đo được xuất riêng; cả ba vẫn cần biên tập. Ba bản trang đích mới đều còn đoạn mâu thuẫn hoặc chưa giải quyết theo cổng ứng dụng. Đánh giá chuyên môn và duyệt chứng cứ của preview vì thế có mẫu số và đối tượng khác nhau.

Trên bộ đủ 50 brief, nhánh lịch sử tại `6a2d65f3` đã có 50 receipt, 150 lời gọi, 75.451 token vào, 16.251 token ra và thời gian sinh trung vị 17,63 giây. Cả 50 preview có giá trị tiền tệ khớp giá nguồn; chỉ 30/50 khớp đơn vị bán cụ thể và MOQ theo brief. Một preview có số điện thoại ngoài nguồn. Ba preview khớp từ khóa cam kết hoặc khuyến mãi cần đọc lại. Phí nhà cung cấp bằng 0.

## Cách kiểm tra bằng máy

```bash
python tests/evaluation/c3/summarize_qualification.py --arm reference=/path/holdout-reference --arm projected=/path/holdout-paired/projected --arm improved=/path/holdout-paired/improved --out c3-quality-summary.json
```

Công cụ đối chiếu SHA-256 của brief và nội dung, SKU đi cùng tên sản phẩm, giá và tiền tệ đọc được, đơn vị bán, thuế, MOQ, bậc giá và điều kiện nguyên văn. Nó phát hiện một số mẫu số điện thoại hoặc cam kết kinh doanh không có trong brief và phân biệt nhận định do cổng ứng dụng phân loại với kiểm tra độc lập. Các mẫu chữ chỉ giúp chọn câu cần đọc lại. Câu có thể hàm ý sai dù không chứa từ khóa và điều kiện xuất hiện ở một đoạn chưa chứng minh cho câu ở đoạn khác.

Tệp JSON đếm các lần gọi model có receipt, bản nháp thật, bản cần làm rõ, ca thiếu receipt, token và thời gian sinh bản. Mọi ca được giao đều thuộc mẫu số 50. Chỉ tính độ trễ sinh nội dung khi có lời gọi model. Khoảng biến thiên giữa các brief khác nhau không phải phép đo độ ổn định trên cùng một brief. Phí nhà cung cấp bằng 0 với inference local. Chi phí máy và nhân công cho mỗi bản được chuyên viên chấp nhận chưa xác định.

## Giới hạn

Không có phiếu của chuyên viên Marketing độc lập, bản chấm thời gian thủ công hoặc chi phí lao động đối chứng. SLA nghiệp vụ, mức giảm 30% tổng thời gian và ngưỡng ≥80% được chấp nhận lần đầu vẫn cần pilot. Kết quả ở môi trường nội bộ giữ trạng thái Commercial GA NO-GO.
