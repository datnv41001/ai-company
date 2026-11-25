# Nghiệm thu sản phẩm Marketing sau C3

Bộ 50 brief v1 cùng mọi output, nhãn AI và phiếu mù được giữ làm hồi quy. Vòng mới đóng băng 10 brief tổng hợp, một ca cho mỗi tổ hợp gồm năm nhóm khách và hai workflow. Commit khóa bộ đề `3b37b06d52ce796dc9d7e2bc04e2fbb3e5421428`, SHA-256 nội dung LF `993f93551657734fbea73f6c8898633a18df9dd573fcd0ff78b5e01653bc3346`. Những người triển khai Studio và luồng sửa đơn vị sử dụng dữ liệu phát triển riêng. Tách mười nhiệm vụ này khỏi các ca dùng để sửa prompt. Khi đã đọc kết quả, các lần chạy tiếp theo trên cùng dữ liệu được gọi là hồi quy.

## Đối chứng theo thành phần

| Nhóm | Giữ cố định | Phép đo |
| --- | --- | --- |
| Composer tất định | Projection đã duyệt, locale, ngành và CTA | Lưu các trường, finding và số lượt gọi model bằng 0 trước khi chạy Qwen. |
| Qwen hiện tại với skill lịch sử @2/@5 | Cùng brief, facts thương mại, model và weights | Chạy thực qua dispatcher, ghi output và token. Hợp đồng historical có cách chiếu dữ liệu riêng nên chênh lệch toàn workflow có nhiều nguyên nhân. |
| Qwen với skill hiện tại @3/@6 và composer | Cùng projection với bản tất định | Lưu checkpoint gốc, bản hoàn chỉnh, phiên bản biên tập, QA theo trường, lịch sử và chi phí. Đối chiếu bản tất định với bản thêm đề xuất của chính lượt chạy này. |
| Tách riêng tác động chỉ dẫn chuyên môn | Giữ cùng câu hỏi từ role, schema JSON, facts, model, composer và các checkpoint khác | Với một role chính của mỗi brief, thực hiện thêm tối đa một lần suy luận loopback bằng chỉ dẫn chung. Lưu digest yêu cầu, đầu ra, token và bản sau kết hợp. Đây là so sánh chỉ dẫn của một role, có thể chịu dao động model. |
| Model mạnh hơn | Giữ nguyên bộ input, skill, schema và composer | Chỉ chạy trên máy đã đủ RAM cho weights và KV cache, đã xác nhận giấy phép, runtime, context và ngân sách. Tới khi có receipt, ghi trạng thái chưa đo. |

Từng mẫu ghi thời gian máy kể từ khâu chuẩn bị nhiệm vụ đến khi lưu bản chỉnh sửa thử nghiệm. Thời gian mô hình được tách riêng. Đo tổng công việc bằng đồng hồ của người thực hành từ khi nhận brief đến khi chấp nhận bản hoàn thiện. Phân riêng phút hỏi lại, sửa dữ liệu thương mại, soạn, tìm nguồn và QA, bao gồm cả brief không tạo được bản. Mọi tỷ lệ cần có mẫu số. Trạng thái sẵn sàng kỹ thuật, số trường điền đủ và điểm tự đánh giá của AI đều chưa xác nhận mức dùng ngay của chuyên viên.

## Chạy lại trên máy khác

Dùng môi trường `workforce-model` trong CI với PostgreSQL thử nghiệm, publisher, loopback llama.cpp và đúng file weights. Mỗi lệnh tạo một thư mục mới. Chạy tuần tự.

```sh
python tests/evaluation/c3/qualification.py smoke-historical
python tests/evaluation/c3/internal_qualification.py smoke-internal
python tests/evaluation/c3/internal_qualification.py frozen-results --study
```

Smoke lịch sử dùng hai release @2/@5. Smoke nội bộ dùng hai release @3/@6 và đủ bảy digest kỹ năng của hai workflow. Các ca tạo workspace, nhiệm vụ và hướng dẫn qua API, chạy worker giới hạn quyền, lưu bản gốc, nội dung đã sửa và QA hiện hành. Artifact chỉ dùng dữ liệu tổng hợp. Các kết quả mới cần gắn SHA chạy, weights và checkout trước khi dùng để ra quyết định.

## Căn cứ cho người chấm

### Hồi quy sau khi mở bộ đề

Lượt smoke sau nghiên cứu ghi nhận Qwen có thể sinh cùng một cặp chỉ dẫn hỏng cả ba lần. Cụ thể, chuỗi thứ hai còn dưới 24 ký tự sau khi bỏ khoảng trắng cuối. Với task intent v2, yêu cầu Director hiện đưa hai lựa chọn nghiệp vụ vào JSON Schema cho mỗi vai trò được workflow cho phép. Model chọn chỉ dẫn, bộ biên dịch tiếp tục kiểm tra nhiệm vụ và thứ tự phụ thuộc. Giao thức task cũ vẫn đọc được các assignment đã lưu.

Trong cùng môi trường Qwen/PostgreSQL nêu trên, chạy `python tests/evaluation/c3/internal_qualification.py director-replay --director-regression` để kiểm tra lại v2-05, v2-07 và service-05. Các kết quả lần đầu vẫn nằm trong [hồ sơ nghiên cứu](c3-product-v2/RESULTS.md). Mỗi bản ghi mới đánh dấu hồi quy sau nghiên cứu, lưu checkout, phí, nội dung và quyết định của worker. CI integration của PR #38 lưu chúng trong thư mục `c3-director-regression` của artifact model.

- Xem CTA có khớp với hành động được ủy quyền và định nghĩa KPI hay không. Chẳng hạn yêu cầu báo giá là lead, còn giao dịch mua có bước ghi nhận riêng. Hướng dẫn chính thức của nền tảng được đọc ngày 25/11/2026. [Sự kiện GA4](https://developers.google.com/analytics/devguides/collection/ga4/reference/events)
- Chấm xem mô tả SEO có tóm tắt được nội dung trang, có căn cứ và giúp người mua chọn bước tiếp theo. Google có thể lấy snippet từ nội dung trang. [Google Search Central](https://developers.google.com/search/docs/appearance/snippet)
- Giữ nguồn gốc, tách ghi chú diễn giải, cho phép tra lại tại từng quyết định biên tập. Ý tưởng tổ chức kho tham khảo đến từ bài viết công khai của Trần Quốc Huy, có liên kết video đi kèm. Đợt này đọc phần văn bản. [Wecommit](https://www.wecommit.com.vn/bai-viet/second-brain-voi-agentic-ai-va-obsidian)

Bộ pilot trước vẫn dùng đúng mã, đúng thứ tự mù và khóa đã phân công. Với phiếu cũ, lưu phần hỏi lại và sửa dữ liệu trong phụ lục theo mã nhiệm vụ, tránh tính hai lần phần đã gộp vào thời gian biên tập. Giữ phiếu gốc và ý kiến bất đồng. Một brief mỗi tổ hợp chỉ phù hợp cho thăm dò. [Pilot chuyên viên](C3-PRACTITIONER-KIT.md)
