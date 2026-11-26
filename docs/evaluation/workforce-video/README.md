# WF-08 · từ brief của agency đến tờ dựng có thể kiểm tra

## 1. Điểm bắt đầu đã tích hợp

Main sau #58 là `1c40ad3185ac49415c3f555bb5b6406e2cdd8cb1`, tree `d3923be500fc756b7f64fe611b3a967015e96941`. Đã kiểm lại hai parent, head `be8e251a`, tree và chín job trên bản chờ merge. ZIP #58 được giữ theo SHA-256 `111a88e22f3a93f71fe65fbae7bb0e1f53cc8dba4f590544608529e5d32e0ebe`. [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45784910737) · [Gói điều khiển lịch sử](https://github.com/datnv41001/ai-company/tree/58b28ea1d75c63bbe05f9ce13fe233e173cf1dbb/docs/evaluation/round57-verification)

CI trên đúng commit merge đạt 3/3 job, 631 test đạt và hai biến thể SQLite được skip vì cần PostgreSQL. Có 22 đường nâng dữ liệu lên v26 và restore giữ dữ liệu giống nhau ở 34 bảng.

## 2. Bốn finding và sản phẩm bàn giao

| Finding | Thay đổi có thể kiểm tra | Điều kiện còn mở |
| --- | --- | --- |
| R58-01 · Thông điệp | Chuyển CTA khảo sát sang gửi đề nghị, sửa master, portrait, metadata, form và trạng thái trên bản mới. Khe Gọn cho phép để lại nhu cầu dưới MOQ. QA ký riêng. [Các bản và ảnh trình duyệt](../aligned-intake/README.md) | Cần người mua đọc đúng nghĩa giá và lịch. |
| R58-02 · Creative | Có preview dọc phát được từ thời lượng, cue, cảnh và CTA trên bản sau QA. Hình tự vẽ, có nhãn minh họa. [Xem và tái dựng](../storyboard-preview/README.md) | Cần footage có quyền và người dựng nếu muốn chuyển sang phim quảng cáo. |
| R58-03 · Workforce | Director nhận brief đã ký, worker tạo storyboard bằng adapter tất định; có run ID, attempt, output và người QA. | Chỉ một lát cắt WF-08 tiếng Việt. Chưa đo chất lượng model sáng tạo hoặc khả năng hoạt động ở ngành bất kỳ. |
| R58-04 · Measurement | Ghép receipt visit với submission và landing cùng edition; replay hợp đồng CRM và KPI lịch hẹn hiện hữu. [Kết quả và protocol](MEASUREMENT.md) | Chưa có nhóm phân bổ hoặc dữ liệu hiệu quả quảng cáo thật. |

## 3. Giao một nhiệm vụ qua runtime

Trong dev PostgreSQL, maintainer dùng quy trình publish registry hiện hữu để cài `catalog/video-storyboard-v1.json` vào database, rồi admin kích hoạt release cho đúng campaign. Từ API Workforce tạo brief, lưu task submission, chọn nguồn theo tenant/client/brand/campaign, ký manifest với quyền và phạm vi. Gửi `POST .../workforce/briefs/{brief_id}/run` với `workflow=dynamic-v1`, `registry_workflow=WF-08/video-storyboard@1`, ID/digest manifest và ngân sách 0. Queue tạo run. Worker lấy lease, dispatcher nhận kết quả Director rồi giao việc cho specialist. API có thể đọc run, provenance và tài liệu chờ QA. Tên “worker” ở đây là tiến trình thực thi adapter cục bộ. [Runbook cài binding trên máy khác](../wf08-storyboard/RUNTIME.md) · [Phép thử và payload cụ thể](../../../tests/test_video_storyboard.py) · [Manifest phát hành](../../../catalog/video-storyboard-v1.json)

## 4. Bản gốc của worker

Tệp `raw.json` lưu nội dung trước biên tập. Mỗi bản gồm concept, hook, hướng thị giác, shot, lời đọc, caption/VTT, kênh, brand, thời lượng, quyền minh họa và nguồn. Dữ kiện thương mại lấy từ manifest được duyệt. Nếu brief không có giá, worker ghi tình trạng thiếu giá trong phần dành cho editor. Lời đọc và phụ đề gửi người xem chỉ dùng nội dung có thể công khai. Cảnh được phân thời lượng và kiểm tốc độ đọc. [SOP được ghim](../../../catalog/video-storyboard-sop-v1.json)

## 5. Bản sau review và thay đổi

| Brief và đầu ra đầu tiên | Bản sau QA | Lượt chạy Director + specialist trong PostgreSQL dev |
| --- | --- | --- |
| [Khe Gọn · bản gốc](../wf08-storyboard/index-tray/raw.json) | [Revision 2](../wf08-storyboard/index-tray/reviewed.json) · [Video](../storyboard-preview/index-tray/preview.webm) | [Receipt](../wf08-storyboard/index-tray/receipt.json) · 340,09 ms, 5 cảnh |
| [Luồng Rõ · bản gốc](../wf08-storyboard/receipt-map/raw.json) | [Revision 2](../wf08-storyboard/receipt-map/reviewed.json) · [Video](../storyboard-preview/receipt-map/preview.webm) | [Receipt](../wf08-storyboard/receipt-map/receipt.json) · 353,67 ms, 5 cảnh |
| [Phách Mở · bản gốc](../wf08-storyboard/rhythm-class/raw.json) | [Revision 2](../wf08-storyboard/rhythm-class/reviewed.json) · [Video](../storyboard-preview/rhythm-class/preview.webm) | [Receipt](../wf08-storyboard/rhythm-class/receipt.json) · 348,85 ms, 3 cảnh |

Thời gian đồng hồ này đo từ khi bắt đầu xử lý Director đến khi nhận kết quả specialist trong phép thử một máy. Chưa tính tuyển người, chuẩn bị brief, QA, dựng video hoặc vòng trả sửa. Hai bản có offer dài 32 giây; brief đọc nhịp không có giá dùng 18 giây. Trường hợp policy mâu thuẫn kết thúc ở failed, có receipt và không xuất tài liệu. [Journal lần thất bại](../wf08-storyboard/failed-policy-conflict.json)

Trong bài diễn tập, người có quyền chọn biến thể hook hướng tới audience. Người QA khác ký revision/digest mới. Bản đầu và bản sửa có thể đối chiếu từng cue; không ghi đè bản đầu. Các ảnh/trang Studio cũ giữ nguyên. Riêng replay sửa CTA của Luồng Rõ trên cùng tài liệu chứng minh bản ký cũ không thể ký thay revision mới và snapshot lịch sử vẫn đọc lại đúng byte. [Hồ sơ sửa CTA](../aligned-intake/revision.json)

## 6. Scope, nguồn và trách nhiệm

Brand Kit, ICP, claim, điều kiện giá, thuế, MOQ, hành động khách được phép và quyền hình là đầu vào. Có kiểm tra sai tenant/manifest và cấp quyền truy cập nguồn cho người sửa. Mỗi output lưu revision, manifest digest và ID nguồn. Tệp receipt lưu run, journal và actor QA tổng hợp. Việc QA chấp nhận nội bộ cho phép chuyển bản cho người dựng trong diễn tập. Không có tác động tới tài khoản quảng cáo hoặc dữ liệu thật.

## 7. Mở preview

Mỗi bản dựng có video dọc VP8/WebM, VTT và ảnh các cảnh đã giải mã. Mở khi tắt âm, đọc đủ giá và đơn vị, rồi kiểm CTA cuối cùng. Biên nhận render chỉ rõ preset hình do người dựng chọn, vùng an toàn và digest đầu vào. Đây là kiểm chứng tiền kỳ. Hai artwork #58 có chung motif hình học được giữ làm đối chứng kỹ thuật. [Các hướng creative và giả thuyết theo ICP](../storyboard-preview/CREATIVE-DIRECTIONS.md)

## 8. Brief khác ngành và chất lượng

Trong lần xem trước, người kiểm tra bắt được câu điều kiện đặt hàng của fixture hàng hóa lọt vào brief dịch vụ và câu claim nối sát phần giới hạn. Đã sửa dữ kiện dịch vụ tại nguồn, phân cách câu rõ hơn rồi chạy lại từ queue và dựng lại cả ba clip. Ca regression thêm kiểm hook hành động chọn buổi ở showroom; câu hỏi mở đầu phải phù hợp cả khi người mua không chọn lớp học.

Một AI độc lập đọc cả ba cặp raw/reviewed, VTT và 14 khung đã giải mã ở [bản trước lần sửa cuối](https://github.com/datnv41001/ai-company/tree/71635e4fd285f6dc13d78a60f312a1ea10030ee7/docs/evaluation/wf08-storyboard). Reviewer nhận thấy các hook có cùng cấu trúc, ảnh trước/sau tháo vách khó phân biệt, biểu tượng sơ đồ bị dùng cho cả bước chờ lịch, và Phách Mở dành bảy giây cho trạng thái giá nội bộ. Giữ nhận xét đó cùng bản đã chấm. Bản hiện hành đưa trạng thái thiếu giá về ghi chú cho editor, giữ CTA chọn buổi và điều kiện của offer trong phạm vi được duyệt. Lượt chấm là đánh giá kỹ thuật của AI, chưa đo phút dựng của người hành nghề.

Phách Mở là brief tổng hợp mới về đọc nhịp cho người lớn quay lại học nhạc. Brand, đối tượng, hành động và cấu trúc offer khác hai brief cũ; brief không cung cấp giá. Kiểm riêng trường hợp mâu thuẫn policy và thu hồi nguồn. Độ hoàn chỉnh đo bằng các trường và cue có thể dựng; độ chính xác đối chiếu claim và điều kiện theo manifest. Người dựng thật chưa chấm tính hữu ích hoặc phút sửa. Ba ca tuyển có chủ đích là bằng chứng cho những đầu vào được thử.

## 9. Nghiên cứu, chi phí và pilot

Ở lượt chạy trên mã tích hợp, hai clip có giá giữ nguyên 32 giây; clip lớp nhạc còn 18 giây. Đã xem 13 điểm đầu cảnh từ video giải mã. Khe Gọn cho thấy một vách được nhấc khỏi chính khay đang lắp, Luồng Rõ tách sơ đồ bàn giao khỏi bước chờ người xác nhận, Phách Mở có ví dụ nhịp mạnh/nhẹ và thẻ chọn buổi. Các hình là minh họa; người dựng chọn preset phù hợp nguồn. Cách đặt hook theo audience vẫn còn chung. [So sánh biên tập và giới hạn](../storyboard-preview/README.md)

Đã đọc hướng dẫn creative của TikTok, transcript công khai Meta về fatigue, mô tả Ads Creative Studio và định nghĩa engagement của YouTube. Ghi riêng lý do nguồn bị chặn, đoạn trích chỉ mục và kinh nghiệm cộng đồng. [Sổ nguồn](../../research/SOURCE_REGISTRY.md) · [Áp dụng O-01 đến O-09](../../research/APPLICABILITY_MATRIX.md#r58-wf08)

WF-08 dùng adapter tất định với số token và phí provider bằng 0. CI tiêu chuẩn vẫn có job hồi quy Workforce model của các release trước. O-09 ở lab, 12 trace theo mẫu và 14 fixture grammar giữ nguyên phạm vi chứng minh và điểm Qwen lịch sử. Chưa mời người thật. Có 0 practitioner, 0 Business-accepted Marketing Work Units. Điện, công sửa của người hành nghề, tác động tới doanh thu và chi phí trên mỗi work unit được chấp nhận chưa đo. [Điều kiện tổ chức pilot và ghi thời gian](../department-study/PILOT-ABCD/OFFICIAL.md)

## 10. Binding, quay lui và câu hỏi phản biện

Giữ charter 49 module, 37 vai trò, 24 workflow mẹ. Bổ sung binding nội bộ `ai-video-storyboard` cho một release của WF-08, dùng lại Director, registry, queue, gateway policy và QA hiện có. Studio vẫn là công cụ render. Khi dừng thử nghiệm, vô hiệu binding của release trên đúng campaign, giữ journal, bản đã duyệt, snapshot và các release cũ. Nếu cần rollback binary, áp dụng runbook phục hồi dev đang dùng. Production và Commercial GA NO-GO. [Phân loại năng lực](../../IMPLEMENTATION_STATUS.md)

Câu hỏi dành cho reviewer là một editor mới có thể dựng đúng hình từ shot list mà không phải xin lại brief hay không, và người xem có hiểu “gửi đề nghị” chưa xác nhận lịch hay không. Ưu tiên đo trên brief mới, có consent, trước khi mở thêm vai trò nội dung theo kênh.
