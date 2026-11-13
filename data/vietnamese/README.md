# Dữ liệu PDF tiếng Việt

- `13nd.signed.pdf`: bản sao nguyên byte do người dùng cung cấp và cho phép lưu trong repo, giữ chữ ký và SHA-256.
- `pages.json`: text OCR từng trang vật lý, metadata và ranh giới chương.
- `manifest.json`: manifest hiện tại đúng schema đề, có `source_path_or_url` chính thức, `local_path` tương đối, `license_or_permission`, ngày truy cập, version, checksum và thống kê trang.

UI và pipeline đọc `local_path` tương đối theo root repo, không phụ thuộc Downloads.
Manifest cũ lúc chạy vẫn được lưu nguyên byte tại `results/vietnamese/input_snapshots/manifest.json`;
`provenance_migrations.json` ghi rõ thay đổi metadata đóng gói. Hash/gold/trace/metrics cũ giữ nguyên.

39 trang vật lý gồm 28 trang phần nghị định, 1 trang danh mục phụ lục và 10 trang mẫu biểu.
Đây là corpus bổ sung, không khai 39 trang là 39 trang nội dung đầy đủ để đáp ứng yêu cầu tối thiểu.
Corpus chính Alice có 82 đơn vị nội dung hợp lệ; xem `data/README.md`.

Các câu hỏi tiếng Việt ở `benchmark/vietnamese_questions.json`, kết quả ở `results/vietnamese/`.
Các câu tiếng Anh vẫn ở `benchmark/questions.json`, dữ liệu gốc `data/alice.txt`,
kết quả A/B/C ở `results/`, kết quả D và 10 câu mới ở `results/extension/`.
