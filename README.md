# Day 06 — Data Ingestion Engineering

**Phan Trọng Hậu · 2A202603547 · L3A**

Pipeline Python đọc/chuẩn hóa tài liệu, chia chunk, tạo embedding thật, lưu Qdrant có metadata filter,
đánh giá top-3 và so sánh các chiến lược. Có UI demo, 5 tài liệu Anh/Việt và kết quả chạy thật.
Yêu cầu bài: [GUIDE](GUIDE.md), [BENCHMARK](BENCHMARK.md), [RUBRIC](RUBRIC.md), [SUBMISSION](SUBMISSION.md).

## Cài đặt

Đã kiểm tra với Python 3.14.9 trên Linux CPU; lần đầu cần mạng tải dependencies/model.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock.txt
```

Không dùng uv: tạo venv Python 3.14, rồi `python -m pip install -r requirements.lock.txt`.
Không cần Docker hoặc API key. Không có fallback mock. Chi phí API 0 USD, chưa tính CPU/điện.

## Chạy pipeline và demo

Từ root repo:

```bash
.venv/bin/python -m starter.src.run             # A/B/C trên Alice
.venv/bin/python -m starter.src.run_extension   # D và 10 câu tiếng Anh mới
.venv/bin/python -m starter.src.run_vietnamese  # A/B/C/D trên PDF Nghị định 13
.venv/bin/python -m starter.src.run_multidoc    # C/D/E/F/G, chung kho 5 tài liệu
.venv/bin/python -m starter.src.demo --port 18763
```

Mở **http://127.0.0.1:18763**. Dữ liệu và kết quả đã nộp sẵn; xem benchmark trên UI không cần chạy lại pipeline.
Chỉ cần chạy pipeline đầu để tạo index khi muốn truy vấn trực tiếp trên máy mới.
Dừng UI trước khi nạp lại index Alice vì Qdrant local khóa theo tiến trình.

UI gồm: truy vấn Alice trực tiếp; phát lại benchmark; bảng so sánh; PDF tiếng Việt;
phép thử nhiều tài liệu; pipeline/kịch bản trình bày. Mỗi chunk có score, document, vị trí và nút mở nguồn.
Các màn hình benchmark ghi rõ là trace đã lưu; truy vấn tự do không tự chấm Hit khi không có gold.
Cosine, logit và RRF là điểm xếp hạng khác nhau, không phải xác suất đúng.

## Dữ liệu, cấu hình và kết quả

[Danh mục dữ liệu](data/README.md) · [Manifest các nguồn](data/sources.json) · [Báo cáo cá nhân](report/individual/2A202603547_PhanTrongHau.md)

- Alice: 82 đơn vị liên tiếp ≥1.500 ký tự, corpus chính đáp ứng yêu cầu tối thiểu; 15 dev/5 test.
- Nghị định 13: 39 trang vật lý scan; 20 câu tiếng Việt mới; không tính mọi trang mẫu biểu là trang nội dung.
- Mở rộng: Nghị định 69, Nghị định 42, hai truyện đầu Sherlock Holmes; toàn kho 5 nguồn có 230 trang/đơn vị, 566 chunk.
- Bộ mới: 45 câu, dev 15 câu Nghị định 69, test 30 câu trên hai tài liệu khác; 20 câu cũ chỉ diagnostic.

| Cấu hình | Thay đổi |
|---|---|
| A | Fixed 500 ký tự, overlap 50, BGE English dense |
| B | Theo đoạn ≤1.000 ký tự, cùng model |
| C | B + filter được cung cấp trong câu hỏi/ngữ cảnh |
| D | Dense20 + BM25_20 + RRF60 → rerank20 bằng cross-encoder tiếng Anh → top3 |
| E | D bỏ reranker, dùng RRF top3 |
| F | Đổi sang E5-small đa ngữ dense |
| G | E5-small + BM25/RRF top3 |

| Bộ đo — Evidence Hit@3 | C | D | E | F | G |
|---|---:|---:|---:|---:|---:|
| Alice dev /15 | 14 | 15 | — | — | — |
| Alice test /5 | 4 | 5* | — | — | — |
| Nghị định 13 riêng /20 | 12 | 16 | — | — | — |
| 5 nguồn: dev /15 | 8 | 10 | 9 | 10 | 11 |
| 5 nguồn: test tài liệu mới /30 | 12 | 18 | 15 | 17 | 19 |
| 5 nguồn: diagnostic cũ /20 | 7 | 15 | 14 | 16 | 18 |

\* D được thêm sau khi đã xem test Alice; không coi điểm này là holdout độc lập.
C chọn trên dev baseline. G chọn trên dev đa nguồn trước khi mở test. G hơn D một câu test,
nhưng kém D ở nhóm Sherlock; không kết luận tốt hơn tổng quát. Báo cáo có đủ trường hợp thắng/thua và giới hạn.

## Minh chứng bài nộp

- `data/`: nguồn gốc, một bản text chuẩn hóa mỗi nguồn, manifest/giấy phép/quy tắc đếm.
- `benchmark/`: câu hỏi, split, gold evidence và protocol chốt trước chạy.
- `artifacts/`: nhật ký cấu hình và giả thuyết.
- `results/`: metrics, trace top3, thống kê, nhãn nội dung/metadata và checksum/model snapshot.
- `starter/src/`, `starter/scripts/`, `starter/ui/`: code tái lập và giao diện.
- `report/individual/2A202603547_PhanTrongHau.md`: báo cáo duy nhất, gồm cả các thí nghiệm mở rộng.

## Kiểm tra

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python starter/scripts/audit_repo.py
node tests/test_demo_ui.cjs  # optional: UI đang chạy; Node chỉ dùng cho kiểm tra này
```

Kết quả tổng hợp: `results/validation.json`. Audit kiểm tra nguồn, 95 câu hỏi, gold,
trace/metrics, offset, split theo tài liệu, link và file bị ignore; không thay thế chấm điểm của giảng viên.
Không commit venv, model, vector DB hoặc cache OCR. Các thư mục đó có thể tái tạo.

Nếu cần tái tạo OCR từ PDF gốc: dùng `starter/scripts/ocr_vietnamese.py` và
`prepare_multidoc_sources.py`; cần Poppler/Tesseract với language pack `vie`.
Snapshot đã có sẵn; không chuẩn bị lại gold hoặc sửa test sau khi xem kết quả mà không ghi phiên bản mới.
