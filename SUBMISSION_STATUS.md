# Trạng thái bản bàn giao — Day 06

Bản mã, dữ liệu, kết quả thực nghiệm và báo cáo được chốt để bàn giao trên nhánh `main`.
Đánh giá nội dung do Codex đọc nguồn/trace hỗ trợ, được người dùng chấp nhận rõ ràng trong phiên làm việc.
Không tuyên bố học viên tự chấm từng dòng, không tuyên bố reviewer độc lập hoặc bảo đảm điểm số của giảng viên.

| Yêu cầu trong đề | Minh chứng bản bàn giao |
|---|---|
| ≥30 trang/đơn vị nội dung hợp lệ | Alice 82 đơn vị, tối thiểu 1.501 ký tự; `data/manifest.json`, `pages.json`, nguồn và license trong `alice.txt` |
| Đọc, Unicode, truy vết, lỗi | `starter/src/ingestion.py`, metadata source/page/offset; `results/errors.log`; PDF scan có OCR và log riêng |
| ≥20 câu, 15 dev / 5 test, ≥3 filter gồm ≥1 test | `benchmark/questions.json`, `protocol.json`: 20 câu, 4 filter; gold kiểm chứng nguồn |
| Embedding thật + store bền vững có filter | FastEmbed BGE 384 chiều, Qdrant local; model snapshot và dependencies khóa |
| Ba cấu hình và so sánh kiểm soát | A/B/C; B–C chỉ đổi filter, chunk/vector giống nhau; `artifacts/experiment_log.csv` |
| Nạp lại không trùng, xử lý dữ liệu đổi | Counts 350/192/192 giữ nguyên sau repeat; thay snapshot loại obsolete chunks; test persistence/filter/replacement |
| Top-3, Hit@1/Hit@3 dev/test | `results/traces.jsonl`, `metrics.json`, `statistics.json`, `selection.json`, `run.json` |
| Coherence 10 vị trí × 3 cấu hình | `results/coherence_review.csv`: 30 nhãn 0–2 và lý do; `coherence_samples.json` có text/offset |
| Metadata 5 test × top-3 × 3 cấu hình | `results/metadata_audit.csv`: 45 dòng đối chiếu source/page/chapter/offset và tuân thủ filter |
| Grounding 5 test × 3 cấu hình | `results/grounding_review.csv`: 15 nhãn và lý do; không thay bằng exact match hoặc độ đúng trả lời LLM |
| Phân tích chiến lược, lỗi, tài nguyên/chi phí | Báo cáo cá nhân có A–B, B–C, trường hợp thất bại, độ dài/thời gian/cache, API 0 USD và giới hạn |
| Công khai sử dụng AI và cách kiểm tra | `results/review_acceptance.json`: phát biểu người dùng chấp nhận phương pháp; reviewer, hash, trạng thái rõ ràng |
| Cách chạy, dữ liệu, báo cáo, thông tin học viên | README root, `data/README.md`, `STUDENT.md`, `report/individual/2A202603547_PhanTrongHau.md` |
| Không lẫn ví dụ hoặc bí mật trong bài làm | `format-example.json` được ghi rõ chỉ minh họa; audit secret-pattern; cache/model/venv bị ignore |
| Mở rộng D và nguồn tiếng Việt | `results/extension/`, `results/vietnamese/`; 20 câu tiếng Việt mới, không tinh chỉnh theo test; PDF nguyên byte trong data |
| UI demo | `python -m starter.src.demo --port 18763`; A/B/C/D trực tiếp, trace đã lưu, benchmark và PDF tiếng Việt |

Chạy kiểm tra: `.venv/bin/python starter/scripts/audit_repo.py` và
`.venv/bin/python -m unittest discover -s tests -v`.
Kiểm thử UI/API: `node tests/test_demo_ui.cjs` khi server đã chạy; Node chỉ cần cho bài kiểm tra này.
Audit không thay cho việc chấm điểm của giảng viên. Có AI hỗ trợ và thiên lệch tự chấm;
đặc biệt kết quả D trên test tiếng Anh cũ là thí nghiệm sau khi đã xem test.

Bàn giao Git: nhánh `main` trên repo trong STUDENT.md; hash chính xác bằng `git rev-parse HEAD`.
Gửi link qua kênh lớp do học viên thực hiện, vì chưa có chỉ định kênh/người nhận trong phiên làm việc.
