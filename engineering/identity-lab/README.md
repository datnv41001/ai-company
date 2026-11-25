# Lab Keycloak cho thiết kế vòng đời phiên AMC

Lệnh sau tạo một Compose project tên ngẫu nhiên, PostgreSQL riêng và Keycloak ghim image digest. Cổng HTTP chỉ lắng nghe loopback. Tài khoản, mật khẩu và realm tổng hợp được tạo mới cho mỗi lần chạy. Cuối phép thử, runner thu hồi đúng project và volume do nó tạo.

```sh
python -m pip install -r requirements-browser.txt 'httpx>=0.27,<1' 'PyJWT[crypto]>=2.10,<3'
python -m playwright install chromium
python engineering/identity-lab/run.py
```

Chromium đi qua trang đăng nhập của provider hai lần, trước và sau khi quản trị viên đổi mật khẩu. Client thử Authorization Code + PKCE, kiểm issuer, signature, audience, state, nonce và subject trước khi thử xoay refresh token. Dòng OBSERVED ghi chính xác khả năng refresh hiện hữu sau reset ở bản provider đang chạy. Runner sau đó yêu cầu logout và kiểm lần refresh kế tiếp. Kết quả chỉ áp dụng cho realm, image và cấu hình này. [Khởi chạy container](https://www.keycloak.org/server/containers) · [OIDC endpoints](https://www.keycloak.org/securing-apps/oidc-layers) · [Admin REST](https://www.keycloak.org/docs-api/latest/rest-api/index.html)

Logout tại provider và thu hồi phiên AMC là hai quyết định riêng. Các ca cần kiểm ở tầng AMC gồm liên kết tài khoản, logout nhiều worker, sự cố IdP, kiểm commit sau thu hồi, khôi phục backup và quyền workspace qua PostgreSQL. Spike chưa nối issuer này vào AMC. Rollback bằng bỏ job lab; runtime AMC tiếp tục dùng cấu hình hiện hành. Chọn IdP production còn chờ quyết định.
