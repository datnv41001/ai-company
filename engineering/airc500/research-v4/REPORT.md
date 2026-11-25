# Holdout năng lực Marketing với nguồn công khai · v4

Mười ca mới, một reviewer MK-022, Qwen2.5-1.5B-Instruct Q4_K_M chạy native trên Windows. Một agent khác tác giả bộ ca gán nhãn độc lập trước inference. Cùng agent này chấm 20 câu trả lời tự do sau khi đã ẩn arm và điểm số. Đây là đối chiếu do AI thực hiện, chưa có người chấm nghiệp vụ độc lập.

| Chỉ số | Chỉ có bibliography | Có thêm packet | Gain / loss theo ca |
|---|---:|---:|---|
| Đúng verdict (flag, keep, insufficient) | 2/10 | 2/10 | L10 / L8 |
| Chọn đúng họ nguồn từ bibliography | 2/10 | 5/10 | L10, L3, L4 / ∅ |
| Chọn nguồn đúng thực sự có trong context | 0/10 | 5/10 | L1, L10, L2, L3, L4 / ∅ |
| Khớp nguyên văn mẫu sửa | 0/10 | 0/10 | ∅ / ∅ |
| Lý do đúng phạm vi (chấm mù) | 1/10 | 1/10 | ∅ / ∅ |
| Quy kết nguồn hợp lệ (chấm mù) | 1/10 | 3/10 | L2, L4 / ∅ |
| Khuyến nghị có thể dùng trong ca (chấm mù) | 3/10 | 4/10 | L10, L3, L8 / L1, L7 |

Trong bốn claim phải flag, arm đối chứng phát hiện 0/4 (∅); arm có packet phát hiện 1/4 (L10). Cờ sai lần lượt là 0 và 1. Các claim được flag đúng đồng thời có đề xuất hữu ích lần lượt là ∅ và L10.

| Năng lực trong arm có packet | Ca có verdict đúng và đạt tiêu chí / đã đo | Kết luận |
|---|---:|---|
| Lập luận Marketing | 1/10 | Mẫu nhỏ |
| Quy kết đúng nguồn | 0/10 | Mẫu nhỏ |
| Claim sai hoặc khẳng định thiếu căn cứ | 1/4 | Mẫu nhỏ |
| Phạm vi tính năng sản phẩm | 0/2 | Mẫu nhỏ |
| Logic mã nguồn | 0/0 | Chưa đo |
| Phân tích bảo mật và hồi quy | 0/0 | Chưa đo |
| Hành động hữu ích cho claim sai | 1/4 | Mẫu nhỏ |

| Arm | Call đã ký | Input token | Output token | Chi phí provider |
|---|---:|---:|---:|---:|
| without | 5 | 1451 | 543 | 0 |
| with | 5 | 1831 | 538 | 0 |

Các nguồn thực sự truy xuất được và giới hạn của chúng:

- G · first-party platform rule. Platform definition for GA4 default engagement. Confirm the property configuration separately. [Google Analytics Help](https://support.google.com/analytics/answer/12195621?hl=en)
- W · first-party product description. First-party description of core grouped products. Extensions or shop-specific restrictions can differ. [WooCommerce](https://woocommerce.com/document/managing-products/)
- S · unverified anecdote. A single self-selected merchant request. Use as a question to investigate, never as proof about another merchant. [Shopify Community](https://community.shopify.com/t/sell-products-with-minimum-quantity-and-increment-quantity-with-fixed-number-of-units/39933)
- H · unverified anecdote. One participant's retrospective experience, without verified measurements. Cannot establish an effect for a client or a population. [Hacker News](https://news.ycombinator.com/item?id=41679891)
- Gap C · Unexpected response status, type or encoding (403).
- Gap E · Unexpected response status, type or encoding (403).
- Gap F · The read operation timed out.

Hai ca L5/L6 về thị trường không nhận trích đoạn ở cả hai arm. Prompt chấm giữ nguyên. ID nguồn trên bibliography có thể được chọn kể cả khi chưa đọc trang. Điểm quy kết được chấm theo lời giải thích và phạm vi nguồn. Không cộng một citation chưa truy xuất vào độ phủ nguồn.

Tần suất phát hiện và khuyến nghị hữu ích là số liệu mô tả trên những ca này. Cùng một model và một seed, hai ca tương quan trong từng call. Mức tăng hoặc giảm trên một cặp không xác lập hiệu quả ngoài holdout. Chưa có căn cứ để mở rộng số reviewer, bật review source thực hay thay đổi commercial GA.

[Kết quả từng ca và ma trận nhầm lẫn](results.json) · [Nhãn trước inference](independent-labels.json) · [Phiếu chấm prose đã làm mù](semantic-grades.json) · [Hướng dẫn sử dụng và các gate](../PUBLIC-RESEARCH.md).

Enrollment SHA-256 `0ad84af4a344e25a1b493835f3072dc1f3e55f0d8a9b6b32b195378bb6cc4fba`. Archive SHA-256 `90821852eb36d40e2ae9c96def75dd2dc0d086fe383e0279aaebba04f65d6503`. Semantic grades SHA-256 `42593a7167d970ba0fb15fa1a8aa32d13afa182a3d55d2572e18467ba3ae2b2f`.
