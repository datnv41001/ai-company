# Xác minh AMC-R57-01

Reviewer kỹ thuật Codex độc lập đã đọc Git objects trước và sau, rồi chạy các ca API tại checkout tách riêng. Main có byte `6d c2 b2`. Head cũ `73c1c04e7db6501979696c63b72d948171d957cb` có `6d c3 82 c2 b2`. Head sửa `eb60d93fe3fec2f419fb621d5ac82ad4c7142c02` khôi phục byte gốc.

RED trên SQLite: hai fail, hai pass, bảy ca ngoài bộ lọc, 14,87 giây. RFQ và CompleteRFQ đều trả 409 cho 12.375 m², trong khi tonne/kg đạt đối chứng. GREEN tại head sửa: sáu đạt, năm ca PostgreSQL ngoài bộ lọc, 33,76 giây. Hai API trả 200 và đúng revision, detail, đơn vị, quantity. Từ chối unit hỏng không tạo dòng. Rà diff đã thêm trên head cũ có một hit trong 6.027 dòng; head mới 0 hit trong 6.150 dòng theo cùng mẫu. Entry runtime cũ được giữ, hai fingerprint mới đối chiếu được. Khuyến nghị kỹ thuật đóng P1 khi CI head và integration đều đạt. PostgreSQL trong JUnit RED/GREEN do nhóm thực hiện chạy; phiên reviewer này tự chạy SQLite.

[Diff sửa và JUnit gốc](https://github.com/datnv41001/ai-company/blob/eb60d93fe3fec2f419fb621d5ac82ad4c7142c02/docs/evaluation/department-review/R57-MATERIAL-UNITS.md)
