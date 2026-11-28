# Phiếu chấm một hướng dẫn sử dụng tại trang sản phẩm

**Đơn vị chấm là một bản Guide ở đúng revision, trong một tình huống và trên thiết bị được giao.** QA đối chiếu brief và nguồn đã khóa. Người đọc làm nhiệm vụ bằng bộ thẻ mô phỏng an toàn. Ghi nhận điểm của hai vai trò ở cột riêng. Chỉ thị cho người đọc nêu tình huống và mục tiêu, ví dụ “Bạn vừa nhận ca ở quầy mẫu. Hãy chuẩn bị bộ thẻ cho đồng nghiệp theo hướng dẫn trên màn hình.” Người quan sát không diễn giải nhãn, gợi ý thao tác, thứ tự, loại thẻ hay CTA. [Quy trình và phân công](PRACTITIONER.md)

## Thang quan sát

| # | Mục cần đo và bằng chứng | 2 | 1 | 0 |
| --- | --- | --- | --- | --- |
| 1 | Người đọc tự nêu hoàn cảnh dùng trước khi thao tác. Ghi nguyên ý, đối chiếu situation/purpose. | Nhận diện đúng hoàn cảnh và mục đích | Chỉ đúng một ý | Chọn sai hoàn cảnh hoặc không xác định được |
| 2 | Chụp revision, ghi thứ tự thao tác thực tế và lần tự sửa. | Hoàn tất các bước; tôn trọng phụ thuộc và định dạng bắt buộc | Tự phát hiện nhầm lẫn, quay lại và hoàn tất đúng | Bỏ bước, sai phụ thuộc, hoặc guide thiếu định dạng bắt buộc |
| 3 | QA đối chiếu từng chỉ dẫn, claim và nguồn P1; người quan sát ghi thao tác ngoài hướng dẫn. | Mọi chỉ dẫn có nguồn phù hợp, đủ bước | Phải yêu cầu làm rõ cách diễn đạt trong khi nguồn và toàn bộ thao tác vẫn nguyên vẹn | Có thao tác thêm/bớt hoặc claim sai dữ kiện |
| 4 | Sau khi đọc, người dùng tự chọn vật liệu hoặc danh sách trong bộ mô phỏng có cả lựa chọn ngoài điều kiện. | Áp dụng đúng mọi qualifier ngay lần đầu | Tự nhận ra và đổi lựa chọn trước khi thực hiện | Guide làm mất/đảo qualifier hoặc người đọc thực hiện ngoài điều kiện |
| 5 | Ghi vai trò, nhiệm vụ cần làm và từ ngữ người đọc gặp vướng. | Người đọc đúng đối tượng hiểu và thực hiện độc lập | Tự khắc phục một điểm mơ hồ, ghi đúng cụm từ | Hướng dẫn nhắm sai vai trò hoặc người đọc không thể tiến hành |
| 6 | QA so nguyên CTA với brief; người đọc chỉ ra hành động kế tiếp trong mockup. | CTA khớp và người đọc hiểu đúng | CTA khớp nhưng người đọc còn phân vân | CTA sai, vượt quyền hoặc dẫn người đọc sang hành động sai |
| 7 | Ghi viewport, thiết bị/zoom, loại input; người đọc xem giới hạn và thực hiện từ trang. | Đọc được toàn bộ, thao tác độc lập | Phải cuộn lại/phóng to để tìm thông tin nhưng vẫn hoàn tất | Nội dung bị cắt, che hoặc không thể hoàn tất |
| 8 | Editor chỉ đúng nguồn cho một bước, giới hạn, CTA và mục đích; QA kiểm tra lại. | Truy được đầy đủ P1 và field của brief/Work Order | Có đúng nguồn nhưng phải dò thêm ở ít nhất một trường | Dẫn sai nguồn, thiếu căn cứ hoặc cần quyền ngoài scope |

**9. Khối lượng biên tập.** Lưu danh sách thay đổi giữa bản đầu và cuối, gồm field, loại sửa, lý do, số lần lưu, revision. Báo số trường khác nhau và tổng số sửa riêng. Không sửa là 0 khi có đủ hai bản; thiếu bản ghi là `null`.

**10. Thời gian và tiếp nhận.** Bấm giờ đọc/làm/biên tập/QA, lưu thời điểm bắt đầu/kết thúc và thời gian chờ. Báo phút thực, trạng thái hoàn thành, quyết định nhận / sửa / giữ / từ chối, lý do và người có quyền quyết định.

Với checklist độc lập, thực hiện bước B trước A là hợp lệ khi brief và P1 cho phép. Một danh sách được đánh số cũng có thể đủ cho công việc đó. Với quy trình có phụ thuộc, kiểm riêng **thứ tự thật**, **tính đầy đủ** và **yêu cầu hiển thị của brief**. Ghi lỗi hiển thị dù người đọc tình cờ làm đúng thứ tự. Hướng dẫn của Google về viết procedure đặt trọng tâm vào trình tự, ngữ cảnh và thường dùng một hành động mỗi bước. Đây là hướng dẫn biên tập công khai đọc ngày 28/11/2026; mức tác động đối với người đọc của AMC cần đo riêng. [Google developer documentation style guide, Procedures](https://developers.google.com/style/procedures)

## Lỗi chặn và cách ghi kết quả

- Đánh dấu `HOLD` ngay khi phát hiện dữ kiện sai trọng yếu, thiếu/thêm bước có thể dẫn tới kết quả sai, đảo nghĩa/mất qualifier, CTA vượt quyền, sử dụng nguồn chưa được phép hoặc lộ dữ liệu. Ghi revision, field, nguồn và trích dẫn tối thiểu, kết quả mong đợi, quan sát thật và người xác minh. Dừng nhiệm vụ khi thao tác tiếp theo không an toàn.
- Khi guide đúng nguồn nhưng người đọc làm sai, ghi riêng lỗi thực hiện và điều kiện quan sát. Reviewer xác định nguyên nhân hoặc giữ “chưa rõ”. Tách lỗi guide khỏi trải nghiệm thực hiện; một hard failure về guide/thẩm quyền vẫn chặn nghiệm thu cho dù mọi điểm trình bày đạt 2.
- Ghi `not_observed` nếu thiếu lượt đọc hay thiếu quyền xem nguồn. Lưu phiếu đầu trước thảo luận, giữ cả ý kiến chưa thống nhất. Tổng hợp từng mục với tử/mẫu theo phương án, locale, loại công việc, thiết bị và số lượt thiếu. Không dùng điểm cộng dồn để vượt qua lỗi chặn.
- Receipt tối thiểu gắn alias công việc, stage, phiên bản thiết kế, source/brief digest, artifact/revision/digest được xem, thiết bị, người quan sát theo mã, excerpt hỗ trợ, điểm hoặc trạng thái và lý do. Khóa chéo nằm ở custodian. Chỉ thu ảnh màn hình tổng hợp khi đã đồng ý; phiếu cá nhân, thời gian chi tiết và biên bản được giữ trong kho riêng. [Protocol thực hành hiện hữu](../../round61/PRACTITIONER.md)
