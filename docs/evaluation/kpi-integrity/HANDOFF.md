# Đối soát KPI lịch hẹn từ tri thức đến Sales

Người vận hành Marketing chọn phép đo đã được bộ phận dịch vụ hoặc Sales duyệt. Một biên tập viên viết bản cho khách; reviewer độc lập kiểm đúng phiên bản trước khi giao. Người đọc Analytics thấy tử số, mẫu số và tỷ lệ của cùng phiên bản KPI trên các sự kiện sandbox. Bản dùng cho phát triển nội bộ có hai phép đo lịch hẹn: **lịch do nhân sự xác nhận trên yêu cầu đặt lịch**, và **buổi đã hoàn tất trên lịch do nhân sự xác nhận**. Commercial GA vẫn NO-GO.

## Sử dụng

1. Trong **Tri thức → Danh mục Marketing → KPI**, chọn mục tiêu chiến dịch, tên, nguồn chứng cứ và định nghĩa phép đo. Chọn cặp biến cố, số ngày và bộ phận đối soát. Lưu nháp, kiểm nội dung, phê duyệt qua luồng tri thức sẵn có. Ô “KPI mô tả” tiếp tục phục vụ các chỉ số chưa có hợp đồng. Định nghĩa cấu trúc sinh cách đo, kỳ, đơn vị và người chịu trách nhiệm.
2. Trong **Brief nháp → Chọn dữ liệu từ danh mục**, chọn đúng KPI của chiến dịch cùng sản phẩm, đối tượng và mục tiêu. Lưu brief mới. Khi lập manifest WF-03/WF-13, chọn lại đúng bản KPI đã ghim. Máy chủ kiểm ID, digest, revision, quyền đọc và chuỗi phê duyệt. Một KPI của campaign khác, một revision khác, hoặc brief thiếu pin đều bị từ chối.
3. Tạo và duyệt kế hoạch từ manifest. Director, Research và Strategy chỉ nhận thuật ngữ KPI cần dùng; ID kỹ thuật được giữ trong biên nhận nội bộ. Content và SEO dùng dữ kiện công khai của offer. Tài sản trong Studio, phần đo gửi khách và đề xuất quảng cáo đều nhận định nghĩa của kế hoạch. Sửa sai mẫu số, chuyển KPI chính vào một câu ngoài trường đo hoặc thêm một mệnh đề trái phép đo sẽ làm mất điều kiện ký. Câu KPI phụ đã được định nghĩa về số phiên web có thể giữ riêng ở dòng thứ hai. Phần mềm chỉ kiểm tra cấu trúc cố định và một số cách gọi tỷ lệ Việt/Anh; reviewer vẫn chịu trách nhiệm với diễn giải mới.
4. Trong **Chiến dịch → Điều hành chiến dịch → Phân tích**, chọn chiến dịch đã có phiên bản kế hoạch được duyệt. Tỷ lệ và số ca thiếu nguồn chỉ tính trong kỳ KPI của kế hoạch. Phiên web hiển thị ở dòng chỉ số phụ. Khi mẫu số bằng 0, hiển thị “Chưa có mẫu số”. API sandbox cho phép đọc lại phép đo của kế hoạch cũ cùng campaign bằng query `measurement_plan_id`.

## Hợp đồng và dữ liệu

Một ví dụ input của bản KPI thuộc một mục tiêu campaign cụ thể (thay các tham chiếu bằng ID thật trong workspace thử):

```json
{
  "name": "Lịch khảo sát được nhân sự xác nhận",
  "objective": "<exact approved campaign objective revision>",
  "source": "<scoped measurement source revision>",
  "measurement": {
    "version": "appointment-measurement/1",
    "business_outcome": "appointment.confirmed_per_requested",
    "window_days": 21,
    "owner_role": "service_operations"
  }
}
```

Bản ghi tri thức bất biến là nguồn của ID, revision và SHA-256. Sau phê duyệt, contract chứa biến cố/điều kiện tử và mẫu, kỳ UTC, đơn vị tỷ lệ, phép đếm mã hẹn duy nhất, xử lý hủy/vắng mặt/hoàn tiền, xử lý thiếu attribution, owner và phép đối soát. Sự kiện yêu cầu hợp lệ đòi hỏi sự đồng ý và phạm vi dịch vụ. Xác nhận đòi hỏi thời điểm được nhân sự xác nhận. Hoàn tất đòi hỏi người được giao xác nhận. Các điều kiện được kiểm tại luồng ghi CRM. Phép đo đọc lại lịch sử các chuyển trạng thái có quyền.

Mẫu số lấy các mã có biến cố gốc trong cửa sổ `(as_of − window_days, as_of]`. Tử số là tập con đã đạt biến cố kết quả vào hoặc sau biến cố gốc và không muộn hơn thời điểm chốt. Ca hủy sau xác nhận vẫn từng đạt xác nhận. Hủy, vắng mặt và thiếu nguồn được ghi riêng. Hoàn tiền không thay đổi một tỷ lệ đếm lịch. Nhiều sự kiện trên cùng mã chỉ tạo một đơn vị. Các chỉ số tổng quan chiến dịch trước đây có phạm vi toàn campaign; `report.primary_measurement` ghi rõ kế hoạch, cutoff, hai tập đếm và KPI phụ trong cùng kỳ.

## Phép thử nghiệp vụ

- **Luồng Rõ.** Bản đo cũ ở #45 được trích từ archive đã xác minh SHA-256; trước bản sửa, renderer trên `f1064d29` tái tạo đúng hai câu sai về “lượt vào”. Tệp lưu cả dữ kiện, hai câu trước sửa và hash file nguồn. Hai renderer và cổng ký hiện đối chiếu với một định nghĩa của KPI đã duyệt. [Dữ liệu gốc đã khóa](../../../tests/evaluation/kpi_integrity/luong-ro.json)
- **Mực Chuẩn.** Holdout ghi trước ở commit `88259c1`. Trong 14 ngày, một buổi hoàn tất trên ba lịch đã xác nhận. Ca sát biên đầu bị loại; ca tại cutoff được nhận; hoàn tất sau cutoff chưa được tính. Ca hủy vẫn nằm trong mẫu số, không có attribution vẫn được tính. Kiểm riêng với phiên của campaign khác và một xác nhận lặp cùng mã. [Holdout và năm đột biến](../../../tests/evaluation/kpi_integrity/holdout.json)
- **Giá trị đối với người dùng.** Sales nhìn thấy tỷ lệ 2/3 ở Luồng Rõ và 1/3 ở Mực Chuẩn dù số lượt web được ghi bằng 0 trong hai hành trình API. Ba trường cuối đã sửa sai bị API từ chối ký và người nhận chỉ nhìn thấy bản đã sửa. Việc tái sử dụng một mệnh đề chỉ số phụ được định danh là kiểm hồi quy biên tập. Không có lượt inference mới. Bản QA/nhận tài liệu trong thử nghiệm dùng danh tính tổng hợp và quyền thật ở API.
- [Kết quả và giới hạn](RESULTS.md) · [Gói thực hành RFQ/dịch vụ của PR #45](https://github.com/datnv41001/ai-company/tree/bea86a87ac82130d866ebc1d77018f7e85c7316f/docs/evaluation/department-study/PILOT-KIT)

## Chạy và tiếp quản

Từ root với môi trường dev của repo, chạy `python -m pytest -q tests/test_measurement_integrity.py tests/test_measurement_edition.py`. Các test dựa trên API được parametrized SQLite và PostgreSQL có RLS theo runbook. Cần database `amc_test_*` disposable, đã chạy migration và login runtime giới hạn quyền khi đặt `AMC_TEST_PG=1`. Đặt `AMC_KPI_EVIDENCE` thành thư mục trống để lưu trace. Đặt thêm `AMC_KPI_BROWSER` khi chạy ca Luồng Rõ trên PostgreSQL để mở Chromium với origin thật, lưu hình desktop/tablet/mobile ở hai theme. Có thể chọn Chromium cài sẵn qua `AMC_BROWSER_EXECUTABLE`. Không có nhu cầu tải model, mua thiết bị hay dùng tài khoản trả phí.

Thiết kế dùng JSON versioned trong Knowledge, manifest, plan và Studio. Bảng DB, snapshot cũ và bản khách đã nhận giữ nguyên. Với hồ sơ lịch hẹn chưa có hợp đồng, bản mới yêu cầu xác minh KPI và tránh tự gán mẫu số. Khi quay lại bản cũ, dừng writer mới, lưu backup và khóa công việc có brief KPI bốn slot. Predecessor yêu cầu đúng ba slot nên không recheck được manifest mới. Phục hồi một cặp binary–database đã kiểm tra tương thích trước khi tiếp tục tác vụ trên hồ sơ đó. Không hạ version từng dòng và không sửa lịch sử khách.

**Đề nghị reviewer thách thức.** Đổi riêng số ngày hoặc mẫu số trong bản đã biên tập, thêm một câu thay KPI chính ở phần quảng cáo, chọn KPI khác lúc materialize, chốt cửa sổ đúng thời điểm hủy rồi thử mẫu số 0. Đối chiếu revision, biên nhận phủ nhận, tử/mẫu thực và bản portal cuối. Đo thời gian/chi phí thực cùng người dùng trước khi đánh giá hiệu quả nghề nghiệp.

Đề xuất tối ưu lưu báo cáo, mốc chốt kỳ đo, phiên bản kế hoạch và mã băm các dữ kiện CRM đã dùng. Khi người thứ hai duyệt, hệ thống đối soát cùng mốc. Chỉ thời gian trôi qua vẫn cho phép duyệt. Nếu dữ liệu đầu vào đã thay đổi thì tạo đề xuất mới dù tỷ lệ tổng hợp vẫn bằng nhau. Với đề xuất cũ chưa có mã băm nguồn, hệ thống tiếp tục đối soát nội dung báo cáo đã lưu.

Khi trang đích đã duyệt tạo lượt vào và form, hệ thống ghi hai nguồn riêng cho lịch hẹn. [Quy tắc đối chiếu và bằng chứng thấy được trên desktop, tablet và mobile](../real-production/landing-attribution/README.md)
