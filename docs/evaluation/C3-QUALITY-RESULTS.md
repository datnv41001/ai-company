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

## Kết quả đủ 50 cặp trên cùng commit

Mỗi cấu hình đã tiếp nhận đủ 50 brief. Cả 100 kết quả có receipt, gồm 80 bản nháp và 20 yêu cầu làm rõ. Chỉ mười brief đã chọn trước ở mỗi cấu hình có thêm nhận xét nghiệp vụ của AI.

| Thước đo | @2 / @5 | @3 / @6 |
| --- | ---: | ---: |
| Sinh được bản nháp | 50/50 (100%) | 30/50 (60%) |
| Sinh nháp ngay lần thử kỹ thuật đầu tiên | 50/50 (100%) | 29/50 (58%) |
| Cần làm rõ trước suy luận | 0/50 | 20/50 (40%) |
| Lượt gọi model có số token | 150/150 | 91/91 |
| Token đầu vào / đầu ra | 75.478 / 16.419 | 58.354 / 8.573 |
| Độ trễ sinh nháp, trung vị [min–max] | 17,76 s [12,41–60,83] | 17,03 s [12,55–100,49] |
| Trên 30 brief cả hai đều ra nháp, trung vị | 16,30 s | 17,03 s |
| Khớp các giá tiền đọc được, tiền tệ và tên sản phẩm | 50/50 nháp | 30/30 nháp |
| Có đúng đơn vị bán, MOQ và bậc giá ghi trong brief | 30/50 nháp | 30/30 nháp |
| Xuất hiện nhãn nội bộ trong preview | 50/50 nháp | 0/30 nháp |
| Có mẫu số điện thoại ngoài nguồn | 1/50 nháp | 0/30 nháp |

Các brief yêu cầu làm rõ gồm đủ mười trường hợp dịch vụ và mười trường hợp lớp học. Trong 30 trường hợp mới có nháp, 29/30 hoàn tất kỹ thuật ngay lần đầu và một trường hợp dùng thêm một lượt gọi. Tổng phí nhà cung cấp bằng 0 USD ở cả hai cấu hình.

Cổng ứng dụng ghi cho phiên bản mới 137 đoạn verified, 22 unresolved và 30 contradiction trên các tiêu đề và preview. Cả 15 preview chiến lược mới chỉ có đoạn verified; cả 15 trang đích mới còn đoạn mâu thuẫn hoặc chưa giải quyết. Ở phiên bản cũ, cả 50 nháp có ít nhất một đoạn cần xử lý. Tỷ lệ đoạn verified của gate không đo độ đúng của mọi câu trong tài liệu nội bộ hoặc các trường SEO và không phải số đo độc lập về ngưỡng 95% nguồn hỗ trợ. Trên cả hai cấu hình, kiểm tra mẫu SKU chưa bắt gặp mã SKU khác trong văn bản. SKU có thể trùng giữa hồ sơ; bằng chứng cách ly khách hàng phải đến từ suite phân quyền trên PostgreSQL.

## Lặp lại 10 brief và đo bộ nhớ

Lần chạy thứ hai dùng cùng SHA, weights, seed, release và danh sách brief. Cả 20 cặp kết quả theo từng cấu hình giữ nguyên trạng thái. Cấu hình cũ tạo nháp cả hai lần trên 10 ca; cấu hình mới tạo nháp cả hai lần trên 6 ca, còn 4 ca đều yêu cầu làm rõ.

| Chỉ số ghép theo cùng brief có nháp cả hai lần | @2 / @5 | @3 / @6 |
| --- | ---: | ---: |
| Tiêu đề cùng nội dung preview trùng hoàn toàn | 4/10 | 2/6 |
| Toàn bộ trường chữ model sinh giống hệt, bỏ qua handle nguồn | 4/10 | 1/6 |
| Số trường chữ thay đổi / tổng trường đối chiếu | 22/90 | 25/63 |
| Các request thành công của mọi vai trò có cùng hash | 5/10 | 1/6 |
| Chênh lệch tuyệt đối độ trễ sinh theo brief, trung vị / lớn nhất | 4,61 s / 38,78 s | 6,94 s / 13,86 s |
| Chênh lệch tuyệt đối token đầu vào, trung vị / lớn nhất | 0 / 64 | 2 / 32 |
| Chênh lệch tuyệt đối token đầu ra, trung vị / lớn nhất | 16 / 50 | 12,5 / 32 |

Kết quả cho thấy hai lần cùng brief có thể cho câu chữ khác nhau. Quá trình dựng lại dữ liệu và đầu ra của các bước trước có thể làm thay đổi request ở các bước sau, nên chưa thể quy tất cả biến thiên cho phép lấy mẫu của model. Hai lần chạy cho mỗi ca cũng chưa cho phép ước lượng độ tin cậy của chất lượng ở quần thể khách hàng.

Sampler Windows theo dõi một tiến trình `llama-server` (PID 28116) từ 13:45:54 đến 14:36:49 ngày 25/11/2026, giờ Việt Nam. Trong 2.895 quan sát, khoảng cách lấy mẫu trung vị là 1,038 s, lớn nhất 2,186 s. Working set cao nhất quan sát được là 924.962.816 byte (882,113 MiB). Đỉnh working set theo vòng đời tiến trình do Windows báo là 924.966.912 byte (882,117 MiB). Hai số này áp dụng cho tiến trình phục vụ nhiều ca; phép đo không phân bổ RAM hoặc chi phí máy cho từng bản giao.

## Cách kiểm tra bằng máy

```bash
python tests/evaluation/c3/summarize_qualification.py --arm reference=/path/holdout-reference --arm projected=/path/holdout-paired/projected --arm improved=/path/holdout-paired/improved --out c3-quality-summary.json
```

Công cụ đối chiếu SHA-256 của brief và nội dung, SKU đi cùng tên sản phẩm, giá và tiền tệ đọc được, đơn vị bán, thuế, MOQ, bậc giá và điều kiện nguyên văn. Nó phát hiện một số mẫu số điện thoại hoặc cam kết kinh doanh không có trong brief và phân biệt nhận định do cổng ứng dụng phân loại với kiểm tra độc lập. Các mẫu chữ chỉ giúp chọn câu cần đọc lại. Câu có thể hàm ý sai dù không chứa từ khóa và điều kiện xuất hiện ở một đoạn chưa chứng minh cho câu ở đoạn khác.

Tệp JSON đếm các lần gọi model có receipt, bản nháp thật, bản cần làm rõ, ca thiếu receipt, token và thời gian sinh bản. Mọi ca được giao đều thuộc mẫu số 50. Chỉ tính độ trễ sinh nội dung khi có lời gọi model. Khoảng biến thiên giữa các brief khác nhau không phải phép đo độ ổn định trên cùng một brief. Phí nhà cung cấp bằng 0 với inference local. Chi phí máy và nhân công cho mỗi bản được chuyên viên chấp nhận chưa xác định.

Khi đủ hai lần chạy trên mười brief đại diện, so sánh từng cặp như sau.

```bash
python tests/evaluation/c3/compare_repeats.py /path/holdout-paired /path/holdout-repeat --memory /path/model-memory.ndjson --process /path/model-process.json --out c3-repeat-summary.json
```

Với mỗi brief và cấu hình, công cụ xác minh cùng SHA, weights, dữ liệu, ID lần gọi khác nhau, rồi so độ trễ, token, câu chữ ở lần gọi thành công cuối cùng của mỗi vai trò và digest của tiêu đề cùng preview. Nó cũng ghi hash của request có lặp lại hay không. Việc dựng lại hồ sơ có thể đổi thứ tự các handle nguồn và làm thay đổi prompt. Hai lần chạy chỉ cho phép mô tả sai khác quan sát được. Bộ nhớ resident lớn nhất trong chuỗi lấy mẫu và đỉnh do Windows lưu suốt vòng đời của tiến trình model được báo riêng.

## Giới hạn

Không có phiếu của chuyên viên Marketing độc lập, bản chấm thời gian thủ công hoặc chi phí lao động đối chứng. SLA nghiệp vụ, mức giảm 30% tổng thời gian và ngưỡng ≥80% được chấp nhận lần đầu vẫn cần pilot. Kết quả ở môi trường nội bộ giữ trạng thái Commercial GA NO-GO.
