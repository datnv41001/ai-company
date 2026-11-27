# Research → Strategy · Independent Review

Head `9f33fd86f99da52a90c25aa5ec196ba601b3910f` · base `6a11bf4d97e7d1be1f5e0da1d503a54eabd15ad1` · trial `85d2235f5f03330a5ea02b83211ca0e7423b054b` · tree `a63361c7673ada6121117028f92aebcb3b8aecd1`.

[Hồ sơ đầy đủ trên candidate](https://github.com/datnv41001/ai-company/blob/9f33fd86f99da52a90c25aa5ec196ba601b3910f/docs/evaluation/round63/README.md). Hai brief tổng hợp, decoder cố định, cùng inputs cho bản trước và sau. Mỗi cặp JSON đã khớp digest trên ba checkout CI và Windows. Đây là đánh giá kỹ thuật. Chưa có practitioner UAT.

| Công việc | Baseline đã phát hành | Bản giao nội bộ | Hướng đề xuất | Content |
|---|---|---|---|---|
| route-shift | [Trước](cases/route-shift/before.json) | [Sau](cases/route-shift/after.json) | handoff | [draft_for_approval](cases/route-shift/WORK-ORDER.md) |
| studio-first-visit | [Trước](cases/studio-first-visit/before.json) | [Sau](cases/studio-first-visit/after.json) | first_visit | [hold](cases/studio-first-visit/WORK-ORDER.md) |
| route-storekeeper | [Trước](cases/route-storekeeper/before.json) | [Sau](cases/route-storekeeper/after.json) | audit | [hold](cases/route-storekeeper/WORK-ORDER.md) |
| route-corrected-observation | [Trước](cases/route-corrected-observation/before.json) | [Sau](cases/route-corrected-observation/after.json) | audit | [hold](cases/route-corrected-observation/WORK-ORDER.md) |
| route-disagreement | [Trước](cases/route-disagreement/before.json) | [Sau](cases/route-disagreement/after.json) | conflicting_evidence | [hold](cases/route-disagreement/WORK-ORDER.md) |
| route-withdrawn-channel-expired-measure | [Trước](cases/route-withdrawn-channel-expired-measure/before.json) | [Sau](cases/route-withdrawn-channel-expired-measure/after.json) | handoff | [hold](cases/route-withdrawn-channel-expired-measure/WORK-ORDER.md) |
| studio-clarify | [Trước](cases/studio-clarify/before.json) | [Sau](cases/studio-clarify/after.json) | needs_clarification | [hold](cases/studio-clarify/WORK-ORDER.md) |
| studio-unrepresented | [Trước](cases/studio-unrepresented/before.json) | [Sau](cases/studio-unrepresented/after.json) | insufficient_evidence | [hold](cases/studio-unrepresented/WORK-ORDER.md) |
| studio-foreign-record | [Trước](cases/studio-foreign-record/before.json) | [Sau](cases/studio-foreign-record/after.json) | first_visit | [hold](cases/studio-foreign-record/WORK-ORDER.md) |

[Đầu vào và output digest](cases/index.json) · [Phản biện và hồi quy](review/CHALLENGE.md) · [Checkpoint Qwen cũ](review/ARCHIVED-WF03.json) · [Kết quả CI](ci.json) · [Chi phí và phạm vi đo](model-resources.json) · [Danh mục](files.json).
