# AMC · Bằng chứng hợp nhất phòng Marketing

| PR | Commit merge trên main | Tree | Hai parent (main, head) | CI sau merge |
|---|---|---|---|---|
| #45 | [`59949e24eea8cb4e3fcff1335aa57e8a16f78d09`](https://github.com/datnv41001/ai-company/commit/59949e24eea8cb4e3fcff1335aa57e8a16f78d09) | `6924d0d40655fab9f9fe62225bd514aa1e86b6e2` | `837ec9fc6c67868f5a88e263f06febc7d0ddf6bc`, `bea86a87ac82130d866ebc1d77018f7e85c7316f` | [526 đạt, 2 bỏ qua](https://github.com/datnv41001/ai-company/actions/runs/45738561950) |
| #46 | [`ee8ea9d5687834b1653134cc036a6729020a7c3e`](https://github.com/datnv41001/ai-company/commit/ee8ea9d5687834b1653134cc036a6729020a7c3e) | `ce6bd5fa3665672050b90f8d1b6b6b1540a887d6` | `59949e24eea8cb4e3fcff1335aa57e8a16f78d09`, `73d6240314e9a626998bf0adf59feabc8e899a4f` | [528 đạt, 2 bỏ qua](https://github.com/datnv41001/ai-company/actions/runs/45740557295) |
| #47 | [`bb678908b767481d051a1364c9247f55fd8d2e2a`](https://github.com/datnv41001/ai-company/commit/bb678908b767481d051a1364c9247f55fd8d2e2a) | `cd3efcb2d5798147e130c6258fe8c21e973a66b7` | `ee8ea9d5687834b1653134cc036a6729020a7c3e`, `3039a32d0da57f79a2566ce70d6464c58899b202` | [531 đạt, 2 bỏ qua](https://github.com/datnv41001/ai-company/actions/runs/45742479869) |
| #48 | [`380be3eb70a41424c6d45318b0b1890fa950970a`](https://github.com/datnv41001/ai-company/commit/380be3eb70a41424c6d45318b0b1890fa950970a) | `ae6cfcdef80d67650f7a245fe92431728ea0730c` | `bb678908b767481d051a1364c9247f55fd8d2e2a`, `16683d056486b7bba4f2396ebf2b9aad95ae79ce` | [537 đạt, 2 bỏ qua](https://github.com/datnv41001/ai-company/actions/runs/45744737771) |

## Tái lập

Mỗi PR có bản ghi JSON riêng cùng các job head, integration và post-merge. Thư mục junit chứa XML tải trực tiếp từ artifact GitHub, kèm SHA-256 trong JUNIT-INDEX.json. Tag `evidence/department-rehearsal-f1064d29` giữ cây trước migration của lần thử 533 bài và 18 ca giao nhau. Với PR #48, đối chiếu thêm cutover-final-local.json và bước native archive trong log API của CI.

Dữ liệu nghiệm thu là fixture. Commercial GA vẫn NO-GO.
