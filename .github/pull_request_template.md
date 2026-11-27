## Mục tiêu và quyết định

1. **Mục tiêu.** Ai giao việc, AMC đảm nhiệm bước nào, ai dùng đầu ra và tiêu chí chấp nhận là gì?
2. **Trước thay đổi.** Mô tả hành vi quan sát được, bằng chứng ban đầu và ảnh hưởng.
3. **Base.** Nhánh, SHA đầy đủ, schema hoặc hợp đồng liên quan.
4. **Phương án.** Lý do chọn, phương án đã thử hoặc loại, trade-off và điều có thể làm thay đổi quyết định.
5. **Nguồn đã dùng.** Link nguồn trong/ngoài repo, ngày, phiên bản và quyền dùng lại nếu áp dụng.

## Thay đổi và nghiệm thu

6. **File thay đổi.** Liệt kê theo chức năng hoặc liên kết diff bất biến có danh sách file.
7. **Đã hiện thực.** Entry point, vai trò, phạm vi dữ liệu, hành vi trước/sau và mức bằng chứng.
8. **Chưa hiện thực.** Nêu phần còn mở trong phạm vi và dependency.
9. **Kiểm thử thực tế.** Lệnh tái lập, môi trường, fixture, đạt/trượt/skip, nguyên nhân và artifact. Giữ kết quả lần đầu khi sửa lỗi.
10. **Đầu ra nghiệp vụ.** Link bản giao, revision, quyết định của người nhận và số đo chất lượng, công sức, thời gian, chi phí so với baseline. Ghi rõ chỉ số chưa đo và phép thử tiếp theo. [Chuẩn nghiệm thu](../docs/PRODUCT_MISSION.md)
11. **Hạn chế, rủi ro, rollback.** Dữ liệu, quyền hạn và lịch sử bị ảnh hưởng, cách phục hồi và cách xác nhận sau phục hồi.
12. **Tài liệu.** Mục có trách nhiệm trong HANDOFF, ADR, đặc tả, runbook, nguồn hoặc báo cáo đã cập nhật cùng PR.

## Bàn giao cho người phản biện

Ghi verdict, người đánh giá, phạm vi, SHA và lý do. **PASS** đủ tiêu chí đang xét. **PASS_WITH_CONDITIONS** chỉ rõ điều kiện, owner và hạn kiểm lại. **CHANGES_REQUIRED** có sai lệch phải sửa. **BLOCKED** có dependency hoặc quyền cản trở phép kiểm. **NOT_VERIFIABLE** thiếu bằng chứng để kết luận. Với lịch sử, “PASS nội bộ” áp dụng cho phạm vi đã ghi; đọc nguyên nhân của “HOLD” để chọn sửa lỗi, gỡ blocker hoặc thu bằng chứng. Giữ nguyên verdict gốc. Ghi riêng từng quyết định cho internal merge, production và Commercial GA.

13. **Phiên bản được review.** Head SHA, PR, link CI và SHA tích hợp. Khi đã merge, bổ sung merge SHA và CI trên main. Dẫn tới tệp bằng chứng nằm trong repository khi artifact CI có thời hạn.
14. **Việc tiếp theo.** Xếp ưu tiên theo giá trị và dependency, nêu người phụ trách và bằng chứng hoàn thành.
15. **Câu hỏi cho ChatGPT Independent Reviewer.** Chỉ ra giả định, phép thử đối chứng và bất đồng chưa giải quyết. Ghi lại phản hồi của Codex, bằng chứng và quyết định của đúng người có thẩm quyền.

Với thay đổi frontend, đính kèm ảnh thật desktop/tablet/mobile, light/dark, bằng chứng bàn phím, focus, độ tương phản, reflow, reduced motion và hiệu năng trong điều kiện đã đo. [AMC Design System](../docs/AMC-DESIGN-SYSTEM.md). Với mục không áp dụng, nêu lý do ngắn.
