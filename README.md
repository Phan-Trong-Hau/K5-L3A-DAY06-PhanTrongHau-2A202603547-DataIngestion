# Day 06 — Data Ingestion Engineering

Bài cá nhân của **Phan Trọng Hậu — 2A202603547 — L3A**.

## Tóm tắt đề

Xây pipeline Python đọc và chuẩn hóa ≥30 trang/đơn vị nội dung, giữ nguồn/vị trí,
chia chunk, tạo semantic embedding thật và lưu vào vector store bền vững có filter.
So sánh ≥3 cấu hình trên ≥20 câu có gold evidence, chia trước 15 dev/5 test.
Đánh giá Hit@1, Evidence Hit@3, coherence, metadata, grounding và đánh đổi tài nguyên.
Nộp mã, manifest, benchmark, trace, nhãn đánh giá và báo cáo có thể tái lập.
Đề gốc chi tiết: [GUIDE](GUIDE.md), [BENCHMARK](BENCHMARK.md), [RUBRIC](RUBRIC.md).

## Bài làm

Danh mục dữ liệu: [data/README.md](data/README.md), [hai corpus và đường dẫn](data/sources.json).

- Corpus: *Alice’s Adventures in Wonderland* — Lewis Carroll; bản Gutenberg nguyên vẹn kèm giấy phép tại `data/alice.txt`.
- 82 đơn vị nguồn liên tiếp ≥1.500 ký tự; không phải số trang PDF. Metadata `chapter` lấy từ heading thật.
- Model `BAAI/bge-small-en-v1.5`, 384 chiều, FastEmbed ONNX CPU; corpus/query tiếng Anh.
- Qdrant local tại `.qdrant/`, cosine exact search, top-3. Backend do Qdrant quản lý, không tự tính vector search bằng Python/SQLite.
- A: fixed 500 ký tự, overlap 50; B: gộp đoạn tối đa 1.000 ký tự; C: giống B và lọc chương khi câu hỏi cung cấp.

## Chạy lại

Đã kiểm tra bằng Python **3.14.9**, Linux CPU; cần mạng cho lần đầu tải dependencies/model.

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.lock.txt
.venv/bin/python -m starter.src.run
.venv/bin/python -m unittest discover -s tests -v
```

Nếu không dùng uv, tạo venv Python 3.14 rồi `python -m pip install -r requirements.lock.txt`.
Chạy từ root repo. Dữ liệu, manifest và benchmark đã có sẵn; không cần tải lại.
Khôi phục dữ liệu gốc nếu cần:

```bash
curl -L --fail https://www.gutenberg.org/ebooks/11.txt.utf-8 -o data/alice.txt
.venv/bin/python starter/scripts/prepare_data.py
```

`prepare_data.py` xác minh nguyên văn evidence và tạo lại manifest; bản online có thể đổi,
vì vậy dùng snapshot đã nộp để tái lập kết quả. Không sửa benchmark sau khi xem test.
`run.py` báo lỗi nếu checksum dữ liệu khác manifest hoặc evidence không tồn tại.
`--output results/rerun` lưu lần chạy mới riêng để giữ số liệu gốc.

Pipeline nạp lại snapshot từng collection A/B/C hai lần và kiểm tra số bản ghi.
ID chunk ổn định theo nguồn, offset và nội dung. Mỗi lần nạp thay toàn bộ collection nên loại chunk lỗi thời;
phù hợp lab nhỏ, không atomic và không tối ưu cho production. Cache embedding theo model/provider/text
ở `.embedding_cache/`; C tái sử dụng vectors của B. Không có fallback mock.

## Kết quả chạy thật

| Cấu hình | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Chunks |
|---|---:|---:|---:|---:|---:|
| A | 5/15 | 9/15 | 5/5 | 5/5 | 350 |
| B | 9/15 | 13/15 | 4/5 | 4/5 | 192 |
| C | 9/15 | 14/15 | 4/5 | 4/5 | 192 |

Chọn **C trên dev** theo tiêu chí ghi trước tại `benchmark/protocol.json`;
không đổi sang A sau khi thấy test. Test chỉ có 5 câu nên chưa đủ kết luận tổng quát.
Chi phí API 0 USD; chưa tính CPU/điện. Thời gian C có cache nên không so trực tiếp với A/B.

## Minh chứng

- [Manifest và quy tắc đếm](data/manifest.json), [các đơn vị nguồn](data/pages.json).
- [20 câu + gold + split](benchmark/questions.json), [giao thức cố định](benchmark/protocol.json).
- [Trace 60 lượt × top-3](results/traces.jsonl), [metrics](results/metrics.json), [thống kê](results/statistics.json).
- [Quyết định trên dev](results/selection.json), [môi trường/model/hash](results/run.json), [dependencies](requirements.lock.txt).
- [Coherence](results/coherence_review.csv), [grounding](results/grounding_review.csv), [metadata audit](results/metadata_audit.csv).
- [Báo cáo cá nhân](report/individual/2A202603547_PhanTrongHau.md).

**Trạng thái đánh giá:** đã chốt 30 nhãn coherence, 15 nhãn grounding và 45 bản ghi metadata theo phương pháp đọc nguồn/trace có AI hỗ trợ. Người dùng đã chấp nhận phương pháp và kết quả trong phiên làm việc; các CSV ghi `student_verified=user_accepted_ai_assisted_review`. Bằng chứng chấp nhận, giới hạn và hash nằm ở [review_acceptance.json](results/review_acceptance.json). Không ghi rằng học viên đã tự chấm từng dòng hoặc có reviewer độc lập.

Bản bàn giao dùng nhánh `main`; thông tin học viên tại [STUDENT.md](STUDENT.md), trạng thái và checklist tại [SUBMISSION_STATUS.md](SUBMISSION_STATUS.md). Nộp link qua kênh lớp là thao tác riêng của học viên.

## UI demo và thuyết trình

Chạy từ root repo, sau khi đã cài môi trường:

```bash
.venv/bin/python -m starter.src.demo
```

Mở **http://127.0.0.1:18763** trong trình duyệt. Đổi cổng bằng `--port 18764` nếu cần.
UI HTML/CSS/JavaScript, server Python standard library, không cần cài Node hoặc thêm dependency.
Font hệ thống, không cần tải CDN.

Bốn màn hình trong menu:

1. **Khám phá tri thức:** nhập câu hỏi tiếng Anh mới, chọn A/B/C/D hoặc so sánh cả bốn. Có chế độ phát lại 20 câu gốc và 10 câu mới; gold được tô sáng. Filter chương chỉ áp dụng C/D. “Xem nguồn & vị trí” mở nguồn và offset.
2. **So sánh benchmark:** biểu đồ dev/test, bảng chỉ số và kết quả 10 câu tiếng Anh mới; D ghi rõ là mở rộng sau khi đã xem test cũ.
3. **Kiểm tra tiếng Việt:** kết quả 20 câu nguồn mới, trace A/B/C/D theo trang PDF, text OCR và liên kết tới scan gốc.
4. **Pipeline & phương pháp:** giải thích các bước và kịch bản thuyết trình 3 phút.

Kịch bản demo gợi ý:

- Bấm **Khi chunk dài bỏ lỡ đáp án** (q17): A tìm được lời cook “Pepper, mostly”; B/C bỏ lỡ.
- Bấm **Metadata giúp ích thế nào?** (q13): C lọc đúng chương IX và tìm được evidence ở top-3.
- Bấm **Đúng nguồn, thiếu evidence** (q08): đúng unit chưa đủ để chấm hit.
- Mở benchmark: C được chọn trước trên dev; không đổi sang A sau khi thấy test nhỏ.
- Chuyển **Truy vấn trực tiếp**, hỏi câu mới và mở nguồn để đối chiếu.

**Lưu ý vận hành:** nếu chưa có `.qdrant/`, chạy pipeline trước để tạo index.
Lần truy vấn đầu có thể cần tải/nạp model. Dừng UI bằng Ctrl+C trước khi chạy lại pipeline,
vì Qdrant local chỉ cho một tiến trình mở index. Backend lỗi sẽ hiện thông báo, không giả kết quả.
Truy vấn tự do chỉ có similarity, không có gold nên không tự chấm Hit/độ đúng câu trả lời.
Server chỉ lắng nghe loopback `127.0.0.1`; không dùng để triển khai public.

Đã kiểm tra HTTP/API, trace q17, đọc nguồn, input không hợp lệ, truy vấn model thật cả A/B/C
và filter chương C; minh chứng `results/ui_smoke.json`. Môi trường hiện không có browser kết nối
để kiểm tra trực quan trong trình duyệt.


## Cấu hình D — hybrid + reranker (mở rộng sau khi đã xem test)

D dùng nguyên 192 chunk và vector của B, dense top-20 + BM25 top-20,
RRF k=60 lấy 20 ứng viên, sau đó rerank bằng **Xenova/ms-marco-MiniLM-L-6-v2**
(FastEmbed CPU) xuống top-3. C/D dùng cùng quy tắc filter chương từ input.
Không truyền gold/đáp án vào retriever. Không có embedding hoặc vector store mới.
Hướng dẫn reranker chính thức: https://qdrant.tech/documentation/fastembed/fastembed-rerankers/

| D | Hit@1 | Evidence Hit@3 |
|---|---:|---:|
| Dev gốc | 12/15 | 15/15 |
| Test gốc — phân tích sau khi đã xem test | 5/5 | 5/5 |
| 10 câu mới chốt trước chạy D | 9/10 | 10/10 |

Cấu hình D và 10 câu mới được chốt trước lần chạy D đầu tiên, không sweep tham số sau kết quả.
Test gốc đã được xem nên 5/5 chỉ minh họa sửa lỗi, không còn là đánh giá độc lập cho D.
Các câu mới vẫn cùng tác phẩm, số lượng nhỏ; A và C cũng đạt Hit@3 10/10 ở tập này.
D chưa đạt top-1 tuyệt đối: q26 lấy nhầm đoạn ở top-1 nhưng có đủ evidence ở top-3.
Không có nhãn thủ công mới cho coherence/grounding của D; nhãn cũ chỉ áp dụng A/B/C.

Chạy lại (dừng UI trước để giải phóng Qdrant lock):

```bash
.venv/bin/python -m starter.src.run_extension
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m starter.src.demo --port 18763
```

D không cần tạo collection riêng; dùng collection B đã được pipeline gốc dựng.
Lần đầu cần mạng tải reranker. Snapshot model/hash, giao thức, metrics, thời gian,
trace top-3 và toàn bộ ứng viên được lưu trong `results/extension/`;
benchmark mới tại `benchmark/extension_holdout.json`.
D trung bình khoảng 1 giây/câu trên lần chạy CPU đã đo, tốn thêm bước rerank;
chi phí API 0 USD, không tính CPU/điện. UI ghi rõ score D là logit, không phải xác suất đúng.

## Kiểm tra thêm trên PDF tiếng Việt

Đã chạy một phép thử nguồn mới trên `13nd.signed.pdf` do học viên cung cấp,
bản scan 2023 của Nghị định 13/2023/NĐ-CP. 39 trang vật lý được OCR Tesseract vie;
chỉ 28 trang phần nghị định, các trang còn lại là danh mục/mẫu biểu, không coi là 39 trang nội dung đầy đủ.
Giữ nguyên model và A/B/C/D, chốt 20 câu tiếng Việt trước truy xuất, không tinh chỉnh sau kết quả.

| Cấu hình | Hit@1 | Evidence Hit@3 |
|---|---:|---:|
| A | 3/20 | 6/20 |
| B | 4/20 | 11/20 |
| C | 5/20 | 12/20 |
| D | 13/20 | 16/20 |

D chưa đạt tuyệt đối; cả bốn câu lỗi đều có evidence đúng trong candidate pool nhưng bị reranker hạ hạng.
Bộ này mới theo tài liệu/ngôn ngữ nhưng chỉ một văn bản scan và do AI hỗ trợ soạn/đối chiếu;
OCR và model thiên tiếng Anh là các giới hạn. Không phải đánh giá pháp luật hiện hành.
Chi tiết: [báo cáo PDF tiếng Việt](report/individual/VIETNAMESE_EXTERNAL_TEST.md).

Chạy lại retrieval từ snapshot đã có:

```bash
.venv/bin/python -m starter.src.run_vietnamese
```

Index riêng `.qdrant_vi/`, giữ nguyên kho Alice và các kết quả cũ.
Để tái tạo OCR cần `pdftoppm`, `tesseract`, language pack `vie`:

```bash
.venv/bin/python starter/scripts/ocr_vietnamese.py data/vietnamese/13nd.signed.pdf
.venv/bin/python starter/scripts/prepare_vietnamese.py
```

PDF ký gốc không bị sửa; bản sao nguyên byte nằm tại `data/vietnamese/13nd.signed.pdf`. Manifest ghi hash và nguồn chính thức.
Các snapshot OCR/gold giữ nguyên lỗi OCR để đo đúng text đã index; cần người chấm xác nhận lại.
UI tại cổng **18763** có màn hình **Kiểm tra tiếng Việt** để xem bảng điểm, 20 câu và trace A/B/C/D,
mở text trang rồi bấm **Mở trang scan gốc** để đối chiếu PDF thật (UI đọc đường dẫn `local_path` tương đối trong manifest).
Màn hình này phát lại benchmark; ô truy vấn tự do hiện vẫn dùng corpus Alice.


## Kiểm tra toàn repo trước khi nộp

```bash
.venv/bin/python starter/scripts/audit_repo.py
.venv/bin/python -m unittest discover -s tests -v
```

Audit kiểm tra toàn bộ file bài nộp (Git tracked và untracked, loại trừ cache/môi trường được ignore),
manifest, nguồn/đơn vị, evidence, offset/chapter, trace, metrics, hash lịch sử,
link tài liệu và dấu hiệu secret. Kết quả tại `results/repo_audit.json` và `report/REPO_AUDIT.md`.
Không chạy lại benchmark để thay điểm. Đánh giá AI hỗ trợ đã được người dùng chấp nhận và khai báo rõ; audit kiểm tra hash, nhãn và hồ sơ chấp nhận. Kết quả không phải cam kết điểm số hoặc chứng nhận chấm độc lập của giảng viên.
