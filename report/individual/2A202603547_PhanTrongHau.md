# Báo cáo cá nhân — Day 06

Phan Trọng Hậu · 2A202603547 · L3A

## Dữ liệu và pipeline

Chủ đề: truy xuất bằng chứng trong *Alice’s Adventures in Wonderland*, Lewis Carroll.
Nguồn: https://www.gutenberg.org/ebooks/11 (bản cập nhật 26/06/2025).
Tác giả mất năm 1898; trang nguồn công bố public domain tại Mỹ.
Giữ nguyên bản tải và toàn bộ Project Gutenberg License ở `data/alice.txt`;
manifest ghi ngày truy cập, version và SHA-256. Không có dữ liệu cá nhân hoặc key.

Corpus có **82 đơn vị nội dung**, không phải 82 trang PDF. Mỗi đơn vị ≥1.500 ký tự
sau chuẩn hóa NFC: gộp các đoạn liên tiếp trong cùng chương đến ngưỡng,
ghép phần dư ngắn vào đơn vị cuối chương. Không lặp nội dung để đạt số lượng.
Bỏ bìa, mục lục, illustration và giấy phép khỏi phần embedding; vẫn giữ trong bản gốc.
`data/pages.json` chứa toàn văn đơn vị; `data/manifest.json` ghi số ký tự,
chương và offset đầu đơn vị trong chương. Không có OCR hoặc trang rỗng.

Chuẩn hóa xuống dòng và whitespace trong đoạn; giữ ranh giới đoạn.
Hạn chế: thơ bị gộp dòng, định dạng nhấn mạnh `_..._` còn giữ nguyên;
đơn vị nguồn chỉ là vị trí truy vết nhân tạo có quy tắc, không tương đương trang sách in.
`load_pdf` cũng hỗ trợ trang vật lý và cảnh báo thiếu text nhưng không được dùng trong thí nghiệm này.

Embedding **BAAI/bge-small-en-v1.5**, 384 chiều, ONNX CPU qua FastEmbed 0.9.1,
dùng `passage_embed` cho documents và `query_embed` cho queries, cùng model mọi cấu hình.
Snapshot ONNX repo `Qdrant/bge-small-en-v1.5-onnx-Q`, revision và hash từng file trong
`results/model_snapshot.json`. Lần tải lại upstream có thể đổi revision; đối chiếu hash trước khi so kết quả.
Vector store **qdrant-client 1.20.0 local persistent** tại `.qdrant/`, collection A/B/C,
cosine, exact brute-force search, top-3. Qdrant tự quản persistence, không tự viết SQLite hoặc vector search.
Môi trường Python 3.14.9; các phiên bản và checksum nằm trong `results/run.json` và `requirements.lock.txt`.

Metadata: `document_id`, `source` là chuỗi; `page` là số thứ tự đơn vị;
`chapter`, `chapter_title`, `language` lấy từ heading/ngôn ngữ bản gốc;
`start/end` là offset ký tự chuẩn hóa trong đơn vị. Filter `chapter` kiểu chuỗi Roman numeral,
giúp phân biệt phạm vi chương, chỉ nhận giá trị từ câu hỏi, không dùng gold source/page.

Mỗi lần ingest thay snapshot collection, loại mọi chunk lỗi thời; ID là hash nguồn/offset/nội dung.
Thực tế chạy hai lần cho mỗi collection, số lượng giữ nguyên 350/192/192.
Cách này đơn giản nhưng không atomic, chưa phù hợp ghi đồng thời ở production.
Không fallback sang mock. `results/errors.log` rỗng vì không có exception của pipeline;
SDK có warning local search vốn đã exact, không ảnh hưởng kết quả.

## Cấu hình và benchmark

- A: cửa sổ 500 ký tự, overlap 50, không filter.
- B: gộp đoạn tối đa 1.000 ký tự; đoạn quá dài cắt theo khoảng trắng, không overlap; không filter.
- C: dùng đúng chunk và vector của B, chỉ thêm filter chương khi câu hỏi cung cấp.

A–B thay chiến lược chunking (bao gồm size và overlap), nên không tách riêng tác động size khỏi ranh giới đoạn.
B–C chỉ thay metadata filter. Mọi cấu hình cùng corpus, embedding, metric và 20 câu.

Benchmark được viết và kiểm tra evidence trước lần truy xuất đầu:
15 dev q01–q15 thuộc chương I–X, 5 test q16–q20 thuộc XI–XII.
Bốn câu có filter: q05, q08, q13 (dev), q16 (test), chương đã nêu ngay trong câu hỏi.
Mỗi evidence được kiểm tra có nguyên văn trong nguồn chuẩn hóa; các nguồn tương đương có thể thêm `alternatives`.
Không có câu không đáp án. Bao phủ câu trực tiếp, diễn đạt lại và điều kiện (q03, q18),
nhưng nhìn chung bộ câu còn dễ, nhiều câu trả lời ngắn.
Cùng một tác phẩm và nhân vật xuyên suốt gây tương quan dev/test; đây không phải holdout theo tài liệu độc lập.

Tiêu chí chọn được ghi trước trong `benchmark/protocol.json`:
ưu tiên dev Evidence Hit@3, rồi dev Hit@1, ít chunk hơn, cuối cùng tên cấu hình.
`selection.json` được ghi sau dev và trước mọi test retrieval. Không dùng test để đổi cấu hình.

## Kết quả chạy thật

Hit yêu cầu đúng nguồn + đơn vị và **đủ toàn bộ evidence trong một chunk**.
Chỉ đúng page nhưng thiếu evidence không phải hit; nhiều chunk hợp lại không thay metric chính.

| Strategy | Split | Hit@1 | Evidence Hit@3 | Chunks | Ingest gồm nạp lại (s) | API USD |
|---|---|---|---|---|---|---|
| A | dev | 5/15 | 9/15 | 350 | 15.559 | 0 |
| A | test | 5/5 | 5/5 | 350 | 15.559 | 0 |
| B | dev | 9/15 | 13/15 | 192 | 16.836 | 0 |
| B | test | 4/5 | 4/5 | 192 | 16.836 | 0 |
| C | dev | 9/15 | 14/15 | 192 | 1.032 | 0 |
| C | test | 4/5 | 4/5 | 192 | 1.032 | 0 |

C dùng cache vector B nên thời gian thấp không chứng minh filter làm embedding nhanh hơn.
A/B gồm tạo embedding; tất cả gồm hai lần ghi snapshot. Chưa đo riêng latency truy vấn,
chưa đo RAM, chưa tính CPU/điện; chi phí 0 là **chi phí API**.

| Strategy | Tổng ký tự chunk | Min / median / p95 / max | Độ dài trung bình |
|---|---|---|---|
| A | 156220 | 96 / 500.0 / 500.0 / 500 | 446.3 |
| B | 142600 | 79 / 756.5 / 986.5 / 999 | 742.7 |
| C | 142600 | 79 / 756.5 / 986.5 / 999 | 742.7 |

### Nhãn nội dung và metadata — AI hỗ trợ, người dùng đã chấp nhận

Codex đã đọc text của các chunk mẫu và top-3 test, đối chiếu nội dung để ghi nhãn và lý do.
Đây là **AI-assisted review**, không khai là học viên đã chấm thủ công độc lập.
Người dùng đã yêu cầu hoàn tất và chấp nhận cách đánh giá AI hỗ trợ trong phiên làm việc. Các CSV ghi `student_verified=user_accepted_ai_assisted_review`; `results/review_acceptance.json` lưu phát biểu chấp nhận, thời điểm và checksum. Đây là chấp nhận phương pháp/kết quả, không phải tuyên bố học viên đã tự đọc từng dòng hoặc có người chấm độc lập. Không suy nhãn coherence/grounding từ exact match.

Coherence lấy cùng 10 đơn vị nguồn đầu, tại offset giữa đơn vị theo protocol chốt trước.
Nếu overlap A có hai chunk bao phủ, đọc cả hai và ghi một nhãn vị trí
(cả hai cùng mức trong mẫu này); B/C có cùng mẫu và nhãn vì chunk giống hệt.
Mẫu chỉ phủ chương I–II nên không đại diện toàn corpus. Thang 0/1/2 theo GUIDE.

| Strategy | Coherence /2 (n=10) | Metadata đúng/đủ | Top-3 tuân thủ filter test | Grounding counts 0/1/2 | Grounding mean /2 |
|---|---|---|---|---|---|
| A | 1.00 | 15/15 | 0/1 | 0 / 0 / 5 | 2.00 |
| B | 1.90 | 15/15 | 1/1 | 1 / 0 / 4 | 1.60 |
| C | 1.90 | 15/15 | 1/1 | 1 / 0 / 4 | 1.60 |

Metadata kiểm tra toàn bộ 5 test × top-3 × 3 cấu hình = 45 bản ghi:
source/document ID/page/chapter và text tại start:end khớp nguồn; CSV ghi từng dòng.
B tình cờ cũng tuân thủ filter ở q16 dù không cưỡng chế lọc; chỉ C bảo đảm phạm vi truy vấn.
`source + page + offset` giúp mở lại đúng evidence. Hạn chế: số unit không tương ứng trang in,
chapter không đủ diễn đạt điều kiện người dùng phức tạp và filter sai có thể loại bằng chứng đúng.

Grounding chỉ đánh giá độ đủ của **evidence retrieval**, không đánh giá độ chính xác trả lời LLM.
A đủ evidence cho cả 5 test; B/C thiếu hoàn toàn lời cook ở q17, bốn câu còn lại đủ.
Đường dẫn: `results/traces.jsonl`, `coherence_samples.json`, `coherence_review.csv`,
`grounding_review.csv`, `metadata_audit.csv`, `review_summary.json`.

## Phân tích và kết luận

**A–B:** dev Hit@3 tăng 9/15 → 13/15; số chunk giảm 350 → 192,
coherence mẫu tăng 1.00 → 1.90. Chunk dài hơn thường giữ đủ evidence và chủ ngữ,
nhưng làm embedding loãng đối với câu hỏi ngắn. Không thể kết luận cải thiện hoàn toàn do theo đoạn
vì đồng thời thay size và overlap trong chiến lược chunking.

**B–C:** dev tăng 13/15 → 14/15, chủ yếu nhờ q13 lọc chương IX loại các đoạn
về bài học ở chương khác. Test không đổi 4/5. Với q16, B đã lấy ba đoạn đúng chương nên filter
không tạo thêm gain; với q17 không có filter, C phải trả giống B.

Ví dụ lỗi đã đối chiếu trace:

1. **q08, A, unit 35/chương VI:** top-1 bắt đầu ở đuôi “hess, and that’s why”,
   mất phát biểu “It’s a Cheshire cat”. Đúng unit nhưng không đủ evidence;
   các chunk còn lại trong top-3 cũng không đủ. Đây là lỗi cắt ý, không được tính hit chỉ vì đúng page.
2. **q14, C, unit 62/chương IX:** top-1 bàn về Classics master là crab và số giờ lessons,
   không có Drawling-master conger-eel ghé mỗi tuần. Cả top-3 thiếu evidence;
   metadata đầy đủ không bảo đảm semantic ranking đúng.
3. **q17 test, B/C, gold unit 75/chương XI:** top-3 nói mustard (57),
   diễn giải tarts (80), bài vè trộm tarts (72), không có lời cook “Pepper, mostly”.
   A tìm đúng đoạn ngắn ở top-1. Giữ nguyên cấu hình sau khi thấy lỗi test.

Chọn **C theo dev**, không đổi sang A dù A thắng trên 5 câu test.
Phù hợp khi câu hỏi cung cấp phạm vi chương đáng tin và ưu tiên đủ evidence trên dev.
Không có bằng chứng chiến lược này tốt nhất tổng quát. Mẫu test nhỏ và cùng truyện,
evidence khớp chuỗi có thể bỏ sót diễn đạt tương đương, nhãn AI chưa có người chấm độc lập,
coherence chỉ phủ đầu sách; thời gian có cache và chưa đo lặp nên không phải benchmark hiệu năng chặt chẽ.

Nếu mở rộng: tạo benchmark mới có nhiều câu điều kiện/đa bằng chứng và người chấm độc lập;
đánh giá sentence-aware splitting, overlap theo câu, reranker hoặc hybrid trên dev mới;
không dùng tập test đã xem để tinh chỉnh rồi gọi là holdout độc lập.

## Tái lập, AI và trạng thái nộp

Chạy từ root theo README: cài `requirements.lock.txt`,
`python -m starter.src.run`, `python -m unittest discover -s tests -v`.
Bốn test đã pass: phủ nội dung/ranh giới chunk, evidence đầy đủ/alternative,
vector-store filter/persistence/snapshot thay dữ liệu, chuẩn hóa và số đơn vị corpus.
Vectors tổng hợp trong unit test chỉ để kiểm tra backend; mọi số liệu thí nghiệm dùng model thật.
Không có kết quả chatbot sinh câu trả lời; không yêu cầu chatbot trong đề.

AI sử dụng: Codex đọc đề, viết code/benchmark, thực thi model local, kiểm tra số liệu,
đọc mẫu và hỗ trợ phân tích/nhãn. Người dùng đã chấp nhận phương pháp và kết quả đánh giá AI hỗ trợ; không khai là chấm độc lập của con người. Điểm và lý do giữ nguyên, chỉ chốt trạng thái chấp nhận. Bản bàn giao là commit trên nhánh main của repo ghi trong STUDENT.md; lấy hash bằng `git rev-parse HEAD`. Học viên có thể đọc lại code/trace để trình bày và gửi link qua kênh lớp; không tự suy diễn deadline hoặc khai đã gửi qua kênh lớp.


## Mở rộng D — hybrid + cross-encoder sau khi đã xem test

Mục tiêu: sửa lỗi ranking bằng candidate retrieval rộng hơn; giữ nguyên kết quả A/B/C và quyết định C ban đầu.
Giao thức riêng `benchmark/extension_protocol.json` chốt trước khi chạy D:
chunk và embedding đúng B, dense top-20 + BM25 top-20, RRF đều trọng số (k=60),
rerank 20 ứng viên bằng `Xenova/ms-marco-MiniLM-L-6-v2`, lấy top-3.
BM25 k1=1.5, b=0.75, token Unicode lower-case bỏ stopword; IDF trên toàn bộ corpus B;
filter áp dụng trước xếp hạng ở cả nhánh dense và lexical. Reranker chạy CPU qua FastEmbed,
đầu ra là raw logit, không phải cosine hoặc xác suất. Không đưa evidence/gold vào retriever.
Nguồn API/model: https://qdrant.tech/documentation/fastembed/fastembed-rerankers/
Snapshot và hash tại `results/extension/model_snapshot.json`.

Không đổi cấu hình D sau khi xem kết quả. Thêm q21–q30 có evidence đã kiểm tra,
chốt trước lần chạy D, đánh giá cả A/B/C/D. Cùng corpus nên chỉ mới ở cấp câu hỏi,
không tuyên bố độc lập hoàn toàn hoặc áp dụng cho mọi dữ liệu.
`results/extension/freeze.json` ghi thời điểm và checksum đầu vào trước truy xuất.

| Cấu hình / tập | Hit@1 | Evidence Hit@3 |
|---|---|---|
| D / dev gốc | 12/15 | 15/15 |
| D / test gốc đã xem | 5/5 | 5/5 |
| A / 10 câu mới | 6/10 | 10/10 |
| B / 10 câu mới | 7/10 | 9/10 |
| C / 10 câu mới | 8/10 | 10/10 |
| D / 10 câu mới | 9/10 | 10/10 |

D đạt full Hit@3 trên cả ba tập được đo, nhưng chưa full top-1 dev và bộ câu mới.
Test gốc chỉ là diagnostic sau khi phân tích lỗi, không báo là holdout độc lập.
Ở tập mới D không hơn A/C về Hit@3; top-1 tốt hơn trong mẫu nhỏ này,
đổi lại thêm model và chi phí tính toán. Chưa kiểm tra khả năng tổng quát trên tác phẩm khác.

q14: chunk chứa Drawling-master ở dense rank 5, BM25 rank 1; reranker đưa lên top-1.
q17: chunk có “Pepper, mostly” cũng ở dense rank 5, BM25 rank 1;
reranker đưa lên top-1, sửa lỗi top-3 của B/C mà không hardcode đáp án.
q26 là lỗi còn lại: top-1 D nói về Tortoise thay vì nguồn gốc tên “lessons”;
evidence đầy đủ ở rank 3. Giữ nguyên lỗi, không sửa tham số theo bộ mới.

30 truy vấn D trung bình 1.012 giây/câu (gồm embed query, dense, BM25, fusion và rerank,
không tính nạp model riêng). Tổng lượt mở rộng 30.933 giây; reranker đã có cache tải,
chi phí API 0 USD, không tính điện/CPU. Không so trực tiếp với thời gian ingest A/B/C.
D dùng lại 192 chunk B, không nhân đôi collection và không gọi dịch vụ trả phí.
Không suy nhãn grounding/coherence cho D chỉ từ Hit@3; chưa có nhãn thủ công mới.

Artifacts mở rộng: `results/extension/traces.jsonl` (60 trace, gồm 30 D và 30 A/B/C trên bộ mới),
`metrics.json`, `run.json`, `freeze.json`, `model_snapshot.json`, `tests.txt`.
Checksum chứng minh trace và metrics A/B/C gốc giữ nguyên. Sáu tests pass, bao gồm
hybrid fusion/dedup/rerank và filter cả hai nhánh; vector/reranker giả chỉ có trong fixture unit test,
tất cả số liệu benchmark dùng model thật. UI hỗ trợ D trực tiếp và trace đã lưu,
ghi rõ logit và trạng thái sau test. Chạy `python -m starter.src.run_extension` khi UI đã dừng,
sau đó `python -m starter.src.demo --port 18763`.

## Kiểm tra chuyển miền sang PDF tiếng Việt

Đã thêm phép thử trên file `13nd.signed.pdf` do học viên cung cấp (Nghị định 13/2023/NĐ-CP,
bản scan 39 trang). Chốt 20 câu tiếng Việt mới trước khi chạy, giữ nguyên model/cấu hình.
Evidence Hit@3: A 6/20, B 11/20, C 12/20, D 16/20. Không sửa tham số theo tập mới.
Bốn lỗi D còn lại là reranking hạ chunk đúng dưới top-3; không tuyên bố đạt tuyệt đối.
Xem phương pháp OCR, giới hạn và phân tích trong [báo cáo nguồn mới](VIETNAMESE_EXTERNAL_TEST.md).


## Chốt hồ sơ đánh giá và bàn giao

Có đủ 5 khía cạnh bắt buộc cho A/B/C: retrieval theo split; 30 nhãn coherence cùng 10 vị trí;
45 bản ghi kiểm tra metadata; 15 nhãn grounding trên cùng 5 câu test; phân tích A–B và B–C,
ví dụ lỗi và tài nguyên. Người dùng đã chấp nhận đánh giá AI hỗ trợ; nguồn nhãn, thang điểm,
lý do, hash và trạng thái được công khai ở `results/review_acceptance.json` cùng ba CSV.
Không thay số liệu hoặc nâng nhãn để đạt điểm, không tuyên bố có người chấm độc lập.
D và tiếng Việt là thí nghiệm mở rộng; không dùng điểm test để sửa cấu hình rồi báo lại như holdout độc lập.
Kết quả audit và bộ kiểm thử cuối tại `results/repo_audit.json`, `repo_audit_tests.txt`, `repo_audit_ui.txt`.
Các mốc 4/6/8 tests ở phần lịch sử thể hiện từng giai đoạn; kiểm tra chốt bài xem các file audit mới nhất.
Checklist đối chiếu đề tại `SUBMISSION_STATUS.md`. Nhánh bàn giao: `main`; hash commit được ghi trong bàn giao Git.
