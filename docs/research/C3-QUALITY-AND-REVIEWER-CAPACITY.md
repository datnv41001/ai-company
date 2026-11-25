# Từ brief đến bản giao có thể dùng

Ngày đọc và đo là 25/11/2026. Ghi chú này bổ sung cho [K-07, K-08 và K-09](KNOWLEDGE_CARDS.md). Nguồn do người vận hành đọc qua trang công khai. Số lượt chạy reviewer để đọc nguồn là **0**.

| Nguồn, phần đã đọc | Loại và giới hạn | Quyết định sản phẩm và ca nghiệm thu | Phương án đã loại |
| --- | --- | --- | --- |
| Dan Hockenmaier, Gustaf Alströmer, Craig Cannon, transcript chính thức YC đoạn 16:57–20:38. Ví dụ Thumbtack phân biệt lời hỏi giá có phản hồi với việc thuê được thợ. [Transcript](https://www.ycombinator.com/blog/advice-on-organizing-and-running-growth-teams-from-dan-hockenmaier-and-gustaf-alstromer/) | Kinh nghiệm điều hành marketplace. Dùng để chọn câu hỏi đo lường. Không có dữ liệu agency Việt Nam hoặc đối chứng nhân quả. | K-08, O-01/O-07. Ca C3 vật liệu xây dựng dùng yêu cầu báo giá có địa bàn, diện tích và kỳ đo. Reviewer kiểm tra bản chiến lược vẫn ghi doanh thu chưa xác định khi CRM chưa xác nhận đơn. | Quy đổi tất cả yêu cầu báo giá thành doanh thu hoặc dùng số lượt xem làm mục tiêu cuối. |
| Google Search Central, ca Rakuten Recipe, phần Solution và Result. Nhóm dùng báo cáo Search Console để kiểm lỗi của structured data rồi theo dõi traffic và thời lượng phiên. [Case study](https://developers.google.com/search/case-studies/rakuten-case-study) | Ca trước/sau do nền tảng và nhà xuất bản mô tả. Không có nhóm đối chứng, không cùng ngành với khách giả lập. | K-06/K-07, O-05/O-06. Trong WF-13, bản nháp có tiêu đề, ý định tìm kiếm và CTA cho đúng sản phẩm. Bằng chứng đánh giá chỉ ghi trang đã xuất bản, lập chỉ mục hoặc tạo traffic khi có dữ liệu tương ứng. | Đưa mức tăng của Rakuten vào dự báo của khách hoặc suy ra đã xuất bản từ một bản nháp. |
| Anthropic, *Demystifying evals for AI agents*, mục thuật ngữ, thiết kế harness và kiểm tra transcripts. [Bài kỹ thuật](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) | Kinh nghiệm thiết kế evaluation từ nhà phát triển. Chưa xác lập ngưỡng chuyên môn Marketing tiếng Việt. | K-09/K-10, O-01/O-08. So cùng ca, nguồn và checkpoint local. Lưu mã băm request, lượt thử lại, số token, bản giao thực và trạng thái DB. Chấm riêng độ đúng của dữ kiện, qualifier, KPI và giá trị sử dụng. | Đếm số job thành công như điểm Marketing. Một lượt cho mỗi ca chưa đủ để ước lượng độ ổn định qua nhiều lần sinh. |

## Chọn máy thử tiếp theo cho AIRC

Báo cáo Joint V5 có 20 invocation, 2 reviewer ID và 8 ca. Cả hai model nhỏ đều đạt 0/8 sau phản biện chéo ở tiêu chí kết luận, nguồn, lý do và hướng sửa đồng thời. Giữ catalog 500, tự động kiểm digest, locator và phạm vi bằng mã. Kết luận chuyên môn tiếp tục cần bộ holdout do người độc lập kiểm tra. [Joint V5 tại SHA đã review](https://github.com/datnv41001/ai-company/blob/9cf65c79d4a450633f4f1c109e3dd501c9e932a8/engineering/airc500/joint-v5/REPORT.md)

Windows API GlobalMemoryStatusEx ghi **15,83 GiB RAM vật lý, 0,78 GiB khả dụng** khi PostgreSQL, model hiện hữu và công việc local cùng chạy. Đây là một lần lấy mẫu trong tải thực. Hai ứng viên dưới đây chỉ là giả thuyết cho một máy khác có đủ RAM. Số invocation của hai ứng viên trong lần khảo sát này là 0.

| Ứng viên | Căn cứ chọn và điều phải đo |
| --- | --- |
| Qwen2.5-7B-Instruct GGUF | Nhà phát triển công bố 7,61 tỉ tham số, hỗ trợ tiếng Việt và sinh JSON. Ước lượng lý thuyết 4 bit/tham số khoảng 3,54 GiB trước metadata, KV cache và bộ nhớ runtime. Cần đo peak RAM ở độ dài bundle thực, tốc độ và khả năng từ chối khi nguồn không đủ. [Model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF) |
| Gemma 4 E4B | Bảng bộ nhớ của Google ghi 4,5 GB ở 4 bit. Cần cộng chi phí theo engine, modality và context, rồi đo trên thiết bị đích. Dùng bộ ca tiếng Việt và đổi thứ tự chứng cứ để kiểm độ bền kết luận. [Bảng tham khảo của nhà phát triển](https://gemma.ai/models/gemma-4/) |

Ở máy thử độc lập, ghim digest weights, phiên bản engine, template và context. Dùng một worker, giới hạn thời gian và token theo ngân sách lab đã duyệt. Ghi RSS, thời gian, hồ sơ từng lỗi và chi phí trên finding kiểm chứng được. Chỉ xem xét thay đổi quyền sau khi reviewer độc lập xem từng ca nghiêm trọng, false positive, nguồn trích và hướng sửa trên holdout giữ kín. Đây là kế hoạch qualification. Trạng thái commercial GA vẫn là NO-GO.
