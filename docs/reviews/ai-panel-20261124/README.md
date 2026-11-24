# Kiểm tra chất lượng Content, SEO và Strategy bằng reviewer AI

**Phạm vi quyết định.** Trên 24 ca Marketing song ngữ có chủ ý đưa vào tình huống khó, QA của WF-13 phát ra 33 cảnh báo. Với phiếu do trọng tài AI phân xử, 18 cảnh báo khớp, 15 cảnh báo thừa và 22 cảnh báo bị bỏ sót. Khi so tất cả các trường và quy tắc, 5/24 ca khớp hoàn toàn. Phù hợp dùng để gợi ý người biên tập kiểm tra bản nháp. Số liệu này chưa đo hiệu quả đối với khách hàng thật.

| Đầu ra | Ca | Cảnh báo khớp | Cảnh báo thừa | Bỏ sót | Tỷ lệ cảnh báo đúng | Tỷ lệ phát hiện |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Content | 12 | 8 | 9 | 10 | 47,1% | 44,4% |
| SEO | 12 | 10 | 6 | 12 | 62,5% | 45,5% |
| Chung | 24 | 18 | 15 | 22 | 54,5% | 45,0% |

Một nhãn là bộ ba **ca, trường, quy tắc**. Tỷ lệ cảnh báo đúng lấy số khớp chia cho tổng cảnh báo của QA. Tỷ lệ phát hiện lấy số khớp chia cho tổng cảnh báo trên phiếu phân xử. Với hai phiếu chuyên gia AI trước phân xử, tỷ lệ cảnh báo đúng đều là 54,5%, tỷ lệ phát hiện lần lượt là 51,4% và 50,0%. Phiếu kỹ thuật ban đầu trên cùng bộ ca chỉ có 26 nhãn, cho kết quả 57,6% và 73,1%. Các con số thay đổi theo nhãn tham chiếu. Cả hai phép đo sử dụng cùng QA policy. [Báo cáo kỹ thuật trước đó](../landing-qa-eval/technical-report.md).

### Ai đã chấm và họ được xem gì

- Hai lượt Codex riêng biệt chấm mù toàn bộ 24 ca dưới góc nhìn biên tập và quản lý chiến dịch. Mỗi lượt nhận brief, nguồn, bản viết và rubric. Với SEO còn có bài Content tiền nhiệm. Hai phiếu cùng tập nhãn ở 22/24 ca. [Phiếu biên tập](ai-editorial.json) · [Phiếu chiến dịch](ai-campaign.json).
- Một lượt Codex thứ ba đọc bộ ca và hai phiếu, phân xử B02 và G04, đồng thời bổ sung ba cặp cả hai lượt trước bỏ sót ở B03 và C05. Phiếu được chốt trước khi so với dự đoán của QA và kết quả hội đồng Qwen. Có 40 nhãn trên 20 ca. Bốn ca còn lại có phiếu trống sau khi chấm. [Phiếu phân xử có lý do từng ca](ai-consensus.json).
- Hội đồng Qwen chạy **216 lượt suy luận hoàn chỉnh**, một vai trò trên một ca, chín góc nhìn cho mỗi ca. Bốn chiến dịch gồm túi xe đạp đi làm, lớp gốm cho người mới, bộ lọc cà phê tại nhà và tour hải đăng gia đình. Mỗi vai nhận cả đầu ra để cân nhắc những cảnh báo ngoài chuyên môn chính. [Brief, toàn văn nguồn và ID bài tiền nhiệm](../landing-qa-eval/cases.json). Tên vai là chức năng nghề nghiệp trong ngữ cảnh chiến dịch. Toàn bộ 216 lượt dùng cùng checkpoint local `Qwen2.5-0.5B-Instruct`. Các phiếu có thể lặp cùng một thiên lệch. Mỗi dòng lưu prompt digest, seed, model, văn bản trả lời gốc và các nhãn đã đọc. [Đọc 216 nhận xét theo từng ca, kèm phân xử tiếng Việt](opinions.md) · [Phiếu Qwen gốc](panel.jsonl).
- Một lượt thẩm định AI riêng đọc bằng chứng nguồn và năm cảnh báo của WF-03. Hai cảnh báo cùng đề cập trường đơn vị. Báo cáo chỉ ra bốn việc cần sửa và đề xuất cách đo để kiểm tra tại cửa hàng. [Đánh giá Strategy và ví dụ KPI](strategy.md).

### Điểm cần sửa trước khi dùng bản nháp

| Tình huống | Hậu quả đối với khách hàng | Cách xử lý bản nháp |
| --- | --- | --- |
| G02 cho phép chạm thấu kính gốc. S1 chỉ cho trẻ chạm bản sao. QA bỏ sót cảnh báo về bằng chứng. | Gia đình có thể đến với kỳ vọng sai về hoạt động của tour. | Viết “Trẻ có thể chạm bản sao thấu kính. Bản gốc được trưng bày sau kính.” Khi QA, đối chiếu đồng thời hiện vật, hành động và điều kiện tiếp cận. |
| L02 dùng “indestructible” dù hướng dẫn thương hiệu yêu cầu loại bỏ từ này. L01 còn mở rộng đặc tính chống nước của đường may sang toàn bộ túi. | Người mua có thể hiểu sai giới hạn độ bền hoặc khả năng chống nước. | Giữ thông tin có nguồn về cách gắn baga và đường may. Đọc chỉ dẫn viết dưới dạng văn xuôi, kể cả khi không có danh sách từ cấm. |
| C01 có CTA “Giữ chỗ cho buổi học”. C02 viết “không cam kết hiệu quả 100%”. QA vẫn báo lỗi ở cả hai. | Biên tập viên có thể bỏ một CTA tốt hoặc sửa câu phủ định thành một thông điệp kém chính xác hơn. | Đọc câu trong ngữ cảnh tiếng Việt. Kiểm tra người đọc có thực hiện được hành động và phân biệt cam kết với câu phủ định cam kết. |
| G06 nói về chuyến tham quan nhưng truy vấn là mua nhà gần hải đăng. C05 nói về mua máy công nghiệp thay cho lớp gốm. | Từ khóa trùng có thể dẫn khách đến trang sai mục đích. | So loại giao dịch, đối tượng và hành động của truy vấn với bài Content đã ghim. Kiểm thử riêng trường hợp hai ý định có cùng danh từ. |
| B02 mượn lời khen hạt cà phê để mô tả bộ lọc. | Một câu có thật trong nguồn vẫn có thể gán sai lời chứng thực cho sản phẩm. | Gắn nhận xét với đúng đối tượng. Muốn mô tả chất liệu hoặc khả năng tái sử dụng của bộ lọc, dẫn nguồn sản phẩm thích hợp. |

Trong 22 cặp bỏ sót, 13 thuộc bằng chứng của claim, 5 thuộc độ khớp giữa metadata và trang, 2 thuộc ý định tìm kiếm, 1 thuộc mục tiêu brief và 1 thuộc hướng dẫn thương hiệu. Ưu tiên nghiệm thu cho lần cải tiến sau là chủ thể của claim, phủ định trong hai ngôn ngữ và ý định tìm kiếm. Khi thay đổi logic, dùng thêm ca mới chưa từng xuất hiện trong tài liệu này để đánh giá lại. [Sai lệch theo từng trường](scores.json).

### Hội đồng theo góc nhìn

Với ngưỡng ít nhất 5/9 phiếu cùng chọn một cặp trường–quy tắc trong một ca, Qwen chọn **15 cặp**. Đối chiếu phiếu phân xử, **0 cặp khớp và 40 cặp bị bỏ sót**. Có 118 phiếu để trống toàn bộ nhãn và 5 phiếu chọn mọi nhãn hợp lệ. Tổng số cặp do từng vai chọn trước khi gộp là 529. Toàn bộ lượt cuối dùng một checkpoint với 151.065 token vào và 15.718 token sinh ra. Đa số của hội đồng này chưa đủ tin cậy để tự duyệt bản giao.

G06 cho thấy một ý kiến thiểu số vẫn đáng đọc. Chỉ 1/9 vai chọn đúng lỗi ý định tìm kiếm mua bất động sản trên trang tour hải đăng (P213). Ở G02 cũng chỉ có 1/9 phiếu chọn đúng lỗi đưa ra lời hứa trái nguồn về thấu kính gốc. Với L01, 4/9 phiếu nhận ra claim về khả năng chống nước của túi, còn đa số gắn lỗi vào headline. P001 chọn tất cả 14 nhãn có thể chọn cho ca này. [L01](opinions.md#l01) · [G02](opinions.md#g02) · [G06](opinions.md#g06).

Mỗi dòng dưới đây tổng hợp 24 lượt của cùng một góc nhìn, mỗi lượt trên một ca. Hai cột cuối đo mức khớp với phiếu phân xử. Một vai có thể nêu chi tiết đáng đọc dù chọn sai nhãn. Vì cả chín góc nhìn dùng cùng model nhỏ, kết quả chỉ phản ánh model, prompt và 24 ca này.

| Góc nhìn | Cặp khớp | Cặp thừa | Bỏ sót | Tỷ lệ cảnh báo đúng | Tỷ lệ phát hiện |
| --- | ---: | ---: | ---: | ---: | ---: |
| Biên tập | 4 | 53 | 36 | 7,0% | 10,0% |
| Thương hiệu | 11 | 33 | 29 | 25,0% | 27,5% |
| Độc giả và khách hàng | 2 | 24 | 38 | 7,7% | 5,0% |
| Kiểm chứng nguồn | 12 | 67 | 28 | 15,2% | 30,0% |
| Chuyển đổi và CTA | 2 | 52 | 38 | 3,7% | 5,0% |
| Tìm kiếm và SEO | 12 | 46 | 28 | 20,7% | 30,0% |
| Bản địa hóa | 4 | 59 | 36 | 6,3% | 10,0% |
| Thông tin sản phẩm | 7 | 58 | 33 | 10,8% | 17,5% |
| Điều phối chiến dịch | 6 | 77 | 34 | 7,2% | 15,0% |

### Kiểm lại trên máy khác

Từ thư mục gốc của repository, dùng Python 3.12 và dependencies đã khóa trong dự án. Checkout commit chứa bộ hồ sơ này để dùng đúng manifest, runtime và casebook. Hai lệnh đầu kiểm tra phiếu đã lưu và tính lại điểm mà không gọi mô hình.

```sh
python docs/reviews/ai-panel-20261124/panel.py --validate-only
python docs/reviews/ai-panel-20261124/score.py --output scores-replay.json --opinions opinions-replay.md
python docs/reviews/landing-qa-eval/evaluate.py --labels docs/reviews/ai-panel-20261124/ai-consensus.json
```

Để sinh hội đồng mới trên máy phát triển, trỏ `--server` vào llama.cpp local đang phục vụ đúng GGUF, dùng `--workers 1` và một đường dẫn `--out` mới. Nếu dùng Docker từ một checkout dev mới, chạy `python scripts/init_env.py` và `python scripts/fetch_workforce_model.py`. Lệnh sau mở llama.cpp trên loopback của máy. Giữ terminal đó chạy trong khi thực hiện lệnh sinh phiếu ở terminal thứ hai.

```sh
docker compose -p amc-ai-panel --profile local-model run --rm --no-deps -p 127.0.0.1:18089:8080 model
```

```sh
python docs/reviews/ai-panel-20261124/panel.py --server http://127.0.0.1:18089 --gguf models/workforce.gguf --workers 1 --out panel-replay.jsonl
```

Dùng cùng đường dẫn khi tiếp tục một lần chạy gián đoạn. Giữ các phiếu gốc khi so lần chạy. Model local có thể cho câu trả lời khác tùy bản dựng, phần cứng hoặc seed. Điểm tham chiếu của báo cáo dùng digest bộ ca `4a9c1b5377c194ab33d65bcf6f9081e6c04ac84af67271a94465de7541717da6` và manifest WF-13 `f47ddd7984fc1aa9d4fe3ba325ce917b49e8cfa4d504debd1ad8d7bb58003c9a`.

Tệp JSONL gốc có SHA-256 `04e59a6c2848ca3ea1cd8f25334d1af5acb22d6571fc458a8cbe6ac46b6a2f43`. Các tác vụ chấm dùng dữ liệu tổng hợp. Điểm số được lưu với nguồn gốc `ai-simulated`. Bộ ZIP chấm mù, nhãn kỹ thuật trước đó, QA policy, quyết định khách và snapshot của run giữ nguyên.
