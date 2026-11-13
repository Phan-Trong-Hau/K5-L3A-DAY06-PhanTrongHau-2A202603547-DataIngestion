# Dữ liệu

Dữ liệu nằm tại `data/` ở root, đúng cấu trúc `SUBMISSION.md`; pipeline tự xác định root repo.
Danh mục: [sources.json](sources.json). Không có dữ liệu giả lập hoặc template trong tập chạy.

| Nguồn | File gốc | Text chuẩn hóa | Manifest |
|---|---|---|---|
| Alice | `alice.txt` | `pages.json` | `manifest.json` |
| Nghị định 13 | `vietnamese/13nd.signed.pdf` | `vietnamese/pages.json` | `vietnamese/manifest.json` |
| Nghị định 69 | `multidoc/raw/nd69.pdf` | `multidoc/nd69_pages.json` | `multidoc/nd69_manifest.json` |
| Nghị định 42 | `multidoc/raw/nd42.pdf` | `multidoc/nd42_pages.json` | `multidoc/nd42_manifest.json` |
| Sherlock Holmes | `multidoc/raw/sherlock.txt` | `multidoc/sherlock_pages.json` | `multidoc/sherlock_manifest.json` |

Corpus chính Alice có 82 đơn vị liên tiếp, mỗi đơn vị ≥1.500 ký tự sau chuẩn hóa,
không phải trang PDF; ranh giới cuối = chapter_start + characters, end-exclusive.
Sherlock chỉ index hai truyện đầu (53 đơn vị); bản gốc toàn sách và license được giữ.
Các nguồn Gutenberg giữ nguyên bản tải và Project Gutenberg License.
PDF là snapshot lịch sử từ nguồn chính thức; giữ nguyên byte/chữ ký, có OCR tiếng Việt.
Không tự coi mọi trang biểu mẫu là trang nội dung đủ điều kiện rubric.

Mỗi nguồn có ID, URL/local_path, quyền/giấy phép hoặc sự cho phép, thời điểm truy cập,
version, SHA-256 và page/unit kèm số ký tự. File ký gốc Nghị định 13 do người dùng cung cấp và cho phép lưu trong repo.

Kho 5 nguồn được ghép trong bộ nhớ bằng `starter.src.corpus.load_multidoc_pages`,
không lưu thêm bản text tổng hợp bị lặp. `multidoc/manifest.json` là index nguồn;
`normalized_sha256` xác nhận bytes của JSON tái dựng giống snapshot được dùng khi chạy.
`multidoc/extraction_environment.json` ghi công cụ/tham số OCR.

Benchmark ở `benchmark/`; kết quả baseline ở `results/`, D ở `results/extension/`,
phép thử Nghị định 13 ở `results/vietnamese/`, phép thử 5 nguồn ở `results/multidoc/`.
`results/provenance.json` ghi việc lược metadata quản lý và tái dựng snapshot, không đổi dữ liệu thực nghiệm.
`.gitattributes` giữ các file nguồn nguyên byte trên các hệ điều hành.
