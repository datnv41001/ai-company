# Chứng nhận main sau PR #70

**PASS nội bộ cho WF-06/product-use-guide@1.** Người nhận in-house có thể tạo guide qua Content worker, sửa bản và trình Independent Content QA trên nguồn đủ thẩm quyền. [PR đã merge](https://github.com/datnv41001/ai-company/pull/70) · [CI trên main](https://github.com/datnv41001/ai-company/actions/runs/46150710378)

| Đối tượng | Git SHA |
|---|---|
| Main | [3d56073fafeb9d5bd5f39843fc74e11bc378fdab](https://github.com/datnv41001/ai-company/commit/3d56073fafeb9d5bd5f39843fc74e11bc378fdab) |
| Parent 1 | [1ae4dc24dcae20c13d64f6dfaf887a03af48e6e3](https://github.com/datnv41001/ai-company/commit/1ae4dc24dcae20c13d64f6dfaf887a03af48e6e3) |
| Parent 2, head đã duyệt | [d4c05dd2c681a367fdee0b6b94f687c0fca866bd](https://github.com/datnv41001/ai-company/commit/d4c05dd2c681a367fdee0b6b94f687c0fca866bd) |
| Trial merge đã duyệt | [d8de0a68654b29e5d24e494b51036f5f4f7034a5](https://github.com/datnv41001/ai-company/commit/d8de0a68654b29e5d24e494b51036f5f4f7034a5) |
| Tree của head, trial và main | `85a92d483ce84c72b243b1f49b7579f3ea737258` |

Diff có 81 tệp gồm cả manifest. Đã đọc lại 80 blob từ URL GitHub theo merge SHA, đối chiếu độ dài và SHA-256 từng tệp. Manifest SHA-256 `94531c63e4fd828cc48bc7a45c66f6ca589d75b0ec68b96f165b188cea86c23f`. [Manifest theo merge](https://github.com/datnv41001/ai-company/blob/3d56073fafeb9d5bd5f39843fc74e11bc378fdab/docs/evaluation/product-guide/MANIFEST.json)

Workflow push attempt 1 đạt 3/3 job bắt buộc. API ghi 824 đạt và 2 skip. Chromium guide đạt 1/1. PostgreSQL nâng 22 baseline lên core v26; bản restore khớp 34 bảng, bốn guide và guard thẩm quyền. [JUnit](https://github.com/datnv41001/ai-company/actions/runs/46150710378/artifacts/15266831052) · [Ảnh và receipt](https://github.com/datnv41001/ai-company/actions/runs/46150710378/artifacts/15266895817) · [Log migration/restore](https://github.com/datnv41001/ai-company/actions/runs/46150710378/job/140996536379)

Campaign trong job Qwen có 34/38 stage đạt ở lần đầu, 1 lần thử lại trong runtime, 11243 token vào và 3482 token ra. Outcome {"invalid_source": 1, "ok": 35, "recipient_revoked": 3}; 3 usage chưa xác nhận. Các journal theo run ID và bài thử hai slot có phạm vi riêng. Phí model provider được ghi trong journal là 0 USD; chi phí runner thực trả chưa có số đo. [Receipt, outcome, thời lượng job và liên kết artifact](main-ci.json)

Phạm vi main dừng ở QA nội bộ với worker replies có kiểm soát trong lát cắt guide. Job Qwen chung của Workforce không cung cấp nhãn practitioner, số phút editor tiết kiệm hoặc kết quả kinh doanh. Production và Commercial GA vẫn NO-GO.
