# Chạy pool trên máy phát triển

PR #5 dùng schema PostgreSQL v9. Chuẩn bị Git, Python 3.12, Docker Engine và Compose v2. Từ thư mục repo, thực hiện phần khởi động Docker trong HANDOFF.md. Sao lưu database và thử khôi phục trên một database tách biệt trước khi nâng một bản có dữ liệu.

## Khởi động

```sh
python scripts/init_env.py
docker compose -p amc-dev up -d --build db migrate api
python scripts/init_pool.py --project amc-dev
python scripts/fetch_workforce_model.py
docker compose -p amc-dev --env-file .env --env-file .env.pool -f compose.yaml -f compose.pool.yaml --profile local-model up -d --build model dispatcher worker-one worker-two
```

Script init_pool ghi ba mật khẩu riêng vào .env.pool và cấp LOGIN bằng service migrate. Chuyển mã và tài liệu qua Git. Khi di chuyển cả volume, khôi phục database, role PostgreSQL và tệp bí mật tương ứng qua kênh riêng. Với database mới, tạo bộ mật khẩu mới. Gateway pool dùng Qwen trên mạng nội bộ Compose. Mỗi worker chỉ nhận DSN của chính nó.

## Đưa agency vào pool

1. Tạm dừng gửi brief mới trong agency. Chờ worker v8 xử lý hết các run queued và running. Gọi `PUT /api/tenants/{tenant}/operations/budget` bằng tài khoản owner/admin với `{"ceiling":1000,"capacity":2,"enabled":true}`. Xem các endpoint và đăng nhập thử tại `/docs`. Mức tiền dùng micro-USD. Mỗi tháng UTC cần đặt hạn mức cho kỳ mới. API trả 409 khi agency còn run legacy đang hoạt động.
2. Tạo client, brand, campaign, editor và grant cho khách qua giao diện hoặc API hiện có. Đăng ký từng campaign được phép cho mỗi worker. Ví dụ dưới đây dùng tên biến minh họa, thay bằng ID của dữ liệu thử. Với một worker phục vụ nhiều campaign, chạy lại lệnh cho từng bộ ID.

   ```sh
   docker compose -p amc-dev run --rm --no-deps migrate python scripts/provision_pool.py route amc_ops_one TENANT CLIENT BRAND CAMPAIGN EDITOR
   docker compose -p amc-dev run --rm --no-deps migrate python scripts/provision_pool.py route amc_ops_two TENANT CLIENT BRAND CAMPAIGN EDITOR
   ```
3. Gửi brief và tạo run như ở PR #4. Dispatcher chọn campaign động. Mở mục **Điều hành agency** để kiểm tra kỳ, hạn mức, số đang giữ, số đã ghi chi, số lượt và trạng thái. Nhấn **Cập nhật số liệu** để đọc lại. Khách hàng truy cập bản chia sẻ qua cổng duyệt hiện có. Kiểm tra QA revision, digest và quyết định khách bằng màn hình bàn giao.

## Đối soát

Một attempt giữ ngân sách trước khi worker nhận việc. Khi đã gửi và mất kết nối hoặc bị thu hồi, khoản giữ chờ đối soát. Gọi `POST /api/tenants/{tenant}/operations/attempts/{uuid}/receipts` với `{"amount":350,"receipt":"provider-receipt-1"}` ở quyền owner/admin. amount là tổng phí xác nhận cho attempt. Lặp đúng chứng từ được chấp nhận một lần về tài chính. Để sửa sai, thêm chứng từ điều chỉnh mới với số tuyệt đối và lưu chứng từ ở hệ thống tài chính của agency. Đối soát ghi vào kỳ của attempt. Nếu vượt hạn mức, số đã ghi chi vẫn phản ánh phí thực tế. Model local dùng giá 0. Bài test kế toán dùng số giả lập 700/1.000.

Kiểm chứng bằng tài khoản migration trên database thử nghiệm. Hai truy vấn chỉ đọc sau cho biết một login đã xử lý bao nhiêu campaign và cách số dư hình thành.

```sql
SELECT a.worker, count(DISTINCT t.campaign) campaigns, count(*) attempts
FROM amc_ops.attempts a JOIN amc_ops.tasks t USING(run,step) GROUP BY a.worker;
SELECT tenant,month,sum(held) held_microusd,sum(spent) spent_microusd
FROM amc_ops.ledger GROUP BY tenant,month;
```

## Khôi phục

Để tạm dừng việc mới, dừng dispatcher. Worker đang suy luận có thể báo kết quả đến khi lease hết hạn. Khởi động lại dispatcher để ghi kết quả, thu hồi lease hết hạn và tiếp tục giới hạn ba lần thử. Khi chuyển về legacy, tạm dừng enqueue, chờ pool xử lý xong các run còn mở, đối soát khoản chưa xác nhận, đặt enabled=false, rồi chạy worker legacy cho run mới. Giữ schema v9 để bảo toàn ledger và snapshot. Rollback toàn database dùng bản backup đã thử khôi phục và cùng phiên bản ứng dụng, sau khi xuất bằng chứng phát sinh kể từ backup.

## Nghiệm thu

Chạy Ruff và pytest với môi trường PostgreSQL thử `amc_test*`. Các biến cần thiết và lệnh tạo database nằm trong .github/workflows/ci.yml. Job api-tests kiểm tra SQLite, PostgreSQL, 8 đường migration và tính lặp; compose-browser kiểm tra desktop/mobile; workforce-model chạy Qwen thật, bao gồm A/B/C với hai LOGIN. Artifact pool-model-measurements chứa loại lỗi, số lượt, tỷ lệ lần đầu theo tử/mẫu, và phần token chưa xác nhận. Bộ test dùng tài khoản và brief tổng hợp. Khâu duyệt nội dung thật vẫn thuộc trách nhiệm người QA. Khả năng chịu tải ở quy mô thương mại và đối soát nhà cung cấp trả phí cần nghiệm thu riêng.
