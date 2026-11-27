# WF-08/2 semantic review matrix

Every cell comes from a signed synthetic brief through the PostgreSQL queue, the scoped editor, submission and independent QA. Each side is a separate database run; compare wording and within-run receipts. Both original and edited content revisions received approval. The matched RED assertions document why approvals on the historical wording were insufficient.

| Action | Style | Reviewed opening | Reviewed alternate | Corrected opening | Corrected alternate | CTA |
|---|---|---|---|---|---|---|
| rfq | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn cần báo giá gì? | Hỏi báo giá cần chuẩn bị gì? | Yêu cầu báo giá |
| rfq | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Cần báo giá? | Hỏi báo giá cần gì? | Yêu cầu báo giá |
| rfq | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị cần báo giá? | Quý vị muốn hỏi báo giá nào? | Yêu cầu báo giá |
| rfq | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình cần báo giá gì nhỉ? | Mình xem gì trước khi hỏi báo giá? | Yêu cầu báo giá |
| appointment | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn muốn hẹn lúc nào? | Bạn cần biết gì trước khi hẹn? | Gửi đề nghị khảo sát |
| appointment | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Hẹn khi nào? | Cần gì trước khi hẹn? | Gửi đề nghị khảo sát |
| appointment | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị muốn đề nghị lịch hẹn nào? | Quý vị cần biết gì trước khi hẹn? | Gửi đề nghị khảo sát |
| appointment | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình muốn hẹn khi nào nhỉ? | Mình xem gì trước khi hẹn nhé? | Gửi đề nghị khảo sát |
| choose_session | plain | Cần kiểm tra điều gì? | Hãy xem điều kiện trước. | Bạn muốn chọn buổi nào? | Buổi nào hợp với bạn? | Chọn buổi |
| choose_session | concise | Kiểm tra đâu trước? | Báo giá cần gì? | Chọn buổi nào? | Buổi nào phù hợp? | Chọn buổi |
| choose_session | formal | Quý vị cần đối chiếu gì? | Quý vị cần báo giá? | Quý vị muốn chọn buổi nào? | Buổi nào phù hợp với quý vị? | Chọn buổi |
| choose_session | friendly | Mình cùng xem nhé? | Mình xem điều kiện nhé? | Mình chọn buổi nào nhỉ? | Buổi nào hợp với mình nhỉ? | Chọn buổi |

## Explicit quote-condition instruction

| Signed conversion | Old angle | Current angle | Current hook | QA (old → current HTTP) |
|---|---|---|---|---|
| appointment | quote_conditions | commercial_conditions | Quý vị muốn đề nghị lịch hẹn nào? | 200 → 200 |
| choose_session | quote_conditions | show_evidence | Quý vị muốn chọn buổi nào? | 409 → 409 |
