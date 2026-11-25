<!-- BEGIN AMC GENERATED QUALIFICATION -->
# Nghiệm thu nội bộ C3 Marketing Studio

**Quyết định sản phẩm: giữ phạm vi nội bộ.** Trên tám brief có cả hai bản để chấm mù, hai agent chuyên môn đánh giá 0/8 bản Qwen 0.5B và 2/8 bản tất định có thể dùng ngay. Mỗi bài được một agent đọc. Chưa có phiếu của người làm Marketing. [Phiếu, lý do và khóa sau chấm](AI-DESK-REVIEW.md)

Trong ca v2-04, hai model nhận cùng yêu cầu Content. Bản 0.5B cam kết hoàn thiện đúng thời hạn. Bản 7B gọi sản phẩm là “chất lượng cao” và “giá tốt”. Nguồn của ca này xác nhận lớp phủ mờ, địa bàn và điều kiện giá. Đây là ví dụ cụ thể về rủi ro ở phần biên tập ngay cả khi bảng giá khớp nguồn. Qwen 7B đã thực sự chạy 8 lượt, hai ca còn lại thiếu yêu cầu cùng vai trò do Director dừng trước đó.

**Công việc kế tiếp.** Giữ ba ca `invalid_plan` làm hồi quy của Director, gồm v2-05, v2-07 và service-05. Mỗi ca dừng sau ba lần thử. Khi cải tiến hướng dẫn, dùng bộ phát triển riêng và lưu source cho từng lợi ích, giả thuyết hoặc cam kết sinh thêm. Chỉ chấm lại khả năng dùng ngay và thời gian lao động trên bộ đối chứng mới với chuyên viên tham gia. [Giao thức](../C3-PRODUCT-QUALIFICATION.md)

Bản tích hợp [`a2dbe4566415fe28226b014ffb8785a1cc2cd9d6`](https://github.com/datnv41001/ai-company/commit/a2dbe4566415fe28226b014ffb8785a1cc2cd9d6) · [GitHub Actions #45582688602](https://github.com/datnv41001/ai-company/actions/runs/45582688602) · [Tải artifact gốc](https://github.com/datnv41001/ai-company/actions/runs/45582688602#artifacts).

## Phạm vi đo

| Nhóm | Có biên nhận / giao | Bản sinh | Đã sửa, QA đúng revision | Trạng thái run | Trung vị hành trình (giây) |
| --- | --- | --- | --- | --- | --- |
| Nghiên cứu giữ kín | 10/10 | 8 | 8 | awaiting_qa 8, failed 2 | 20.94 |
| Khôi phục đơn vị | 20/20 | 19 | 19 | awaiting_qa 19, failed 1 | 17.87 |
| Luồng nội bộ | 2/2 | 2 | 2 | awaiting_qa 2 | 28.54 |

Tình trạng thu thập 10/20/2: **đủ biên nhận theo hợp đồng**. Một lần sinh thành công đưa bản nháp đến QA. Phê duyệt chuyên môn, hiệu quả chiến dịch, thời gian lao động thực tế và Commercial GA chưa được xác lập.

Tập mới SHA-256 `993f93551657734fbea73f6c8898633a18df9dd573fcd0ff78b5e01653bc3346`; tập hồi quy `c497ff707c986acaa3c48ba799ab1a378f194d3e7cd4262834d41a4aae0fe477`. Luồng sửa điều khoản ghi nhận 20/20 ca; đơn vị đã xác nhận: participant 10, visit 10. Trung vị lần lượt theo giai đoạn, đơn vị giây: approve 0.17, clarify_and_propose 0.24, resume 0.2, seed_and_task 1.19.

## Đối chiếu trên cùng dữ liệu

Phiên bản workflow trước có 10 bản sinh trong 10 biên nhận đối chiếu trên 10 ca được giao. Cả hai phiên bản sinh được bản nháp ở 8/10 ca. Trạng thái phiên bản trước: awaiting_qa 10. Phiên bản trước thay đổi cả workflow và hợp đồng kết quả. Phép thử prompt chung chỉ thay hướng dẫn của một vai trò trên cùng đầu vào và schema.

| Hai nhánh theo thứ tự A → B | Cặp so sánh / giao | Trường khác / đã so | Trường có nội dung A → B | Cảnh báo cấu trúc A → B |
| --- | --- | --- | --- | --- |
| Composer cố định → đầy đủ | 8/10 | 46/73 | 73 → 73 | 0 → 11 |
| Prompt chung → hướng dẫn đầy đủ | 8/10 | 18/73 | 73 → 73 | 18 → 11 |

Có 8/10 biên nhận gọi prompt chung và 8/10 cặp đủ trường để so sánh. Số trường thay đổi đo khác biệt văn bản. Nhận định theo nghĩa hoặc chất lượng chuyên môn cần người đọc đánh giá.

## Chi phí và thời gian

| Nhánh | Số lần gọi | Token vào đã đo | Token ra đã đo | Lần thiếu số token | Phí nhà cung cấp (USD) |
| --- | --- | --- | --- | --- | --- |
| Nghiên cứu giữ kín | 30 | 18200 | 2462 | 0 | 0 |
| Khôi phục đơn vị | 60 | 39316 | 5258 | 0 | 0 |
| Luồng nội bộ | 7 | 4638 | 668 | 0 | 0 |
| Workflow trước | 30 | 14834 | 3279 | 0 | 0 |
| Prompt chung | 8 | 4292 | 1140 | 0 | 0 |
| 7B | 8 | 5411 | 1530 | 0 | 0 |

Composer cố định sử dụng 0 lần gọi mô hình. Phí nhà cung cấp chỉ phản ánh inference loopback. Công lao động, chi phí máy thực tế và chi phí trên mỗi tài sản được chuyên gia duyệt chưa được đo.

## Kiểm toán độc lập các trường thương mại

Công cụ tất định đối chiếu giá, đơn vị, điều kiện và các quy tắc có trong từng fixture. Mỗi mẫu số đếm phép kiểm dự kiến trên một bề mặt riêng. Câu ngoài phạm vi được chuyển sang đọc thủ công.

### Nghiên cứu giữ kín · 8/10 ca có đầu vào hợp lệ

| Bề mặt | Phép kiểm dự kiến | Kết quả theo trạng thái | Dòng thương mại cần đọc thêm |
| --- | --- | --- | --- |
| Bản khách trước sửa | 120 | inconclusive 24, matched 96 | 9 |
| Điều khoản trước sửa | 120 | inconclusive 24, matched 96 | 0 |
| Bản khách sau sửa | 120 | inconclusive 24, matched 96 | 9 |
| Điều khoản sau sửa | 120 | inconclusive 24, matched 96 | 0 |

| QA sản phẩm | Ca có bản / giao | Phát biểu có handle / tổng | Handle ngoài danh sách | Trạng thái phát biểu | Cảnh báo Studio |
| --- | --- | --- | --- | --- | --- |
| before | 8/10 | 54/136 | 16 | contradiction 6, editorial 22, needs_correction 29, unresolved 31, verified 48 | relevance 4, repetition 7 |
| after | 8/10 | 54/136 | 16 | contradiction 6, editorial 22, needs_correction 22, unresolved 38, verified 48 | relevance 4, repetition 6 |

SHA-256 của scorer `f4dd914b66f7537dfeeb6efe60cdc9a203168614810864178cb381d042af86e7`.

### Khôi phục đơn vị · 19/20 ca có đầu vào hợp lệ

| Bề mặt | Phép kiểm dự kiến | Kết quả theo trạng thái | Dòng thương mại cần đọc thêm |
| --- | --- | --- | --- |
| Bản khách trước sửa | 240 | inconclusive 12, matched 228 | 8 |
| Điều khoản trước sửa | 240 | inconclusive 12, matched 228 | 0 |
| Bản khách sau sửa | 240 | inconclusive 12, matched 228 | 8 |
| Điều khoản sau sửa | 240 | inconclusive 12, matched 228 | 0 |

| QA sản phẩm | Ca có bản / giao | Phát biểu có handle / tổng | Handle ngoài danh sách | Trạng thái phát biểu | Cảnh báo Studio |
| --- | --- | --- | --- | --- | --- |
| before | 19/20 | 114/317 | 34 | contradiction 13, editorial 56, needs_correction 25, unresolved 113, verified 110 | relevance 10, repetition 26 |
| after | 19/20 | 114/326 | 34 | contradiction 10, editorial 56, needs_correction 20, unresolved 130, verified 110 | relevance 10, repetition 21 |

SHA-256 của scorer `f4dd914b66f7537dfeeb6efe60cdc9a203168614810864178cb381d042af86e7`.

## Đối chứng Qwen 7B

Trạng thái `partial`. Đã gọi 8/10; đủ kết quả so sánh 8/10. Trường khác 24/73. Thời gian trung vị của lần gọi đã ghi nhận: 49.68 giây. Peak RSS tiến trình model: 10090897408 byte. Trạng thái từng ca: paired 8, unpaired_source 2.

Mô hình `Qwen2.5-7B-Instruct Q4_K_M`, revision `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. Giới hạn 10 lần gọi, concurrency 1, retries 0. Trạng thái tài nguyên hoặc lỗi được ghi nhận: xem biên nhận từng ca.

RAM khả dụng / yêu cầu: 15512944640/8390987520 byte. Dung lượng trống / yêu cầu: 97010159616/7921225472 byte.

| Shard dự kiến | SHA-256 | Đã xác minh tải xuống |
| --- | --- | --- |
| qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf | dfce12e3862a5283ccfb88221b48480e58745165de856439950d0f22590580db | Có |
| qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf | 539cf93f78e887edea1c04e2d7d8cdaca9d01dae9c9025bcb8accbe29df3d72a | Có |

Trọng số mô hình nền `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` · build llama.cpp `b12648-44d50873b`. Phép so sánh giới hạn ở Strategy hoặc Content; khả năng của toàn bộ workflow dùng 7B chưa được đo.

## Bảy phương pháp Marketing

Có bằng chứng ghim phiên bản trên các bản sinh ở tập 10 ca cho 7/7 phương pháp.

| Phương pháp có biên nhận | SHA-256 |
| --- | --- |
| campaign-channel@1 | e5f47b865cad8e80a7efab8d1ef1854cf9a4cf5b8185b80ecc263fea1dc631d0 |
| icp-segmentation@1 | b69cd2acdf276b874a4cb956987cfd9ebf00efe4fd286e80d4b835ec6ab5102f |
| kpi-measurement@1 | b3f38b752f72b7a4bb76afc2783e08308f3d19a473b3a18eeed277d6552a13f9 |
| landing-conversion@1 | 65fed41e31b470d9ac009c03a5ee376851fe86664f2c73f2c5e08af49385bcc6 |
| market-research@1 | 86eeef60340cfd5035e4ecbba3807b7afca9b4abd4356e047d8806b8c9f77621 |
| positioning-value@1 | b83430d074a232e1b0e8a2485a935c20bdc2d72521ac25478ac34f99475af93c |
| search-intent-seo@1 | 95015035ae8f0183d82fa88c9851879885736b82032ce11d9b8f12230dc0152d |

## Hai bản mẫu để đọc lại

Chọn ca đầu tiên theo ID trong các ca có bản sinh hợp lệ của mỗi workflow. Ví dụ giữ nguyên ngôn ngữ nguồn, đủ bảy phần dành cho nhân viên và bản xem trước dành cho khách.

[WF-03 · v2-01](EXAMPLE_WF-03.md) · [WF-13 · v2-02](EXAMPLE_WF-13.md)

## Tệp đối chiếu

[Số liệu tổng hợp](METRICS.json) · [Bảng chi tiết nén](OBSERVATIONS.json.gz), SHA-256 `726a0b16d08035a18084513d2bd20bd6e629c9957b80900d454775a2930cabff`. Artifact nguồn: `pool-model-measurements-integration` và `c3-stronger-role-a2dbe4566415fe28226b014ffb8785a1cc2cd9d6`. [GitHub Actions](https://github.com/datnv41001/ai-company/actions/runs/45582688602#artifacts).

Kết luận đọc nghiệp vụ độc lập, nếu có, được lưu cùng hồ sơ và phải ghi rõ người hoặc mô hình thực hiện. Commercial GA vẫn NO-GO.
<!-- END AMC GENERATED QUALIFICATION -->
