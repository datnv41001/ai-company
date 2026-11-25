# Mốc main dùng cho Business Profile C1

Các nhánh sản phẩm, danh tính và công cụ AIRC dùng cùng base `16fea3d45aff62dc4ba80243fcf0791627ffb90f`, schema v21. Các SHA bên dưới định danh đúng lượt tích hợp đã chạy trên GitHub. Git tree và hai commit cha của từng bản merge trùng với bản integration tương ứng.

| PR | Head đã tích hợp | Integration đã kiểm thử | Merge SHA | Git tree | CI sau merge |
| --- | --- | --- | --- | --- | --- |
| [#18 · thiết kế Business Profile](https://github.com/datnv41001/ai-company/pull/18) | `8c504c9144a17b8a673060ea60c78d17e8f0030d` | `ec04c668da160334f8398537cf58113e24bd197b` | `c8d479cff6eeff398c7d542288eb8825b7a9e02e` | `4bd8c6da05a0169bb9c0be6e75a8306cab76968a` | [Actions](https://github.com/datnv41001/ai-company/actions/runs/45433640196) |
| [#19 · giới hạn thao tác danh tính](https://github.com/datnv41001/ai-company/pull/19) | `d152a1c2d923829b92350ebcffac6a23790016a1` | `e3ea81603985a712f3052e51fd4e8e1e461ef332` | `a9bdc2399bfce6a608c747288dd33a3ae63b9224` | `7c4068a0b33bd14d23c80d6781c492197b68daef` | [Actions](https://github.com/datnv41001/ai-company/actions/runs/45435122922) |
| [#20 · nghiên cứu AIRC](https://github.com/datnv41001/ai-company/pull/20) | `0f5ec0b0719a9815eb996d221e3d51b55d69762f` | `4a4e627ffa66caf9c6946e1b3c85fdafbf176555` | `16fea3d45aff62dc4ba80243fcf0791627ffb90f` | `f95a1f4c05a2816620bfe3f62578a5160a89095f` | [Actions](https://github.com/datnv41001/ai-company/actions/runs/45436500101) |

Trước khi merge, #18 đạt 11/11 job. #19 đồng bộ với #18 rồi đạt 9/9 job. #20 đồng bộ với #19 rồi đạt 11/11 job. Bằng chứng gồm ứng dụng trên head và integration, cùng lượt phát lại archive và phép kiểm cô lập khi thay đổi AIRC. [Integration #18](https://github.com/datnv41001/ai-company/actions/runs/45421535440) · [Integration #19](https://github.com/datnv41001/ai-company/actions/runs/45433794407) · [Integration #20](https://github.com/datnv41001/ai-company/actions/runs/45435307681) · [AIRC replay](https://github.com/datnv41001/ai-company/actions/runs/45435307736) · [Linux containment](https://github.com/datnv41001/ai-company/actions/runs/45435308142)

C1 thử schema v22 trên database dùng riêng. Kiểm thử native ở mốc C1 ghi nhận kết quả `SHOW server_version` là PostgreSQL 16.16. Compose của AMC ghim image PostgreSQL 16.6. Khôi phục C1 bằng backup v21 và code đúng mốc v21, đối soát mọi thay đổi phát sinh từ thời điểm backup trước khi chuyển dữ liệu. Các pool có sẵn trên máy không tham gia diễn tập.
