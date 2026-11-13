# Kiểm tra toàn repo và cấu trúc dữ liệu

Thời điểm UTC: 2026-11-13T11:30:57.084544+00:00
Trạng thái: **PASS_WITH_DISCLOSED_AI_REVIEW**

Đã quét 106 file bài nộp (tracked và untracked không bị ignore), gồm dữ liệu gốc, OCR, benchmark, toàn bộ trace, báo cáo, UI, code và cấu hình.
Không duyệt môi trường ảo, Git internals hoặc cache/model/vector DB được ignore; đây là trạng thái runtime, không thuộc gói bài nộp.

| Kiểm tra | Trạng thái | Chi tiết |
|---|---|---|
| submission_file_scan | PASS | {"files": 106, "bytes": 4432880, "by_extension": {"(no extension)": 4, ".md": 18, ".csv": 5, ".svg": 2, ".json": 32, ".txt": 8, ".pdf": 1, ".log": 3, ".jsonl": 3, ".example": 1, ".yml": 1, ".sql": 1, ".py": 23, ".js": 1, ".html": 1, ".css": 1, ".cjs": 1}, "scope": "All tracked+untracked non-ignored submission files, including raw PDF/text, results and dotfiles. Excludes Git internals, .venv, vector databases, OCR/model caches and audit outputs."} |
| manifest_schema_and_portable_sources | PASS | Both current manifests match required schema; bundled source paths exist, are relative and match SHA-256. |
| corpus_counts_and_normalized_text | PASS | {"alice_units": 82, "alice_min_characters": 1501, "vietnamese_physical_pages": 39, "vietnamese_regulation_pages": 28, "note": "Primary Alice corpus meets >=30 rule; VI is supplemental and not claimed as 39 full content pages."} |
| all_benchmarks_and_gold | PASS | {"questions": {"benchmark/questions.json": 20, "benchmark/extension_holdout.json": 10, "benchmark/vietnamese_questions.json": 20}, "total": 50, "main_split": "15 dev / 5 test", "note": "Evidence verified against current stored source text; semantic/human confirmation remains separate."} |
| all_traces_metrics_and_source_offsets | PASS | {"traces": 200, "top3_records": 600, "metrics": "All recomputed exactly", "provenance": "Every returned chunk maps to its source page and normalized offsets"} |
| historical_input_integrity | PASS | {"checked": 13, "historical_snapshots": [{"original": "data/vietnamese/manifest.json", "snapshot": "results/vietnamese/input_snapshots/manifest.json"}], "note": "No benchmark/trace/metric hashes or recorded run timestamps rewritten."} |
| disclosed_accepted_assessments | PASS | {"rows": {"results/coherence_review.csv": 30, "results/grounding_review.csv": 15, "results/metadata_audit.csv": 45}, "total": 90, "method": "AI-assisted source/trace review explicitly accepted by user; no independent human scoring claimed", "summary": "Scores unchanged; hash-bound labels and acceptance record verified."} |
| all_markdown_local_links | PASS | {"local_links_checked": 36} |
| secret_patterns_and_package_exclusions | PASS | No matching populated API-secret assignments; runtime caches excluded and PDF included. Template local-only database password is documented, not an API credential. Pattern scan is not a guarantee of all possible secret formats. |
| ui_static_checks | PASS | JS syntax and unique HTML IDs checked; visual browser QA not available in current environment. |

## Kiểm tra bổ sung đã chạy

- `results/repo_audit_tests.txt`: Ran 9 tests in 0.099s; OK
- `results/repo_audit_ui.txt`: PASS: A/B/C/D saved/live, Vietnamese traces/metrics/source PDF hash/render labels, new holdout, score labels, D chapter filter; render smoke only (no visual browser).

## Các sửa đổi sau audit

- Manifest tiếng Việt có local_path tương đối, URL chính thức và license_or_permission đúng schema đề; xóa mô tả cũ chưa copy PDF.
- Giữ nguyên manifest lúc chạy trong input_snapshots; sidecar chỉ rõ thay metadata đóng gói. Không sửa gold, trace, metrics hoặc hash lịch sử.
- UI/pipeline đọc đường dẫn từ manifest, không phụ thuộc Downloads. Script OCR tái tạo cũng xuất schema/đường dẫn phù hợp.
- Thêm data/README.md và sources.json để phân biệt corpus chính Alice với phép thử PDF tiếng Việt; giữ format-example.json là ví dụ của đề.
- Làm rõ số trang/đơn vị: Alice 82 × >=1500 ký tự đủ quy tắc; PDF 39 trang vật lý không tự coi là 39 trang nội dung hợp lệ.

## Phương pháp đánh giá và phạm vi bàn giao

- 90 dòng đánh giá đã chốt theo AI-assisted review, được người dùng chấp nhận rõ ràng trong phiên làm việc; không ghi thành chấm độc lập của con người.
- Nhãn/điểm và lý do không bị nâng sau chấp nhận; hồ sơ user instruction và hash tại results/review_acceptance.json.
- Bản bàn giao trên nhánh main; việc push được xác minh khi bàn giao. Gửi link qua kênh lớp là thao tác riêng ngoài phạm vi repo.
- Chưa có kiểm tra trực quan UI bằng browser trong môi trường này; API/render smoke và kiểm thử được chạy riêng.

Chi tiết inventory, hash và dữ liệu kiểm tra: `results/repo_audit.json`. Tái chạy: `.venv/bin/python starter/scripts/audit_repo.py`.
