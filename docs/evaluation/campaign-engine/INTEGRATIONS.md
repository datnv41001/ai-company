# Bốn bản tích hợp nền trên main

Đối chiếu kết quả trên commit của pull request và trên commit merge. Ở mỗi hàng, parent thứ nhất là main trước khi merge, parent thứ hai là head được kiểm thử. GitHub tạo SHA merge mới nhưng giữ cùng tree và đúng thứ tự hai parent của bản tích hợp đã chạy CI.

## PR #40

- Parent main `220d7aa11914d1f732415478b00a230c37d6f36f`
- Parent head `159afde2a56e61722db49a08b14724af63d74ec8`
- Commit tích hợp `ed1299218c67a1eb825da4129060886961f9bb6c`
- Commit merge trên main `e8ec9b663128b25f100694a04043517fb40b6aa4`
- Tree chung `aee57843223dcb597c74635ba354979392683926`
- CI của bản tích hợp đạt 485 test, 2 bỏ qua, 22 đường nâng cấp có dữ liệu và restore 34 bảng. [PR #40](https://github.com/datnv41001/ai-company/pull/40) · [CI trên head](https://github.com/datnv41001/ai-company/actions/runs/45605536645) · [CI PR và bản tích hợp](https://github.com/datnv41001/ai-company/actions/runs/45606308053) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45613109238)

## PR #43

- Parent main `e8ec9b663128b25f100694a04043517fb40b6aa4`
- Parent head `ff71c226f27f7d78fff3fca18371a28eb289720b`
- Commit tích hợp `db944e024d8f7621aa0199fa0daf1aa75030b2d3`
- Commit merge trên main `e45b369a7d67b833da1e34ef0017f4f9dc80229c`
- Tree chung `b00bc108fcb09d9585c04509890d21f4983bcfb0`
- CI của bản tích hợp đạt 491 test, 2 bỏ qua, 22 đường nâng cấp có dữ liệu và restore 34 bảng. [PR #43](https://github.com/datnv41001/ai-company/pull/43) · [CI trên head](https://github.com/datnv41001/ai-company/actions/runs/45614049444) · [CI PR và bản tích hợp](https://github.com/datnv41001/ai-company/actions/runs/45614062063) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45616653453)

## PR #41

- Parent main `e45b369a7d67b833da1e34ef0017f4f9dc80229c`
- Parent head `639904f32334d6f67c4e16a904de2f18758b7e5a`
- Commit tích hợp `8ef7f8c43d231c6826e29fa883bf01636081f9ce`
- Commit merge trên main `99a7bf34ca92c9081157e99299a5a384c34f8afc`
- Tree chung `2f0f0d5bbd8fa2db018ebe1524aa304189c1fa76`
- CI của bản tích hợp đạt 497 test, 2 bỏ qua, 22 đường nâng cấp có dữ liệu và restore 34 bảng. [PR #41](https://github.com/datnv41001/ai-company/pull/41) · [CI trên head](https://github.com/datnv41001/ai-company/actions/runs/45616698184) · [CI PR và bản tích hợp](https://github.com/datnv41001/ai-company/actions/runs/45616706310) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45619084073)

## PR #42

- Parent main `99a7bf34ca92c9081157e99299a5a384c34f8afc`
- Parent head `398e9325cf62a15a29c42f02f731c9d61bba40ca`
- Commit tích hợp `77b0f7014309723db17ff9d164de2c5ddd42b721`
- Commit merge trên main `1b9e3a9643014122d4c6e510efffc3d02b9843cf`
- Tree chung `2adb084c45fae22ba3fd44d71ea4b112830ffcdb`
- CI của bản tích hợp đạt 501 test, 2 bỏ qua, 22 đường nâng cấp có dữ liệu và restore 34 bảng. [PR #42](https://github.com/datnv41001/ai-company/pull/42) · [CI trên head](https://github.com/datnv41001/ai-company/actions/runs/45619165400) · [CI PR và bản tích hợp](https://github.com/datnv41001/ai-company/actions/runs/45619182455) · [CI sau merge](https://github.com/datnv41001/ai-company/actions/runs/45621758867)

Hồ sơ JSON ghi job ID, checkout, parent, tree, kết quả từng đường nâng cấp và biên bản C3 v4. Campaign Lab của #41 là fixture cố định. Đợt #42 là nghiên cứu ngoại tuyến. [Dữ liệu đối chiếu](integrations.json)
