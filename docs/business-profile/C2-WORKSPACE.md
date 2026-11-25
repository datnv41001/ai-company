# Hồ sơ doanh nghiệp trong workspace

Đây là đặc tả giao diện và bộ ca nghiệm thu cho C2. Mốc tham chiếu là API C1 trong PR #22. Khi C1 được chấp nhận, ghi commit đã duyệt và đối chiếu các trường điều kiện, trạng thái tranh chấp và quyền phê duyệt với OpenAPI ở commit đó trước khi nối giao diện.

## Một doanh nghiệp, nhiều thương hiệu

Trong agency, một khách hàng đại diện một doanh nghiệp. Với Solo và đội Marketing nội bộ, dùng cùng quan hệ khách hàng–thương hiệu dưới workspace của họ. Tên pháp nhân và lĩnh vực đã có trên `Client`. Dùng cặp tenant/client làm chủ sở hữu hồ sơ chung. Mỗi thương hiệu tham chiếu hồ sơ chung thay vì sao chép hồ sơ sang một brand mặc định. Dữ kiện chung được biên tập qua revision cấp công ty có RLS và khóa đồng thời riêng. API C1 hiện yêu cầu brand trên mọi revision. Việc bổ sung scope công ty thuộc C2 và cần migration độc lập sau khi xác định thứ tự với Identity A1.

Trường được kế thừa hiển thị “Từ hồ sơ doanh nghiệp” cùng hành động “Điều chỉnh cho thương hiệu”. Giữ ba trạng thái kế thừa, ghi đè và chủ động để trống. Bỏ ghi đè trở về giá trị công ty đang có hiệu lực. Khi hiển thị kết quả, trả cả revision nguồn và revision ghi đè. Bản công ty mới chỉ ảnh hưởng lần đọc mới. Bản brief và snapshot đã ghim tiếp tục đọc revision cũ. Kiểm thử hai brand cùng client, hai client trong cùng tenant và cùng tên doanh nghiệp ở hai tenant. Mọi lệnh sửa hồ sơ doanh nghiệp phải qua backend kiểm tra quyền đúng scope.

## Từ lần đầu đăng nhập đến brief nháp

Trong workspace, liên kết “Hồ sơ doanh nghiệp” mở thẳng bộ chọn khách hàng và thương hiệu mà người dùng có quyền. Chỉ một lựa chọn thì chọn sẵn. Bốn trường thiết lập là “Tên doanh nghiệp”, “Sản phẩm hoặc dịch vụ”, “Khách hàng mục tiêu” và “Mục tiêu”. Cho lưu từng phần. Tiến độ đếm trường có giá trị đã lưu. Cảnh báo rõ khi người dùng vừa sửa và chưa lưu. Gợi ý hành động dựa trên dữ liệu còn thiếu, chẳng hạn bổ sung điều kiện bán trước khi dùng giá trong nội dung.

Nút “Tạo brief nháp” tạo bản làm việc nội bộ và ghim dữ liệu đã chọn, kèm danh sách câu hỏi còn trống. Solo có thể tạo nháp khi chưa có recipient, nguồn giá hoặc quyền chia sẻ. Endpoint Workforce hiện đòi recipient và brief đã nộp có nguồn. Tạo loại nháp chuẩn bị, lưu theo brand và người sở hữu. Chỉ chuyển sang hợp đồng Workforce khi các điều kiện C3 đã đủ. Thử lại cùng thao tác phải mở cùng bản nháp. Đo số WorkforceRun và số dòng ledger trước/sau để kiểm tra bước này.

## Các màn hình và quyết định người dùng

| Màn hình | Hành động | Kết quả cần nhìn thấy |
| --- | --- | --- |
| Sản phẩm và dịch vụ | Tìm theo tên/SKU, mở đúng biến thể, chỉnh offer và tình trạng hàng | Tiền tệ, đơn vị bán, số lượng cơ sở, MOQ, bậc, thuế, điều kiện, vùng/kênh và khoảng hiệu lực hiển thị cùng giá. Nhập số tiền theo đơn vị quen dùng, chuyển sang minor unit chính xác ở server. |
| Thời hạn và tranh chấp | Đối chiếu hai dòng còn hiệu lực, ghi lý do và lựa chọn có quyền | Hiển thị draft, có hiệu lực, hết hạn, bị thay thế, tranh chấp và bị thu hồi; phân biệt phê duyệt trước giờ bắt đầu với quyền sử dụng bây giờ. Sau quyết định, đọc lại trạng thái mới và giữ liên kết lịch sử. |
| Thương hiệu và đối tượng | Sửa giọng điệu, quy chuẩn, ICP và phân khúc | Phân biệt giả thuyết với dữ kiện có căn cứ, hiển thị thị trường, kênh, thời gian, nhóm người được khảo sát và phương pháp lấy mẫu khi liên quan. |
| Mục tiêu và KPI | Nối mục tiêu công ty, thương hiệu và chiến dịch; định nghĩa phép đo | Hiển thị đơn vị, mẫu số, kỳ, phương pháp, nguồn và người phụ trách. Baseline/target/actual chưa có dữ liệu được ghi “Chưa có số liệu”. |
| Nguồn và claim | Mở nguồn, chọn dòng hoặc vùng, đối chiếu nguyên văn và claim, gửi duyệt | Hai cột ở desktop, hai phần có tiêu đề liên tiếp ở mobile. Hiện tất cả qualifier và phạm vi cạnh câu sẽ sử dụng. Hiển thị người đủ quyền, lý do từ chối, lịch sử và các snapshot bị ảnh hưởng trước khi thu hồi. |

Đối với nội dung public đã duyệt, backend trả một projection cho editor gồm câu, điều kiện công khai, phạm vi áp dụng, thời hạn và trạng thái sử dụng hiện tại. Chỉ người có quyền đọc chứng cứ mới nhận excerpt, locator nội bộ, danh tính và ghi chú nhà cung cấp. Cắt dữ liệu tại server trước khi trả body. Portal tiếp tục dùng luồng bàn giao riêng. Khi chuyển tenant/client/brand, hủy tác vụ đang tải, xóa lựa chọn cũ và so thế hệ ngữ cảnh trước khi vẽ phản hồi. Kiểm cả response body và màn hình khi đổi tài khoản.

## Lưu nháp và khôi phục

Lưu nháp phía server theo actor và scope. Trước lần gửi đầu tiên, tạo một command key kèm expected revision. Giữ khóa cho đến khi nhận được kết quả chắc chắn. Khi mất phản hồi, đối chiếu hoặc thử lại nguyên lệnh, sau đăng nhập lại vẫn tìm được lệnh đang chờ. Một payload mới cần khóa mới. Trình duyệt chỉ giữ định danh nháp và lệnh trong phiên khi cần; nội dung nguồn hạn chế đặt ở server. Bản autosave hiển thị “Đã lưu” sau khi server xác nhận. Khi nhận 409, tải revision hiện tại, hiển thị khác biệt theo trường và giữ bản đang sửa. Người dùng có thể giữ bản server, áp dụng lại những trường đã chọn hoặc bỏ nháp. Khi quyền bị thu hồi, dừng mọi thao tác lưu và xóa phần dữ liệu đã hiển thị ở màn hình đó.

Luồng bàn phím đi từ ngữ cảnh tới mục danh sách, chi tiết và lưu. Đưa focus về lỗi đầu tiên; sau khi đóng hộp thoại, trả focus về nút mở. Ở 390 px, các bảng bằng chứng chuyển thành hàng có nhãn. Phân biệt đang tải, chưa có bản ghi, không có kết quả tìm kiếm, lỗi có thể thử lại và hết quyền. Tắt nút trong lúc gửi cùng kiểm idempotency tại server.

## Ma trận nghiệm thu qua trình duyệt

Chạy từng hàng hai lần qua Chromium 1280 × 850 và 390 × 844 với API trỏ PostgreSQL tổng hợp. Tạo tài khoản, workspace và grant bằng fixture hiện có. Thao tác cần nghiệm thu phải đi qua giao diện. Sau mỗi lần ghi, tải lại trong browser context mới, đăng nhập lại và đối chiếu dữ liệu server. Bảng này liệt kê ca cần chạy.

| Persona | Luồng và đối chứng | Bằng chứng quyết định |
| --- | --- | --- |
| Cửa hàng trực tuyến nhỏ | Điền hai trường, lưu, refresh, tạo brief nháp áo mưa size L khi chưa có giá; tiếp tục điền đủ bốn trường | Một draft; ghi rõ giá/audience còn thiếu khi phù hợp; số run và chi phí giữ nguyên. Ảnh sau khi mở lại brief. |
| Nhà cung cấp vật liệu B2B | Lập SKU, hai bậc giá theo m², chính sách thuế và MOQ; tạo hai quan sát kho trái nhau tại cùng địa bàn, đối chiếu rồi thu hồi một nguồn | Mức giá chỉ khớp đúng điều kiện; trạng thái tranh chấp chặn quyền mới; quyết định và lịch sử còn đọc được. Ảnh trước và sau giải quyết. |
| Doanh nghiệp dịch vụ | Thêm dịch vụ tại chỗ, hai địa bàn và hai kỳ hiệu lực; xem lịch khi giá tương lai chưa có hiệu lực | Đổi địa bàn/ngày đổi dữ liệu được phép dùng. Editor thấy câu công khai đã duyệt, response gửi tới editor không có excerpt hạn chế. |
| Agency nhiều khách | Tên SKU giống nhau ở hai client; đổi ngữ cảnh khi yêu cầu cũ đang tải. Hai thương hiệu của một client kế thừa tên công ty, chỉ một brand ghi đè | Phản hồi tới chậm không hiện dữ liệu client cũ. Không nhập lại thông tin chung. Kiểm riêng tài khoản portal. |
| Marketing nội bộ | Nhập một giả thuyết ICP, khai báo mục tiêu và KPI, mở hai tab sửa cùng trường; làm mất phản hồi sau một lần server đã lưu | Có đối chiếu khác biệt, một lần ghi cho mỗi ý định, bảo toàn bản nháp; giả thuyết và KPI chưa đo có nhãn rõ. |

Trong job C2 đính kèm ảnh sau các bước trên, SHA, viewport, schema, mã persona, kết quả đối chiếu API/DB và liên kết CI. Dữ liệu và tên trong ảnh phải là fixture. Ảnh một trang tĩnh hoặc một lần render không đủ để xác nhận luồng. Bộ ca thương mại mẫu dùng lại từ [C0](acceptance-cases.json). [Hợp đồng tiêu thụ dữ liệu ở C3](C3-KNOWLEDGE-PROJECTION.md).
