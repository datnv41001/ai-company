# Marketing Studio cho bản hoàn tất WF-03 và WF-13

Từ **Phê duyệt → Soạn và bàn giao cho khách**, chọn bản làm việc rồi mở **Biên tập tài liệu Marketing**. Nhân viên cũng có thể mở tài liệu từ kết quả công việc của Đội ngũ AI.

| Workflow | Nhóm nội dung được lưu và duyệt |
| --- | --- |
| WF-03 research-strategy-draft@3 | Nghiên cứu người mua, chiến lược, kế hoạch đo lường |
| WF-13 landing-seo-draft@6 | Nội dung trang cho người mua, trường SEO |

Khi nhiệm vụ mới có hành động người mua được chọn rõ ràng, worker lưu các trường cùng lần tạo tài liệu và ghi nguồn `worker`. Với kết quả @3/@6 đã có trước Studio, nhân viên chủ động lưu đề xuất để bắt đầu lịch sử. Nhãn chỉnh sửa và đề xuất của model đều có thể cần người làm Marketing sửa lại. Dữ kiện thương mại dùng toàn bộ công bố đã ghim, gồm đơn vị, thuế, ngưỡng và điều kiện. Người dùng có thể lưu bản còn thiếu để tiếp tục biên tập.

## Quy trình Biên tập → QA → Bàn giao

1. Sửa tài sản trong Studio và lưu. Từng lần lưu tăng `qa_revision`, kể cả khi nội dung trùng bản trước. Xem bản trước trong **Lịch sử tài liệu**. Kết quả WF-03 gồm tài liệu nội bộ và bản xem trước công khai riêng. Với WF-13, bản xem trước được tạo từ nhóm nội dung trang, SEO chỉ hiển thị trong Studio.
2. Gửi bản làm việc sang QA. Người duyệt độc lập xem từng trường, đọc nguồn, ghi nhận quyết định chuyên môn khi có đủ thẩm quyền. Số liệu chưa khớp, điều kiện bị bỏ và claim bị cấm trả về cho biên tập. Một SKU đã biết có thể xuất hiện trong câu mới nhưng cần tiếp tục kiểm tra ý nghĩa của câu.
3. Người có vai trò owner/admin khác người tạo và người sửa cuối ký từng nhóm. Mỗi quyết định đối chiếu lại quyền, nguồn, revision và digest của chính nhóm đó. Khi toàn bộ nhóm đủ điều kiện, thực hiện QA chung và chia sẻ qua quy trình sẵn có. Lần lưu mới yêu cầu những chữ ký mới. Nội dung khách đã duyệt nằm trong snapshot của lần bàn giao.
4. Hệ thống gắn cảnh báo cấu trúc cho trường trống, CTA sai, trường lặp, trích dẫn thương mại thiếu và tiêu đề xa sản phẩm. Mức phù hợp với thị trường, sức thuyết phục và hiệu quả chuyển đổi vẫn cần được kiểm định bằng nghiệp vụ và dữ liệu thực tế.

## Hợp đồng HTTP

Cả ba thao tác dùng session nhân viên, tenant, campaign, brand và client của tài liệu thực. Viewer không đọc được tài liệu nội bộ, gồm hai khách trong cùng một agency.

- `GET /api/tenants/{tenant}/deliverables/{id}/studio` trả về `mode`, `workflow`, `revision`, `groups`, `preview`, lịch sử, tham chiếu đã công bố, findings, digest và chữ ký hiện hành của từng nhóm. `proposal` là trường gợi ý. `saved` là dữ liệu đã lưu. Các trường của `groups` là hợp đồng phiên bản `amc.marketing-studio/1`.
- `PATCH` cùng URL nhận `{"expected_revision": 2, "groups": {...}}`. Phải gửi đủ nhóm và khóa của hợp đồng. API trả 412 nếu revision cũ, 422 nếu cấu trúc không đúng.
- `POST .../studio/approvals` nhận `group`, `expected_revision`, `expected_asset_digest`, `note`. Trả 409 khi cần xác minh nguồn, chất lượng hoặc trạng thái, 412 khi bản xem đã cũ.

Nguồn chính là `app/c3_studio.py`, `app/c3_studio_routes.py`, `app/c3_content_evidence.py` và `app/c3_boundaries.py`. Các bản lưu và biên nhận dùng kho document, audit và scoped knowledge command của AMC. Khi phối hợp bản nâng cấp, chạy quy trình migration/giao thức trong HANDOFF và dùng runtime đã chốt cho core v25/module amc_c3 v2. Dùng dữ liệu tổng hợp để nghiệm thu.

## Kiểm chứng trên máy khác

Từ thư mục gốc, cài dependency kiểm thử như HANDOFF, rồi chạy:

```sh
python -m pytest -q tests/test_c3_studio.py tests/test_c3_content_gate.py
python -m playwright install chromium
python -m pytest -q tests/browser_marketing_studio.py
```

Biến `AMC_BROWSER_EXECUTABLE` chọn Chrome có sẵn, `AMC_STUDIO_EVIDENCE` chọn thư mục ảnh. Bài browser phát lại câu trả lời Qwen đã lưu của agency-01 và agency-02 trong `docs/evaluation/c3-holdout-v1/first-pass.jsonl.gz`. Một bản ghi JSON ghi checkout, model hash, run gốc, tài liệu và thời gian mở. Nhân viên đăng nhập, sửa qua HTTP và đọc bản đã lưu ở 1280/820/390 px, hai theme. Chỉ ghi nhận lượt suy luận mới khi có biên nhận của tiến trình model mới. Smoke PostgreSQL có thể gọi `capture_live(base_url, actor, run_id, workflow, output_dir)` trong `tests/browser_marketing_studio.py` để chụp chính kết quả vừa sinh, dùng tài khoản thử được cấp quyền sửa. Hàm lưu ảnh và receipt đã loại credentials.

Để tái lập đánh giá tự động, dùng `compose(workflow, projection, checkpoints={})` cho nhóm baseline đúng cùng manifest và `compose(workflow, projection, checkpoints)` cho nhóm có model hỗ trợ. Hai nhóm cần được chấm bằng tiêu chí giống nhau. Commercial GA vẫn NO-GO.
