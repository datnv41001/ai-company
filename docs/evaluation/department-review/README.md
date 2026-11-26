# Nghiệm thu liên phòng ban trong sandbox

**Mốc lịch sử của bảng dưới là head `c5c63295`.** Tại mốc này, khách dưới MOQ được ghi nhận nhưng chưa có đường giao hồ sơ đó cho Sales tư vấn. Chỉ số `qualified_quotes` khi ấy đếm hồ sơ đủ điều kiện. Bộ alias pilot công khai là fixture. Xem [vòng sửa tiếp theo của PR #55](REVIEW-55-FOLLOWUP.md) khi nghiệm thu luồng tư vấn, chỉ số phát hành báo giá hoặc chấm bản nháp đầu.

Người phụ trách chiến dịch cần biết đề xuất tối ưu đang dùng số liệu của kế hoạch nào. Sales và Service cần nhận đúng dữ liệu mà nội dung Marketing đã yêu cầu khách cung cấp, theo quyền được giao tại thời điểm xử lý. Người ký QA cần biết khi nào bộ kiểm tra có thể gắn cờ sai và khi nào vẫn phải đọc nguồn. Đây là ba công việc được kiểm định trong vòng này.

| Finding | Quyết định và cách kiểm tra |
|---|---|
| AMC-R49-01 | Chấp nhận P1. Ca hai kế hoạch tái hiện một lịch hủy làm sai đề xuất RFQ. Xem cửa sổ đo, nguồn, trường hợp đề xuất cũ và ảnh 390/820/1280 px trong [biên bản trước và sau sửa](../optimization-scope/README.md). |
| AMC-R50-01 | Chấp nhận yêu cầu kiểm định. Đã chạy API tiền nhiệm và Role Desk trên cùng PostgreSQL hạn quyền. Quyền theo vai trò, theo tổ chức và điều kiện của giao dịch được kiểm tại thời điểm ghi hoặc đọc lại receipt. [Ma trận đường ghi và ca tranh chấp](AUTHORITY.md) |
| AMC-R51-01 | Chấp nhận P1. Dùng hợp đồng intake từ kế hoạch đã duyệt để nối nội dung, biểu mẫu, đồng ý liên hệ, dữ liệu giao Sales/Service và chỉ số. Xem các bộ RFQ, Luồng Rõ, bơm, điều kiện MOQ, tương thích writer và rollback trong [biên bản intake](../business-intake/README.md). |
| AMC-R52-01 | Chấp nhận khoảng trống về ngữ nghĩa. Đánh giá một lượt Qwen cục bộ trên từng claim sau khi khóa prompt. Dùng cả phát hiện đúng, báo sai, bỏ sót và trường hợp chưa kết luận để quyết định quyền của AI. [Kết quả và cách chạy lại](../department-study/advisory/REPLAY.md) |
| AMC-R52-02 | Chấp nhận yêu cầu chứng minh giá trị chuyên môn. Hai brief tổng hợp, sáu vai trò, đầu ra từng phương án, rubric chấm mù và phiếu pilot nằm trong [nghiên cứu chuyên môn](../department-study/advisory/SPECIALISTS.md) và [hướng dẫn pilot](../department-study/PILOT.md). |

## Phiên bản, phạm vi và người tiếp quản

Nhánh tích hợp bắt đầu từ head PR #54 `eff86cda2f99dd10244dc8127451e941bb546a3c`. Chuỗi sản phẩm là #49 → #50 → #51 → #52 → #54. Head và base của từng nhánh, cây tích hợp cùng hai lượt CI đã đối chiếu được lưu trong [baseline.json](baseline.json). PR #53 về quản trị tri thức có quyết định review riêng tại `56a120ca`. [Knowledge Map](https://github.com/datnv41001/ai-company/blob/56a120cac4bb3f77a4e1fc6fe93298cc838121ea/docs/KNOWLEDGE_MAP.md) · [PR #53](https://github.com/datnv41001/ai-company/pull/53)

Để tái chạy trên máy khác, checkout **head SHA trong biên nhận**, khởi tạo cấu hình phát triển bằng `python scripts/init_env.py`, rồi theo [runbook Docker](../../../HANDOFF.md) và từng lệnh trong năm biên bản trên. Artifact của mỗi lượt CI phân biệt bản head và bản ghép thử bằng SHA checkout. Đối chiếu SHA và tree khi đánh giá. Các receipt, CI và nhận xét của người tiếp quản trên bản cuối được lưu riêng để kết quả kiểm thử không làm thay đổi cây mã đã kiểm. [Biên nhận bản tích hợp và cold handoff](https://github.com/datnv41001/ai-company/tree/evidence/department-closure-20261126/docs/evaluation/verification)

Phạm vi V1 gồm 49 module, 37 vai trò và 24 workflow. Xem [Product Mission](../../PRODUCT_MISSION.md), [đặc tả sản phẩm](../../PRODUCT_SPEC_V1.md), [trạng thái theo năng lực](../DEPARTMENT-CAPABILITY-REGISTER.md) và [release gates](../../SECURITY_AND_GA_BLOCKERS.md). Dữ liệu dùng ở vòng này là tổng hợp, số người hành nghề tham gia pilot là 0. Commercial GA **NO-GO**. Người có thẩm quyền giữ quyết định merge và phát hành.

## Gói đã bàn giao giữa các máy

| Gói | SHA-256 khi tải |
|---|---|
| [89 tệp chiến dịch tổng hợp](https://github.com/datnv41001/ai-company/raw/d320f7fe4d0588238a84320832780e31a0c7e8d4/docs/evaluation/downloads/AMC-rendered-campaigns.zip) | `cedc1b9cfe73a18d85b018b03e61bfb31e4bdd1d3eebf1bd45082e22f287604f` |
| [Bằng chứng review của vòng trước](https://github.com/datnv41001/ai-company/raw/d320f7fe4d0588238a84320832780e31a0c7e8d4/docs/evaluation/downloads/AMC-review-evidence.zip) | `461c72455ae7f4d59ddc3a2fbecfdfd8fa06e9d1bb4c92edae0e8573791be08b` |

Gói render giữ nguyên từng byte. Trong gói review, XML chia sẻ giữ tên ca, thời gian và kết quả, gồm lần chạy đầu thất bại. Hostname và đường dẫn máy đã được lược bỏ. File chỉ mục lưu hash XML gốc để đối chiếu với GitHub Actions. Cả hai ZIP đã được tải lại từ GitHub và kiểm SHA-256.

## Câu hỏi cho reviewer

- Một hồ sơ dưới MOQ có thể đủ thông tin cho Sales tư vấn. Tiêu chí nào được ghi trong brief để phân biệt nhu cầu tư vấn, yêu cầu đủ điều kiện báo giá và quyền đặt hàng?
- Khi một sự kiện đến trễ sau khi khóa đề xuất, hãy thử đọc lại biên nhận cũ, rồi thử duyệt đề xuất chưa ký. Người xem có giải thích được vì sao cần tạo bản mới?
- Khi kiểm định trên dữ liệu Việt/Anh khác hai brief tổng hợp, mức báo sai và thời gian chuyên gia phải sửa có đủ thấp để đưa AI vào quy trình QA thường ngày?
