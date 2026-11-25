# Nghiên cứu công khai và năng lực reviewer Marketing

Công cụ engineering chạy từ commit nền `5dc4ebc73c9423f360d63287d52350e2ef21a31a`. Người tiếp quản cần Python 3.12, Git, các dependency trong `requirements-pilot.txt`. Đọc [báo cáo và ghim bằng chứng](research-v4/REPORT.md) trước khi diễn giải các chỉ số. Các fixture và bản chạy PR #17, #20, #21 vẫn dùng được với lệnh replay ghi trong HANDOFF.

## Hai tiến trình với quyền khác nhau

1. Operator chạy `public_research.py FILE analytics catalog market community experiments` tại thư mục này. Để chọn topic tự động từ PR tổng hợp đã đăng ký, chạy `public_research.py FILE --fixture public-marketing-v4`. Bộ thu chỉ chấp nhận năm topic đã duyệt. Một lần thu thập chính đọc tối đa sáu URL và một lượt bổ sung được cấu hình cho series thị trường. Dùng `--supplement FILE market` cho nguồn bổ sung. Trình thu thập ánh xạ topic sang trang cố định. Người vận hành thêm publisher, căn cứ quyền trích và locator qua review code trước lần truy xuất tiếp theo. Hiện chưa có tìm kiếm Internet mở.
2. Fetcher chỉ gửi HTTPS GET đến URL đã duyệt. Kiểm tra mọi kết quả DNS, dùng chính địa chỉ IP đã kiểm khi mở socket, xác thực TLS bằng hostname gốc. Từ chối redirect, nội dung nén, tài liệu ngoài HTML và trang lớn hơn 2 MB. Mỗi nguồn có 15 giây, mỗi lần thu thập tối đa 90 giây. Tiến trình không sử dụng proxy hay cookie kế thừa hoặc gửi nội dung ca, tên reviewer, dữ liệu khách hàng, email hay token.
3. Fetcher kiểm tra đoạn trích ngắn trong phần văn bản hiển thị rồi ghi URL, publisher, locator, thời gian UTC, số byte, SHA-256 toàn bộ body và trích đoạn, phân loại nguồn và giới hạn sử dụng. Body chỉ tồn tại trong RAM. Mất trích đoạn, trang bị chặn, lỗi TLS, dữ liệu quá lớn hay timeout tạo gap. Trang có thể thay đổi kể từ lúc chụp. Kiểm lại nội dung gốc trong tương lai tùy quyền và tình trạng publisher. Replay offline xác minh snapshot đã ghim và các digest, không tải lại trang đã đổi.
4. Reviewer chỉ nhận bibliography và các trích đoạn đúng chủ đề từ snapshot trong kế hoạch đã đóng băng. Ba lần đọc packet chỉ dùng một snapshot. Tuổi tối đa cho thí nghiệm mới là bảy ngày. Một snapshot mới có ID khác. Nếu nguồn bị rút, operator ngừng enrollment mới dựa trên nguồn đó, tìm các study có snapshot digest tương ứng và mở lại nhận xét liên quan. Lịch sử giữ nguyên. Thu hồi tự động liên kho vẫn là việc mở.
5. Tài liệu nền tảng và đối thủ mô tả phạm vi sản phẩm của publisher. Một phản hồi cộng đồng hoặc cuộc thảo luận Marketing có thể gợi ra giả thuyết cần xác minh. Chỉ dữ liệu hợp lệ của đúng khách hàng mới xác lập giá, chính sách hoặc kết quả kinh doanh riêng của họ. Tất cả đoạn trích là dữ liệu chưa tin cậy. Worker không có adapter mạng, công cụ shell, credentials hoặc thao tác gửi findings. Model local dùng tiến trình native chỉ trên máy dev và input tổng hợp.

## Thiết kế phép đo

Mười ca tổng hợp mới về engagement trong GA4, nhóm sản phẩm WooCommerce, suy luận từ dữ liệu Mỹ, quy cách đơn hàng và retargeting. Một agent khác tác giả bộ ca đã gán nhãn, nêu nguồn và đề xuất hành động trước khi chạy Qwen. Đây là nhãn do AI chấm. Một người chấm nghiệp vụ độc lập vẫn là nguồn đối chiếu cần thiết cho quyết định thương mại.

Mỗi arm dùng cùng reviewer `MK-022`, checkpoint Qwen2.5-1.5B đã pin, seed 61, ngân sách đầu ra 285 token/call, cùng ca, rubric, bibliography và schema. Năm topic × hai arm, thứ tự arm luân phiên, mỗi lần gọi xử lý hai ca. Chỉ arm có nghiên cứu nhận bốn packet thực sự truy xuất được theo topic. Hai ca thị trường có prompt giống hệt giữa hai arm. Giới hạn cả run là 16.000 token, một slot, không retry, phí provider bằng 0. Một closed-set source ID và verdict đi kèm hai trường giải thích/khuyến nghị tự do. Hai mươi verdict đến từ mười lượt gọi, một reviewer, một checkpoint.

Đối chiếu ba lớp riêng. Verdict so với tiêu đề gold của đúng ca. ID nguồn liên quan có thể đo ngay ở cả hai arm; một citation có bằng chứng trong context cần source đã truy xuất và đúng chủ đề. Ba đánh giá ngữ nghĩa độc lập xem lý do, quy kết đúng phạm vi và khuyến nghị sử dụng được. Xuất thứ tự mù, ẩn arm và điểm tổng; người chấm vẫn có thể suy ra arm từ nội dung trả lời. So khớp nguyên văn với mẫu sửa chỉ là proxy hạn chế. Sai từ ngữ trong proxy tách riêng khỏi lỗi lập luận hay hành động của model. Chỉ báo gain/loss theo từng cặp trên holdout. Mười ca, một seed, ba gap, một người chấm AI giới hạn khả năng suy rộng.

## Tái dựng trên máy khác

Từ repository root, sau khi kích hoạt venv engineering:

```sh
python -m pip install -r engineering/airc500/requirements-pilot.txt
python engineering/airc500/research_release.py
python -m unittest discover -s engineering/airc500 -p "test_*.py" -v
python -m unittest discover -s engineering/airc500/stronger -p "test_evidence.py" -v
```

Replay kiểm tra pins ở mã review, synthetic Git fixture, SHA của oracle và snapshot, ngữ cảnh/plan, chữ ký Ed25519, raw response, usage và toàn bộ kết quả theo ca. Không cần network hoặc weights. Khi thu thập nghiên cứu mới, dùng tên file ngoài bộ chứng cứ v4 và review enrollment mới trước khi thực thi. Trên máy Windows có bundle runtime và GGUF đã pin, dùng `research_study.py enroll --out NEW_DIRECTORY --private EXTERNAL_NEW_DIRECTORY` để chốt pin; tiếp theo `run --out NEW_DIRECTORY --private EXTERNAL_NEW_DIRECTORY --pin REVIEWED_SHA256 --server LLAMA_SERVER --model QWEN_GGUF`. Những lệnh này tạo measurement mới trên fixture đã đóng băng trong kho; enrollment mới từ chối nguồn đã hết hạn. Private key, model và SQLite journal nằm ngoài checkout. Muốn chấm diễn giải mới, dùng `research_assessment.py blind` rồi cố định file grader trước khi unblind.

## Lộ trình review revision AMC lịch sử

| Điều kiện | Bằng chứng cần có | Trạng thái |
|---|---|---|
| Chủ sở hữu cấp phép | Quyền đọc ghi rõ repository, commit, scope, người nhận, hạn và ngân sách | Chưa cấp revision thực |
| Cô lập | Runner riêng đọc-only; mount, giới hạn tài nguyên, network mặc định đóng; chứng minh bằng bài kiểm tra môi trường thật | Docker probe cũ chỉ đo worker thử, nghiên cứu Windows dùng dữ liệu tổng hợp |
| Quản lý khóa | Tách quyền ký adapter và attest của verifier, custody độc lập, rotation/revocation, log bất biến, thử recovery | Key dev Ed25519 được tạo ngoài checkout, chưa có custody độc lập |
| Ground truth | Người đánh giá độc lập đóng dấu trước tập lỗi đã biết và ca sạch; chia theo năng lực, giữ lại một tập chưa công bố | Mới có holdout Marketing tổng hợp do AI chấm |
| Năng lực | Chứng minh cải thiện có thể lặp lại trên verdict, nguồn và hành động; đo clean false positives, abstention, chi phí; xét riêng từng capability | Code logic và security/regression chưa đo với model; xem bảng Marketing trong báo cáo |
| Kiểm soát đầu ra | Phân quyền người đọc, lưu report local, nhãn dissent và escalation. Hành động đăng/merge ngoài phạm vi reviewer | Không có dispatch tới repository thực trong plan này |

Sau khi owner xác nhận các điều kiện, thử một revision lịch sử được cấp phép, một khoản token đã duyệt, bộ lỗi được chuẩn bị độc lập và tập đối chứng sạch. So với review thủ công và deterministic. Chỉ đề xuất mở rộng những chuyên môn có lợi ích đo được. Registry vẫn đủ 500 profile. Commercial GA và real-source review tiếp tục HOLD. Rollback riêng tooling bằng ngừng thu thập và thực thi v4; các snapshot đã ký và truy vết kết quả vẫn đọc offline.

**Challenge cho reviewer.** Xem từng cặp cùng nội dung, kiểm tra trường hợp có source ID đúng nhưng câu giải thích sai; so số khuyến nghị hữu ích với điểm exact-match. Kiểm tra rằng hai lỗi 403 và timeout không làm phát sinh citation hợp lệ cho các ca thị trường. Đối chiếu số lượt gọi thực với số case-level verdict trong báo cáo.
