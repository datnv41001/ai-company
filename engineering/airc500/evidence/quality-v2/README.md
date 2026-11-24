# Kết quả 100 lượt review Qwen 0.5B trên fixture

Bảng điểm dùng hai cohort tổng hợp, một checkpoint Qwen2.5-0.5B-Instruct Q4_K_M và hai seed 17/43. Mỗi case chạy lại với seed khác có cùng nhãn. Mỗi nhánh tái dùng lượt mù chung, nên chỉ số participation đếm theo receipt duy nhất. So sánh một reviewer với hai reviewer ở cùng số lượt. Vòng tranh luận cần thêm thời gian và token. [Thiết kế, nguồn nhãn và giới hạn mẫu](../../QUALITY-EVALUATION.md).

GGUF SHA-256 `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db`, revision model `9217f5db79a29953eb74d5343926648285ec7e67`. Mỗi cohort dùng một key adapter và một key verifier theo hai vai trò trên cùng host tin cậy. Chữ ký cho phép kiểm tra nguồn output.

Trong bảng, TP là lỗi được phát hiện đúng, FP là cảnh báo nhầm, FN là lỗi bỏ sót và TN là ca sạch được giữ. Giải thích và hướng sửa chấm riêng trên các TP. Tổng giây gọi model cộng thời gian thực của từng attempt. Cột thời gian chỉ tính các lượt gọi model. Hai cohort có thể chạy song song trên cùng máy.

Hai cohort có tổng cộng 13 ID reviewer khác nhau. Các lượt mù bao gồm cả lượt lặp cùng ID cho nhánh đối chứng.

**Marketing.** seed 17 có 36 TP với verifier thuần, hội đồng cuối đạt 21 TP và 0 FP, 0/21 hướng sửa đúng, hai vòng trao đổi ghi nhận 0 lượt TP chuyển vào tập đang xét. seed 43 có 36 TP với verifier thuần, hội đồng cuối đạt 22 TP và 0 FP, 0/22 hướng sửa đúng, hai vòng trao đổi ghi nhận 0 lượt TP chuyển vào tập đang xét.

**Danh tính.** seed 17 có 8 TP với verifier thuần, hội đồng cuối đạt 7 TP và 0 FP, 0/7 hướng sửa đúng, hai vòng trao đổi ghi nhận 0 lượt TP chuyển vào tập đang xét. seed 43 có 8 TP với verifier thuần, hội đồng cuối đạt 7 TP và 0 FP, 0/7 hướng sửa đúng, hai vòng trao đổi ghi nhận 0 lượt TP chuyển vào tập đang xét.

## 96 ca Marketing, scope và đếm trùng

Git fixture `cd727a0fc56e67b9f4d2c307a492bbde12dbf2fa` → `952055df5aa813184b7cfab199d4a371a59910b6`. Hai seed dùng 11 ID thực sự nhận receipt (AR-002, LC-012, MK-022, MK-023, MK-025, MK-052, MK-053, MK-054, MK-055, QT-032, QT-033), 80 lượt ký hợp lệ, 112,894 token đầu vào và 14,102 token đầu ra. Chi phí API trả ngoài bằng 0 µUSD.

[Số liệu đầy đủ](marketing/metrics.json) · [Lịch sử từng finding và domain](marketing/trace.json.gz) · [Journal seed 17](marketing/seed-17.json.gz) · [Journal seed 43](marketing/seed-43.json.gz)

| Seed | Cấu hình | TP / FP / FN / TN | Precision | Recall | FPR | Giải thích đúng / TP | Hướng sửa đúng / TP | Lượt | Input / output token | Tổng giây gọi model |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | Verifier | 36 / 0 / 12 / 48 | 100.0% | 75.0% | 0.0% | 36/36 | 36/36 | 0 | 0 / 0 | 0.0 |
| 17 | Một reviewer, hai lượt | 48 / 48 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/48 | 0/48 | 16 | 20,412 / 2,827 | 308.8 |
| 17 | Hai reviewer độc lập | 48 / 48 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/48 | 0/48 | 16 | 20,408 / 2,826 | 290.5 |
| 17 | Một reviewer + verifier | 15 / 0 / 33 / 48 | 100.0% | 31.2% | 0.0% | 0/15 | 0/15 | 16 | 20,412 / 2,827 | 308.8 |
| 17 | Hội đồng + verifier | 21 / 0 / 27 / 48 | 100.0% | 43.8% | 0.0% | 0/21 | 0/21 | 32 | 46,260 / 5,658 | 657.2 |
| 43 | Verifier | 36 / 0 / 12 / 48 | 100.0% | 75.0% | 0.0% | 36/36 | 36/36 | 0 | 0 / 0 | 0.0 |
| 43 | Một reviewer, hai lượt | 48 / 48 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/48 | 0/48 | 16 | 20,412 / 2,799 | 360.9 |
| 43 | Hai reviewer độc lập | 48 / 48 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/48 | 0/48 | 16 | 20,408 / 2,822 | 364.2 |
| 43 | Một reviewer + verifier | 14 / 0 / 34 / 48 | 100.0% | 29.2% | 0.0% | 0/14 | 0/14 | 16 | 20,412 / 2,799 | 360.9 |
| 43 | Hội đồng + verifier | 22 / 0 / 26 / 48 | 100.0% | 45.8% | 0.0% | 0/22 | 0/22 | 32 | 46,222 / 5,654 | 742.4 |

| Seed | Giai đoạn hội đồng | TP / FP | TP thêm / mất | FP bỏ / thêm | Chưa phát hiện |
|---:|---|---:|---:|---:|---:|
| 17 | Mù | 48 / 48 | 48 / 0 | 0 / 48 | 0 |
| 17 | Phản biện | 48 / 48 | 0 / 0 | 0 / 0 | 0 |
| 17 | Trọng tài | 48 / 48 | 0 / 0 | 0 / 0 | 0 |
| 17 | Xác minh cuối | 21 / 0 | 0 / 27 | 48 / 0 | 27 |
| 43 | Mù | 48 / 48 | 48 / 0 | 0 / 48 | 0 |
| 43 | Phản biện | 48 / 48 | 0 / 0 | 0 / 0 | 0 |
| 43 | Trọng tài | 48 / 48 | 0 / 0 | 0 / 0 | 0 |
| 43 | Xác minh cuối | 22 / 0 | 0 / 26 | 48 / 0 | 26 |

| Seed | Execution | Evidence trọng tài | Quyết định coverage | Wilson 95% cho recall cuối | Wilson 95% cho FPR cuối |
|---:|---:|---:|---|---:|---:|
| 17 | 40/40 | 9/96 | inconclusive | 30.7–57.7% | 0.0–7.4% |
| 43 | 40/40 | 7/96 | inconclusive | 32.6–59.7% | 0.0–7.4% |

Từ gốc repo, kiểm chứng enrollment, archive và tái dựng kết quả bằng lệnh sau.

```sh
python engineering/airc500/quality_study.py verify --out engineering/airc500/evidence/quality-v2/marketing --enrollment-pin 1ea5a98f97c21a08bfc19cfd058ea7f93e0f30da19dc3f5685b7852ce7aeed2b --archive-pin e5f05c3b92bcef739fe2d683728f303e1049c4b85d5636bc2cff19d95568faeb
```

## 16 ca chính sách danh tính

Git fixture `cfbb31b2d382dd123f31572edee720622b65c05e` → `cdfbd49b181c4d6d0fa23763e761241f7741cadb`. Hai seed dùng 4 ID thực sự nhận receipt (AR-002, QT-032, SP-011, SP-012), 20 lượt ký hợp lệ, 17,501 token đầu vào và 14,967 token đầu ra. Chi phí API trả ngoài bằng 0 µUSD.

[Số liệu đầy đủ](identity/metrics.json) · [Lịch sử từng finding và domain](identity/trace.json.gz) · [Journal seed 17](identity/seed-17.json.gz) · [Journal seed 43](identity/seed-43.json.gz)

| Seed | Cấu hình | TP / FP / FN / TN | Precision | Recall | FPR | Giải thích đúng / TP | Hướng sửa đúng / TP | Lượt | Input / output token | Tổng giây gọi model |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | Verifier | 8 / 0 / 0 / 8 | 100.0% | 100.0% | 0.0% | 8/8 | 8/8 | 0 | 0 / 0 | 0.0 |
| 17 | Một reviewer, hai lượt | 8 / 8 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/8 | 0/8 | 4 | 3,126 / 2,954 | 264.3 |
| 17 | Hai reviewer độc lập | 8 / 8 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/8 | 0/8 | 4 | 3,126 / 2,969 | 231.0 |
| 17 | Một reviewer + verifier | 7 / 0 / 1 / 8 | 100.0% | 87.5% | 0.0% | 0/7 | 0/7 | 4 | 3,126 / 2,954 | 264.3 |
| 17 | Hội đồng + verifier | 7 / 0 / 1 / 8 | 100.0% | 87.5% | 0.0% | 0/7 | 0/7 | 8 | 7,184 / 6,086 | 505.7 |
| 43 | Verifier | 8 / 0 / 0 / 8 | 100.0% | 100.0% | 0.0% | 8/8 | 8/8 | 0 | 0 / 0 | 0.0 |
| 43 | Một reviewer, hai lượt | 8 / 8 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/8 | 0/8 | 4 | 3,126 / 2,955 | 236.2 |
| 43 | Hai reviewer độc lập | 8 / 8 / 0 / 0 | 50.0% | 100.0% | 100.0% | 0/8 | 0/8 | 4 | 3,126 / 2,964 | 239.9 |
| 43 | Một reviewer + verifier | 5 / 0 / 3 / 8 | 100.0% | 62.5% | 0.0% | 0/5 | 0/5 | 4 | 3,126 / 2,955 | 236.2 |
| 43 | Hội đồng + verifier | 7 / 0 / 1 / 8 | 100.0% | 87.5% | 0.0% | 0/7 | 0/7 | 8 | 7,191 / 6,026 | 470.4 |

| Seed | Giai đoạn hội đồng | TP / FP | TP thêm / mất | FP bỏ / thêm | Chưa phát hiện |
|---:|---|---:|---:|---:|---:|
| 17 | Mù | 8 / 8 | 8 / 0 | 0 / 8 | 0 |
| 17 | Phản biện | 8 / 8 | 0 / 0 | 0 / 0 | 0 |
| 17 | Trọng tài | 8 / 8 | 0 / 0 | 0 / 0 | 0 |
| 17 | Xác minh cuối | 7 / 0 | 0 / 1 | 8 / 0 | 1 |
| 43 | Mù | 8 / 8 | 8 / 0 | 0 / 8 | 0 |
| 43 | Phản biện | 8 / 8 | 0 / 0 | 0 / 0 | 0 |
| 43 | Trọng tài | 8 / 8 | 0 / 0 | 0 / 0 | 0 |
| 43 | Xác minh cuối | 7 / 0 | 0 / 1 | 8 / 0 | 1 |

| Seed | Execution | Evidence trọng tài | Quyết định coverage | Wilson 95% cho recall cuối | Wilson 95% cho FPR cuối |
|---:|---:|---:|---|---:|---:|
| 17 | 10/10 | 5/16 | inconclusive | 52.9–97.8% | 0.0–32.4% |
| 43 | 10/10 | 6/16 | inconclusive | 52.9–97.8% | 0.0–32.4% |

Từ gốc repo, kiểm chứng enrollment, archive và tái dựng kết quả bằng lệnh sau.

```sh
python engineering/airc500/quality_study.py verify --out engineering/airc500/evidence/quality-v2/identity --enrollment-pin 548266dc5cb792cfcc480fa2513b19c70c782c71a5f5018f73d6489765e6b191 --archive-pin b43cf9c34ca8986f291ec7f87869d872f8c1044182033f5c619db89100c1b616
```

## Diễn giải và phạm vi tin cậy

Verifier định kiểu tự kiểm được giá trị và phạm vi trên nguồn fixture. Verifier abstain với 24 ca ngữ nghĩa Marketing thuộc phủ định, CTA và claim thiếu nguồn. Điểm hướng sửa của verifier thuần phản ánh khả năng tạo operation theo field định kiểu. Nhánh có AI chỉ xác minh candidate từng được reviewer nêu kèm đúng subject và nguồn. Vì vậy hai nhánh có thể đạt số lỗi cuối khác nhau dù dùng lại cùng quy tắc typed.

Execution đếm receipt hợp lệ. Evidence yêu cầu trọng tài đưa đúng verdict, đúng subject, đúng nguồn và thuộc miền verifier có thể kiểm. Số finding cuối còn xét lịch sử candidate và ý kiến thiểu số từ các vòng trước. Các obligation thiếu khiến coverage ở trạng thái `inconclusive`. Chỉ số P/R/FPR và Wilson 95% của mọi phase/domain, danh sách ca bỏ sót, FP, giải thích và hướng sửa đã chấm đều có trong trace.

Ví dụ từ seed 17, finding `F-970c36d8`. Nguồn của Indigo tote quy định CAD, nội dung ghi USD. Lượt mù `s17-common-0` (MK-022) báo có lỗi nhưng trỏ Linen wrap, chọn cả current và expected là “do not use CAD”, operation `keep` và nguồn D. Bộ chấm cho điểm phát hiện đúng đối với unit, điểm hướng sửa và giải thích bằng 0. [Journal chứa output gốc](marketing/seed-17.json.gz).

Giao thức Marketing dùng tám chỉ số lựa chọn cho mỗi unit. Cohort identity dùng JSON với tên field và giá trị đầy đủ. Cả hai giao thức đặt verdict flag ở vị trí đầu. Hiệu ứng thứ tự lựa chọn còn chưa được kiểm soát. Thay đổi đồng thời miền và encoding ngăn suy luận kiểu trả lời nào tốt hơn từ phép so giữa hai cohort. Mỗi miền Marketing chỉ có bốn ca dương và bốn ca âm. Mẫu tổng hợp nhỏ chưa xác lập năng lực nghiệp vụ hoặc khả năng tổng quát hóa.

Trước phép đo, một dispatch với biến thể JSON schema cũ nhận HTTP 400 từ llama-server, 0 receipt được chấp nhận, 1 attempt không rõ usage và 4.000 token dự phòng vẫn bị giữ. [Checkpoint đã hủy](preflight-unsupported-schema.json). Các bảng chỉ dùng lần chạy với schema đã được hỗ trợ; 100 lượt đo đều có output ký và pin riêng.

Qwen trong báo cáo này chạy native Windows trên fixture, trả phí ngoài bằng 0. Bằng chứng probe container Linux độc lập với các receipt đó. Bước kế tiếp cần hội đồng đủ căn cứ trước khi tăng số reviewer, xác nhận hiệu quả trên tập mới và có nhãn nghiệp vụ độc lập. Đọc source repository thực bằng reviewer tự động tiếp tục HOLD. Commercial GA tiếp tục NO-GO.
