# Cơ hội sản phẩm từ nghiên cứu

C2 là luồng đang cho người dùng thử. C3 là luồng áp dụng tiếp theo. Danh sách này cung cấp đầu vào cho quyết định roadmap; chỉ PR triển khai cùng bằng chứng mới thay đổi trạng thái sản phẩm. Trạng thái hiện tại của từng phương pháp được ghi trong [ma trận](APPLICABILITY_MATRIX.md).

<a id="o-01"></a>

## O-01 · Gói tri thức cho WF-03 và WF-13

**Thứ tự và người phụ trách dự kiến.** C3 đầu tiên sau khi chốt C2. Chủ C3 và QA nghiệp vụ.

**Giá trị cho người dùng.** Nhân viên chiến lược và editor nhận đúng SKU, thị trường, qualifier và phần còn thiếu; giảm đối chiếu bằng tay.

**Module và phụ thuộc.** [K-01](KNOWLEDGE_CARDS.md#k-01)/[K-02](KNOWLEDGE_CARDS.md#k-02). AIO-06, MKT-03, WF-03/13. Dùng brief pin của C2, C1 authority, adapter release riêng và QA theo revision.

**Nghiệm thu.** Cùng một brief đóng băng chạy baseline và candidate trên bộ ca có nguồn xung đột, quá hạn, sai brand và thiếu nguồn. Reviewer chấm tính hữu ích, citation, qualifier và lỗi nghiêm trọng trước khi mở nhãn phiên bản. Thu hồi nguồn giữa queue/QA/share phải chặn lần dùng tiếp theo và giữ bản đã giao. Ghi token/chi phí thực, không chấp nhận candidate sinh thêm lỗi quyền.

<a id="o-02"></a>

## O-02 · Quản lý thay đổi Marketing Skill

**Thứ tự và người phụ trách dự kiến.** Song hành phát hành adapter C3. Chủ registry.

**Giá trị cho người dùng.** Người vận hành tái tạo được bản nháp và biết rubric nào làm đổi kết quả.

**Module và phụ thuộc.** [K-03](KNOWLEDGE_CARDS.md#k-03). AIO-03/09, WF-13. Dùng registry, release pin, hash runtime và fixture cũ.

**Nghiệm thu.** Tạo bản thứ hai của một rubric nội dung. Replay bản cũ cho cùng bytes/phiên bản. Bản mới chạy cả ca tốt lẫn ca thiếu qualifier. Chỉ chủ phát hành có thể kích hoạt cho campaign đúng scope, và có đường quay lại bản pin cũ.

<a id="o-03"></a>

## O-03 · Command Center phản ánh công việc và mục tiêu

**Thứ tự và người phụ trách dự kiến.** Áp dụng ngay ở C2; nối goal→outcome ở C3. Chủ frontend và QA.

**Giá trị cho người dùng.** Solo tìm việc đầu tiên để làm. Business thấy tiến độ và kết quả theo mục tiêu. Agency thấy rõ khách hàng trước khi mở một bản giao.

**Module và phụ thuộc.** [K-04](KNOWLEDGE_CARDS.md#k-04)/[K-11](KNOWLEDGE_CARDS.md#k-11). AIO-01, AGY-05, MKT-18. Các API đã phân quyền, dữ liệu task/campaign/deliverable và design system của PR UI riêng.

**Nghiệm thu.** Kiểm workspace trống, workspace có hai khách, lỗi nguồn và trả lời đến muộn. Với fixture biết trước, số hiển thị phải khớp dữ liệu được quyền đọc; thanh tiến độ có mẫu số, kết quả QA có trạng thái. Chụp ảnh desktop/tablet/mobile trong sáng/tối, thử bằng bàn phím. Hoạt động đã xong không tự tạo doanh thu.

<a id="o-04"></a>

## O-04 · Bảng chọn cơ hội trong brief

**Thứ tự và người phụ trách dự kiến.** Sau khi có dữ kiện discovery. Chủ strategy.

**Giá trị cho người dùng.** Account manager giải thích với khách vì sao ưu tiên một vấn đề trước vấn đề khác.

**Module và phụ thuộc.** [K-05](KNOWLEDGE_CARDS.md#k-05). AGY-02, MKT-01/02/05. Cần mục tiêu, segment, evidence locator và người quyết định.

**Nghiệm thu.** So hai cơ hội cho cùng outcome, ghi tác động dự kiến, cơ sở ước lượng, effort và giả định. Nguồn thiếu phải được đánh dấu; người phụ trách có thể chọn phương án điểm thấp hơn với lý do được lưu. Một ca không đủ bằng chứng phải có kết quả hoãn quyết định.

<a id="o-05"></a>

## O-05 · Dẫn xuất asset theo kênh

**Thứ tự và người phụ trách dự kiến.** Sau khi C3 có bản giao dùng được. Chủ Content Studio.

**Giá trị cho người dùng.** Editor tái sử dụng nội dung mà vẫn truy được nguồn và lịch sử duyệt.

**Module và phụ thuộc.** [K-06](KNOWLEDGE_CARDS.md#k-06). MKT-07/08/11, AIO-08. Snapshot, quyền reuse, channel và bản nội dung gốc.

**Nghiệm thu.** Từ asset đã duyệt tạo đúng một biến thể email sau hai lần gửi lại cùng lệnh. Ghim revision/digest của gốc, quyền và locale. Kiểm giá hết hạn, nguồn bị rút, người đọc khác client. Biến thể cần QA mới và giữ nguyên snapshot cũ.

<a id="o-06"></a>

## O-06 · Phiếu đọc kết quả thử nghiệm

**Thứ tự và người phụ trách dự kiến.** Sau khi có hợp đồng event. Chủ analytics.

**Giá trị cho người dùng.** Analyst và marketer nhận được quyết định dùng/hoãn/hủy có lý do thay vì một phần trăm lift thiếu căn cứ.

**Module và phụ thuộc.** [K-07](KNOWLEDGE_CARDS.md#k-07). MKT-12/17, WF-13/19. Cần phân bổ, cửa sổ, mẫu số, metric, nguồn và guardrail.

**Nghiệm thu.** Trên dữ liệu tổng hợp, tính ví dụ 10/100 và 15/100 thành +5 điểm phần trăm, +50% tương đối. Ca mất log variant, trùng exposure hoặc chưa hết cửa sổ phải hiện chưa kết luận. Một thay đổi làm hỏng guardrail không tự được triển khai dù CTR tăng.

<a id="o-07"></a>

## O-07 · Đối soát lead với doanh thu

**Thứ tự và người phụ trách dự kiến.** Sau hợp đồng CRM/consent; thử offline trước. Chủ data và CRM.

**Giá trị cho người dùng.** Chủ doanh nghiệp phân biệt lượt quan tâm, lead đủ chuẩn và tiền thực thu.

**Module và phụ thuộc.** [K-08](KNOWLEDGE_CARDS.md#k-08). MKT-13/16/17, WF-17/18/20. Cần mapping ID theo tenant, event schema, nguồn hợp lệ, fiscal period và tiền tệ.

**Nghiệm thu.** Fixture gồm lead lặp, conversion đến trễ, khoản hoàn và hai loại tiền. Đếm distinct đúng kỳ theo quy tắc công bố, không cộng chéo tiền tệ, phân biệt 0 với null. Mỗi doanh thu có đối chứng sổ đơn/hóa đơn phù hợp định nghĩa. Không có quyền đọc thì không trả hàng của khách khác.

<a id="o-08"></a>

## O-08 · Từ lỗi đã phản biện tới thẻ reviewer

**Thứ tự và người phụ trách dự kiến.** Engineering song song, giới hạn ở fixture công khai/tổng hợp. Chủ AIRC.

**Giá trị cho người dùng.** QA và reviewer tái kiểm được vì sao một finding đáng sửa, tác vụ nào cần thêm chứng cứ.

**Module và phụ thuộc.** [K-09](KNOWLEDGE_CARDS.md#k-09)/[K-10](KNOWLEDGE_CARDS.md#k-10). AIO-03/06/09, WF-21. Broker có receipt, rubric theo task, bộ holdout được đăng ký trước và ngân sách đã duyệt.

**Nghiệm thu.** Thêm ví dụ đã duyệt và counterexample, ghim revision thẻ vào run. Đánh giá có/không có thẻ trên cùng model, task và ngân sách. Báo kết quả đúng đồng thời kết luận, nguồn, lý do, đề xuất sửa; ghi false positives, unresolved và cost/finding. Không lấy fixture đã dùng viết thẻ làm holdout; lượt thiếu receipt không tính tham gia.

Khi lấy một mục vào sprint, chủ module ghi rõ base SHA, tiêu chí bắt buộc, bộ dữ liệu được phép, cách rollback và số đo trước/sau trong PR. Nếu đối chiếu thấy chức năng đã có, thêm fixture hoặc dẫn chứng vào ma trận và đóng đề xuất trùng. [Những giả thuyết đã loại hoặc hoãn](REJECTED_HYPOTHESES.md)

<a id="o-09"></a>

## O-09 · Làm rõ yêu cầu ngay trước khi bàn giao Sales hoặc Service

**Quyết định.** Ưu tiên đúng một câu hỏi nghiên cứu cho WF-14/WF-20. Khi nào hồ sơ đủ chuyển tiếp và khi nào tư vấn viên phải hỏi lại hoặc xin người có thẩm quyền? Chủ lợi ích là người nhận công việc và khách đang chờ được tư vấn. Người duyệt pilot là chủ quy trình Sales/Service. Tần suất lỗi, mức sẵn lòng trả, công lao động và giá trị mỗi lead trong doanh nghiệp vẫn chưa đo. [Nguồn và tình huống](KNOWLEDGE_CARDS.md#k-12) · [Ma trận vai trò](APPLICABILITY_MATRIX.md#nine-jobs)

**Điều kiện đầu vào.** Tận dụng AGY-01, AGY-06, MKT-13 và AIO-09. Brief được phép, điều khoản theo scope/revision, dữ liệu consent và rubric khóa trước. Trong lab chỉ dùng trường hợp tổng hợp. So baseline hiện hữu, quy tắc cải thiện và AI advisory trên cùng cohort mới. Đóng băng dữ liệu, nhãn, rubric và ngân sách trước inference, chỉ chạy model khi đủ quyền theo protocol. Mỗi đầu ra trả về quyết định, bằng chứng vì sao và một câu hỏi hoặc người có quyền cần xử lý. Không cấp công cụ thay đổi CRM, báo giá hoặc lịch. [Benchmark trước](../evaluation/department-study/advisory/HANDOFF-BENCHMARK.md) · [K-14](KNOWLEDGE_CARDS.md#k-14)

**Nghiệm thu nghiên cứu.** Cohort chứa ca thiếu, đính chính, hết hiệu lực, chưa rõ ý, mâu thuẫn thương mại, cần hỏi, cần người có thẩm quyền và đủ tiếp tục. Dùng control cùng ca để xác định lỗi nào giảm hoặc tăng. Báo riêng số hồ sơ bị báo đủ sai trong tất cả ca thực sự chưa đủ, hồ sơ đủ bị hỏi lại, trích dẫn sai, output thiếu và mẫu số mỗi nhóm. Kiểm thủ công ca rút điều kiện, trường còn giá trị cũ, cam kết có điều kiện và nhầm contact với người được duyệt. Chỉ xem xét đưa vào luồng tư vấn sau khi người nhận đánh giá mù, kiểm an toàn và lập quyết định riêng.

**Kinh tế.** Giai đoạn practitioner ghi theo từng việc được giao gồm phút sản xuất, biên tập, QA và đối soát, thời gian chờ tới lúc chấp thuận đầu ra, chi phí model/hạ tầng và quyết định chấp nhận hay trả lại. Chi phí trên việc được chấp nhận bằng tổng chi phí đầy đủ của *mọi* việc trong nhánh chia số việc thực sự được chấp nhận. Nếu mẫu số bằng 0 hoặc thiếu timesheet/đơn giá thì ghi “chưa xác định”. Đối chứng về luồng clarify có thể cải thiện chất lượng kỹ thuật ngay cả khi chưa xác định giá trị kinh tế. [Quy trình pilot hiện hữu](../../tests/evaluation/department/official_pilot.py)

**Các cơ hội còn lại.** Xếp sau O-09 là giảm công tìm bằng chứng cho thông điệp/creative và đối soát mẫu số trong báo cáo. Chỉ mở đầu việc nếu người chịu trách nhiệm nêu được quyết định thật, nguồn có quyền, lỗi lặp lại, thời gian đối soát ban đầu và tiêu chí nghiệm thu. Khi đó đánh giá tiếp trong O-05/O-06 hoặc luồng report đã có. Chín nhóm việc là bản đồ khảo sát, chưa phải chín hạng mục triển khai. [Năng lực hiện có](../evaluation/DEPARTMENT-CAPABILITY-REGISTER.md)
