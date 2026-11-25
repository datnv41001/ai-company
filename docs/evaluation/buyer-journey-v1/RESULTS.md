# Composer theo hành trình mua · Hồi quy biên tập tiếng Việt

Bộ phận Marketing cần quyết định người mua sẽ làm gì sau khi đọc và ai chịu trách nhiệm tiếp nhận. Ví dụ, nhà thầu yêu cầu báo giá theo số thanh cần cung cấp số lượng và địa bàn. Sales cần mã RFQ để đối soát một báo giá. Một lượt gửi form chưa xác nhận doanh thu.

Ứng viên nội bộ dùng những trường đã tạo bởi composer tất định hiện hành trên đúng projection lúc chạy. Sau đó nó đề xuất cách đặt câu hỏi, thử nội dung và đo bước tiếp theo theo bảy loại hành động và đơn vị bán của brief. Sản phẩm vật liệu dùng thử mẫu hoặc RFQ, dịch vụ theo máy dùng lịch hẹn, lớp thực hành tính theo người dùng đăng ký, kênh đại lý có luồng tải danh mục và RFQ theo hộp. Phân loại này là giả thuyết biên tập giới hạn trong bộ dữ liệu. Cần chuyên viên xác nhận cách chọn playbook trước khi đưa vào Studio. [Playbook dùng trong phép thử](../../../tests/evaluation/c3/buyer_journey_playbooks.py)

## Kết quả đối chiếu 10 brief đã mở

| Phép đo | Kết quả |
| --- | --- |
| Nguồn dữ liệu | 10 file kết quả gốc ở commit tích hợp `a2dbe456`, mỗi file khớp SHA-256 đã lưu trong nghiên cứu. 30 lần thử model trong lịch sử. |
| Composer tất định trước và sau | 10/10 cặp so sánh ngoại tuyến. Giữ 95/95 trường, sửa 60 trường văn bản. |
| So với phiên bản có Qwen | 8/10 cặp có bản model, gồm 73 trường. Hai lần Director dừng ở v2-05 và v2-07 vẫn nằm trong mẫu số. Hai ứng viên soạn từ control tất định ở các ca này chỉ là đầu ra của thử nghiệm biên tập ngoại tuyến. |
| Giữ dữ kiện | Cả 10 khối điều kiện thương mại/nghiên cứu giữ nguyên văn. Scorer hiện hữu đối chiếu được 120/120 phép kiểm trên **khối điều kiện** của ứng viên. Trong nghiên cứu cũ, hai ca thiếu bản model vẫn thiếu bằng chứng trên bề mặt giao khách. |
| Sửa có giới hạn | Trên cả năm trang đích, câu lợi ích do model đề xuất chưa khớp nguyên văn khai báo có điều kiện. Mỗi ca thay trường đó một lần bằng dòng nguồn đã khóa. Báo cáo lưu cả câu cũ, lý do và mã nguồn. Một diễn đạt khác nguồn có thể đúng ý; quyết định của bộ lọc không chứng minh câu ấy sai. |
| Nghiệm thu | Không có lời gọi model mới, chi phí nhà cung cấp mới bằng 0. Chưa có phép đo thời gian lao động, tiền máy, chi phí trên bản được duyệt hay khả năng dùng ngay của chuyên viên. |

Với v2-04, bản Qwen từng cam kết hoàn thiện đúng thời hạn. Ứng viên giữ nguyên giá, lượng tối thiểu và điều kiện cắt vật liệu. Người đọc nhận lời hướng dẫn gửi số lượng và địa bàn. Với v2-03, chiến lược thử bảng so mẫu theo vị trí lắp đặt rồi chuyển yêu cầu cho phụ trách vật liệu. Người chấm nên kiểm tra liệu hướng dẫn này có giảm việc hỏi lại và liệu có loại bỏ một ý hay của bản model. Từng cặp bản đầy đủ, gồm cả trường bị thay và loại phát biểu, nằm trong [kết quả máy đọc được](REGRESSION.json). Các đầu ra đều là bản nội bộ chờ nghiệp vụ và kiểm chứng quyền sử dụng.

Các chỉ số trên mô tả độ phủ trường, bám nguồn có cấu trúc và cách triển khai. Điểm lịch sử của reviewer AI vẫn là 0/8 bản model và 2/8 bản tất định dùng được ngay. Bộ 10 ca đã được đọc khi xây ứng viên nên cần bộ mới, chấm mù, để đo lợi ích thực. [Nghiên cứu và điểm lịch sử](../c3-product-v2/RESULTS.md)

## Cơ sở phương pháp và phép thử kế tiếp

Google Analytics mô tả hành động tạo lead và giao dịch mua bằng các sự kiện khác nhau. Trong thử nghiệm này, RFQ được đo bằng yêu cầu đủ thông tin rồi mới đối soát đơn. Với mua hàng, loại đơn hủy và theo dõi khoản hoàn. Đây là đề xuất đo lường, chưa có tracking triển khai hoặc chứng cứ tăng chuyển đổi. [Tài liệu sự kiện Google Analytics](https://developers.google.com/analytics/devguides/collection/ga4/reference/events)

Google Search Central khuyến nghị mô tả ngắn tóm tắt đúng nội dung trang. Trong phép thử, metadata lấy câu mô tả có phạm vi và thao tác khớp với trang. Chuyên viên cần chấm tính tự nhiên, khả năng phân biệt trang và giá trị cho từng truy vấn. Google quyết định nội dung snippet thực tế. [Google Search Central](https://developers.google.com/search/docs/appearance/snippet)

Bước tiếp theo là cho biên tập viên xem đề xuất ở một revision cụ thể, thay đổi hoặc bỏ qua từng trường, rồi chạy lại QA và quy trình phê duyệt của Studio. Giữ nội dung sáng tạo có giá trị, nguồn hạn chế và quyết định chia sẻ thuộc đúng phạm vi. Khi có chuyên viên, dùng brief mới tương đương độ khó, đo cả thời gian làm rõ, biên tập, QA, đầu ra bị từ chối và chi phí. [Giao thức pilot](../C3-PRACTITIONER-KIT.md)

## Chạy lại từ máy khác

Trong artifact `pool-model-measurements-integration` của run bên dưới, thư mục `c3-product-v2` chứa `v2-01/result.json` tới `v2-10/result.json`. Cài môi trường phát triển theo HANDOFF rồi chạy từ gốc repository. Đổi `PATH_TO_ARTIFACT` thành thư mục đã giải nén. [GitHub Actions và artifact gốc](https://github.com/datnv41001/ai-company/actions/runs/45582688602)

```sh
python tests/evaluation/c3/grounded_composer_study.py PATH_TO_ARTIFACT/c3-product-v2 --out runs/buyer-journey.json
python -m pytest -q tests/test_grounded_composer_study.py tests/test_product_qualification_summary.py
```

Để kiểm tra cả ba series của lần chạy gốc và tạo bản nghiên cứu mới trong cùng lệnh:

```sh
python tests/evaluation/c3/product_qualification_summary.py PATH_TO_ARTIFACT --checkout a2dbe4566415fe28226b014ffb8785a1cc2cd9d6 --require-complete --out runs/original-summary.json --buyer-journey-out runs/buyer-journey.json
```

CI chạy kiểm thử dữ liệu tổng hợp, kiểm tra mẫu số và bảo vệ trường. Đối chứng đầy đủ cần artifact gốc. Báo cáo được đóng băng khi còn đọc được artifact để có thể tiếp tục review trên máy khác. Runtime, workflow đã phát hành và bước chia sẻ tài sản với khách không nhận đầu ra của thử nghiệm. Commercial GA tiếp tục NO-GO.
