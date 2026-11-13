# Dữ liệu bài làm

Theo `SUBMISSION.md`, dữ liệu và manifest ở `data/` tại root là hợp lệ;
không bắt buộc chuyển vào `starter/data/`. Mọi entry point dùng đường dẫn theo root repo.
`starter/data/` chỉ là thư mục trống được giữ từ starter ban đầu.

```text
data/
├── README.md
├── sources.json                 # danh mục hai corpus và vai trò của từng bộ
├── alice.txt                    # sách tiếng Anh gốc, kèm Project Gutenberg License
├── manifest.json                # manifest corpus chính Alice
├── pages.json                   # 82 đơn vị nội dung chuẩn hóa
├── format-example.json          # ví dụ của đề; KHÔNG được dùng trong thí nghiệm
└── vietnamese/
    ├── README.md
    ├── 13nd.signed.pdf           # bản PDF ký gốc, nguyên byte
    ├── manifest.json            # nguồn chính thức, local_path tương đối, OCR, số trang/quyền
    └── pages.json               # OCR của 39 trang vật lý, metadata/chapter spans
```

| Corpus | Vai trò | Quy tắc tính | Benchmark | Kết quả |
|---|---|---|---|---|
| Alice — tiếng Anh | Corpus chính đáp ứng yêu cầu tối thiểu | 82 đơn vị liên tiếp, mỗi đơn vị ≥1.500 ký tự chuẩn hóa; bỏ bìa/mục lục/giấy phép, không nhân bản | `benchmark/questions.json`: 15 dev / 5 test; `extension_holdout.json`: 10 câu mới | `results/` cho A/B/C; `results/extension/` cho D và bộ mới |
| Nghị định 13 — tiếng Việt | Phép thử bổ sung trên nguồn/ngôn ngữ mới | 39 trang scan: 28 trang phần nghị định, 1 trang danh mục phụ lục, 10 trang mẫu biểu; không tự cộng thành 39 trang nội dung đủ điều kiện | `benchmark/vietnamese_questions.json`: 20 external_test, không dùng để chọn tham số | `results/vietnamese/` |

Trong manifest Alice, `page` là ID đơn vị, `chapter_start` là offset đầu trong chương;
ranh giới cuối được tính bằng `chapter_start + characters` (end-exclusive).
Trong manifest tiếng Việt, `page` là trang vật lý PDF; offset chunk tính trong text OCR của trang.

Mỗi corpus có nguồn, quyền/giấy phép hoặc sự cho phép, thời điểm truy cập, version,
SHA-256 và danh sách trang/đơn vị kèm số ký tự. PDF và toàn bộ text được xử lý local.
Bản PDF gốc được người dùng cung cấp và cho phép lưu trong repo;
không chỉnh sửa, flatten hoặc ghi OCR đè lên PDF ký.

Manifest tiếng Việt đã được cập nhật đường dẫn tương đối sau khi đóng gói PDF.
Snapshot nguyên byte của manifest tại thời điểm chạy được lưu tại
`results/vietnamese/input_snapshots/manifest.json`; sidecar `provenance_migrations.json`
giải thích việc thay metadata. Không sửa hash, thời điểm, gold, trace hay điểm của lần chạy cũ.
Dấu vết Downloads trong snapshot chỉ là lịch sử, không phải phụ thuộc runtime.

Không commit `.qdrant/`, `.qdrant_vi/`, `.embedding_cache/`, `.ocr_cache/` hoặc `.venv/`.
Các thư mục này được ignore và có thể tái tạo theo README root.
Không xóa corpus tiếng Anh khi thêm corpus tiếng Việt; hai phép thử giữ nguyên dữ liệu và kết quả riêng.

`.gitattributes` giữ hai file nguồn gốc nguyên byte (không tự đổi CRLF trên Windows).
Text Gutenberg gốc có khoảng trắng/cuối dòng của nguồn; chỉ bản chuẩn hóa mới được làm sạch.
