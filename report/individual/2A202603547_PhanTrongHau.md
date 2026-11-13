# Báo cáo cá nhân — Day 06: Data Ingestion Engineering

**Họ tên:** Phan Trọng Hậu · **MSSV:** 2A202603547 · **Lớp:** L3A

## 1. Mục tiêu và dữ liệu

Xây pipeline Python đọc và chuẩn hóa tài liệu, chia chunk, tạo semantic embedding thật,
lưu vector bền vững có metadata filter, đánh giá top-3 và phân tích các đánh đổi.
Corpus chính đáp ứng yêu cầu tối thiểu: Alice’s Adventures in Wonderland, **82 đơn vị liên tiếp**,
mỗi đơn vị ít nhất **1.501 ký tự** sau chuẩn hóa; không nhân bản nội dung.
Bỏ bìa, mục lục và giấy phép khỏi phần index; bản Gutenberg nguyên vẹn vẫn giữ nguồn và giấy phép.
Unit là vị trí truy vết của text, không phải trang PDF hoặc trang sách in.

Mở rộng thêm bốn nguồn để kiểm tra tổng quát, trong đó ba nguồn là văn bản tiếng Việt:

| Nguồn | Bản gốc trong data | Phạm vi index |
|---|---|---|
| Alice (Gutenberg #11) | `data/alice.txt` | 82 đơn vị, 12 chương |
| Nghị định 13/2023/NĐ-CP | `data/vietnamese/13nd.signed.pdf` | 39 trang scan: 28 trang phần nghị định, 1 danh mục phụ lục, 10 trang mẫu biểu |
| Nghị định 69/2024/NĐ-CP | `data/multidoc/raw/nd69.pdf` | Toàn bộ 37 trang vật lý, gồm cả biểu mẫu |
| Nghị định 42/2022/NĐ-CP | `data/multidoc/raw/nd42.pdf` | Toàn bộ 19 trang vật lý |
| Sherlock Holmes (Gutenberg #1661) | `data/multidoc/raw/sherlock.txt` | Chỉ hai truyện đầu, 53 đơn vị ≥1.500 ký tự; bản gốc toàn sách và license được giữ |

Không tự quy 39/37/19 trang vật lý thành số trang nội dung đủ điều kiện.
Các văn bản pháp luật là **snapshot lịch sử**, dùng để đánh giá retrieval theo nguồn,
không phải tư vấn pháp luật hoặc xác nhận hiệu lực hiện tại.
Nguồn chính thức, giấy phép/sự cho phép, thời điểm truy cập, version, số ký tự và SHA-256 ở từng manifest;
`data/sources.json` là danh mục chung. Chỉ lưu một bản text chuẩn hóa cho mỗi nguồn.

## 2. Xử lý và lưu trữ

Chuẩn hóa Unicode NFC, whitespace; giữ ranh giới đoạn, document ID, source, page/unit và offset.
Alice chia theo nhóm đoạn liên tiếp ≥1.500 ký tự trong từng chương; phần dư ngắn ghép vào đơn vị cuối.
PDF scan dùng **Tesseract 5.3.4, vie, 200 DPI, PSM 3**; giữ nguyên byte PDF ký, không flatten hoặc ghi đè.
Đã đối chiếu ảnh trang chứa evidence với text OCR. Không sửa chính tả OCR theo kết quả truy xuất.
OCR còn lỗi như “đữ”, “thê”, “kế”; không có bản chép tay toàn văn nên chưa đo CER/WER.
Văn bản thơ có thể bị gộp dòng khi chuẩn hóa.

Metadata tối thiểu: `document_id`, `source`, `page`, `start/end`.
`chapter` lấy từ heading nguồn; Nghị định 13 có ranh giới chương được đối chiếu ảnh khi OCR sai số chương.
Trong phép thử mới, filter `language` dùng giá trị vi/en khi câu hỏi/ngữ cảnh đã cung cấp.
Không lọc bằng gold source/page. Các PDF mới chưa trích xuất chương thì để trống, không đoán.

Backend: **Qdrant local persistent**, cosine exact search, top-3; không tự thay bằng SQLite/vector Python.
Kho Alice: `.qdrant/`; Nghị định 13: `.qdrant_vi/`; kho 5 nguồn: `.qdrant_multidoc/`.
ID chunk ổn định từ nguồn, vị trí và text. Nạp snapshot hai lần giữ nguyên số bản ghi,
loại chunk lỗi thời khi corpus thay đổi; cách này không atomic và chưa phù hợp ghi đồng thời ở production.
Không fallback mock khi model hoặc backend lỗi. Vector tổng hợp chỉ có trong unit test.

Embedding gốc: **BAAI/bge-small-en-v1.5, 384 chiều**, FastEmbed passage/query adapters.
Embedding đa ngữ: **intfloat/multilingual-e5-small**, ONNX INT8 từ Xenova,
384 chiều, mean pooling có attention mask, L2 normalize, prefix `query: ` / `passage: ` cho mọi ngôn ngữ,
giới hạn 512 token. Model/revision/checksum ở các `model_snapshot.json` và `e5_model_snapshot.json`.
Môi trường Python 3.14.9, FastEmbed 0.9.1, qdrant-client 1.20.0; dependencies trong `requirements.lock.txt`.

## 3. Cấu hình và benchmark

| Cấu hình | Chunk / model | Truy xuất |
|---|---|---|
| A | Fixed 500 ký tự, overlap 50 / BGE | Dense top-3, không filter |
| B | Gộp đoạn ≤1.000 ký tự / BGE | Dense top-3, không filter |
| C | Giống B | Thêm filter khi có input |
| D | Giống B | Dense20 + BM25_20 → RRF k=60 top20 → cross-encoder ms-marco-MiniLM-L-6-v2 → top3 |
| E | Giống B / BGE | Cùng candidate retrieval như D; dùng RRF top3, bỏ reranker |
| F | Giống B / E5 đa ngữ | Dense top3 + filter |
| G | Giống B / E5 đa ngữ | Dense20 + BM25_20 → RRF top3 + filter |

B–C chỉ đổi filter; A–B đổi cả size/overlap/ranh giới đoạn nên không tách riêng các yếu tố đó.
D–E kiểm tra bỏ reranker; C–F đổi embedding; F–G thêm lexical/fusion; E–G đổi embedding.
E/F/G là thí nghiệm mở rộng, không gộp vào yêu cầu giữ cùng model của A/B/C.
Cosine, reranker logit và RRF không cùng thang điểm và không phải xác suất trả lời đúng.

Bộ gốc: **20 câu = 15 dev / 5 test**, evidence được kiểm tra trong nguồn trước truy xuất.
4 câu có filter chương: q05, q08, q13 và q16 (test). Chọn cấu hình bằng dev Hit@3,
rồi Hit@1, ít chunk hơn; ghi quyết định C trước test, không đổi sang A khi thấy test tốt hơn.
Dev chương I–X, test XI–XII; cùng tác phẩm/nhân vật nên không độc lập theo tài liệu.

D được thêm **sau khi đã xem test gốc**: điểm test đó chỉ là diagnostic.
Có thêm 10 câu tiếng Anh mới, chốt trước D; vẫn cùng sách, không coi là độc lập hoàn toàn.
Nguồn Nghị định 13 có 20 câu tiếng Việt mới, giữ nguyên A/B/C/D; không chọn tham số trên tập này.

Phép thử nhiều nguồn: **45 câu mới**, chốt trước chạy; dev là Nghị định 69 (15 câu),
test là Nghị định 42 và Sherlock Holmes (30 câu). Tài liệu dev/test không trùng nhau;
Alice/Nghị định 13 cùng nằm trong index làm distractor. Dùng cùng **566 chunk** cho C/D/E/F/G.
Chọn G trên dev trước test; không sweep sau test. 20 câu Nghị định 13 cũ chỉ chạy diagnostic sau cùng.
Có trực tiếp, diễn đạt lại, phủ định, điều kiện, ngoại lệ, hai dữ kiện, filter và truy vấn khác ngôn ngữ nguồn.

## 4. Kết quả corpus chính và năm khía cạnh

Hit yêu cầu đúng source/page và **đủ evidence đã chốt trong một chunk**.
Chỉ đúng page hoặc ghép evidence từ nhiều chunk không thay định nghĩa chính.
Exact alternatives được chấp nhận; đánh giá tương đương về ý nghĩa vẫn là giới hạn của bộ đo.

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Chunk | Ingest gồm nạp lại (s) | API USD |
|---|---|---|---|---|---|---|
| A | dev | 5/15 | 9/15 | 350 | 15.559 | 0 |
| A | test | 5/5 | 5/5 | 350 | 15.559 | 0 |
| B | dev | 9/15 | 13/15 | 192 | 16.836 | 0 |
| B | test | 4/5 | 4/5 | 192 | 16.836 | 0 |
| C | dev | 9/15 | 14/15 | 192 | 1.032 | 0 |
| C | test | 4/5 | 4/5 | 192 | 1.032 | 0 |

C tái sử dụng cache vector của B; không kết luận C làm embedding nhanh hơn.
Độ dài A: min/median/p95/max = 96/500/500/500, trung bình 446,3; tổng 156.220 ký tự kể cả overlap.
B/C: 79/756,5/986,5/999, trung bình 742,7; tổng 142.600 ký tự chunk.
Số bản ghi sau nạp lại: A 350, B/C 192, không trùng.

Coherence lấy cùng 10 vị trí giữa 10 đơn vị đầu theo protocol; A có hai chunk overlap ở một vị trí,
đọc cả hai (cùng mức). Thang 0 = mất ý/chủ thể, 1 = hiểu một phần, 2 = trọn ý/tự hiểu được.
Grounding đọc top-3 cùng 5 câu test: 0 không evidence, 1 thiếu điều kiện, 2 đủ trả lời và truy nguồn.
Metadata kiểm tra toàn bộ 45 kết quả test với source/page/chapter/offset nguồn.
Các nhãn có lý do cụ thể, không suy điểm nội dung chỉ từ exact match.

| Cấu hình | Coherence /2 (n=10) | Metadata đủ/đúng | Top3 tuân thủ filter test | Grounding counts 0/1/2 | Grounding /2 |
|---|---|---|---|---|---|
| A | 1.00 | 15/15 | 0/1 | 0/0/5 | 2.00 |
| B | 1.90 | 15/15 | 1/1 | 1/0/4 | 1.60 |
| C | 1.90 | 15/15 | 1/1 | 1/0/4 | 1.60 |

A–B: dev Hit@3 tăng 9→13/15, coherence tăng 1,00→1,90, chunk giảm 350→192;
đổi lại chunk dài có thể loãng tín hiệu truy vấn. B–C: 13→14/15, chủ yếu q13 lọc chương IX.
B tình cờ cũng tuân thủ chương ở q16, nhưng chỉ C cưỡng chế filter.
`source + page + offset` giúp truy vết; unit không phải trang in và filter sai có thể loại evidence đúng.
Grounding là chất lượng **bằng chứng truy xuất**, không phải độ chính xác câu trả lời sinh bởi LLM.

Ví dụ sai và đánh đổi:
- q08/A, unit 35: đúng page nhưng top-1 bắt đầu ở đuôi câu, mất “It’s a Cheshire cat”; không đủ gold.
- q14/C, unit 62: lấy đoạn Classics master/crab và giờ lessons, thiếu conger-eel ghé mỗi tuần.
- q17/B/C, gold 75: top3 nói mustard/tarts/bài vè, thiếu “Pepper, mostly”; A tìm đúng top1.
- D đưa gold q14 và q17 từ dense rank 5, BM25 rank 1 lên top1; q26 bộ mới vẫn sai top1, đúng rank3.

## 5. Kiểm tra nguồn mới và các biến thể

| Phép thử | C | D | E | F | G |
|---|---|---|---|---|---|
| Nghị định 13 riêng, Hit@3 /20 | 12 | 16 | — | — | — |
| 5 nguồn: dev /15 | 8 | 10 | 9 | 10 | 11 |
| 5 nguồn: test mới /30 | 12 | 18 | 15 | 17 | 19 |
| 5 nguồn: diagnostic cũ /20 | 7 | 15 | 14 | 16 | 18 |

D trên Alice: Hit@3 15/15 dev, 5/5 test đã xem, 10/10 bộ câu mới; Hit@1 tương ứng 12/15, 5/5, 9/10.
Không lấy kết quả này làm bảo đảm tổng quát: D chỉ 16/20 trên nguồn tiếng Việt riêng.
Bốn lỗi vi03/vi06/vi10/vi18 đều có gold trong pool nhưng bị rerank xuống hạng 7/18/4/5;
vi10 là trường hợp reranker làm xấu kết quả so với C. OCR và model tiếng Anh là các giới hạn.

| Cấu hình | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 | Retrieval trung bình ms* |
|---|---|---|---|---|---|
| C | 4/15 | 8/15 | 8/30 | 12/30 | 2.6 |
| D | 7/15 | 10/15 | 11/30 | 18/30 | 961.6 |
| E | 8/15 | 9/15 | 10/30 | 15/30 | 3.5 |
| F | 10/15 | 10/15 | 15/30 | 17/30 | 1.7 |
| G | 10/15 | 11/15 | 17/30 | 19/30 | 3.8 |

* Chưa gồm thời gian embed query dùng chung, được lưu riêng trong trace. D tốn thêm cross-encoder;
G không có bước đó. Ingest của lần chạy thành công dùng cache; không coi khoảng 2 giây ghi collection là thời gian tạo embedding từ đầu.
Có lỗi điều phối ghép trùng trường `kind` ở lần đầu, đã sửa trước khi có kết quả dev/test hoàn chỉnh;
không đổi câu hỏi, gold, model hoặc tham số; embeddings đã tạo được dùng lại.

G thắng trên dev 11/15 rồi được cố định. Trên test mới G 19/30, D 18/30: chỉ hơn một câu, chưa đủ
kết luận mạnh. G so với D có 3 ca thắng (m4201, m4213, msh07), 2 ca thua (msh03, msh13).
Theo nguồn: Nghị định 42 G 13/15, D 11/15; Sherlock G 6/15, D 7/15.
Không có cấu hình tốt nhất mọi nguồn: model đa ngữ/fusion giúp tiếng Việt nhưng vẫn có thể làm kém truyện tiếng Anh.
E bỏ reranker chỉ đạt 15/30, thấp hơn D; F đa ngữ dense đạt 17/30; G thêm BM25/RRF lên 19/30.

## 6. Kết luận và giới hạn

C là lựa chọn baseline theo dev ban đầu; G là lựa chọn theo dev của thí nghiệm 5 nguồn.
Giữ nguyên các quyết định sau khi xem test. Tập test nhỏ, một nguồn dev và hai nguồn test,
nhãn đối chiếu nguồn chưa có reviewer độc lập; không suy rộng ngoài corpus.
Không tách riêng hoàn toàn tác động ngôn ngữ, OCR, thể loại và cạnh tranh giữa tài liệu.
Strict quote có thể bỏ sót evidence tương đương; vi03 có các vai trò định nghĩa gần nhau cần cân nhắc khi diễn giải.
Mẫu coherence chỉ ở đầu Alice, không đại diện toàn bộ sách hoặc PDF mới.
Không có ablation đa ngữ reranker, đo RAM/điện hay kiểm thử hiệu năng lặp nhiều lần.
Chi phí API toàn bộ 0 USD, chưa tính CPU/điện/tải model.
Nếu mở rộng tiếp, dùng tài liệu dev tiếng Anh và tiếng Việt riêng, thêm nhãn độc lập và test mới;
không tinh chỉnh bằng các tập test đã xem rồi báo như đánh giá độc lập.

**Công cụ hỗ trợ:** sử dụng Codex để hỗ trợ triển khai và rà soát; số liệu lấy từ pipeline chạy local.
Nhãn nội dung dựa trên đối chiếu nguồn/trace có hỗ trợ công cụ, không khai là đánh giá độc lập của con người.

## 7. Tái lập và minh chứng

Setup/run theo README root. `requirements.lock.txt` khóa dependencies; dữ liệu nguồn kèm manifest và license/sự cho phép.
`results/` là baseline; `results/extension/` là D; `results/vietnamese/` là phép thử riêng;
`results/multidoc/` là 5 nguồn. Mỗi bộ có metrics, top3 trace, config/freeze, thời gian và model snapshot.
Ba CSV `coherence_review.csv`, `grounding_review.csv`, `metadata_audit.csv` lưu nhãn/lý do cho năm tiêu chí.
`results/provenance.json` ghi thay đổi metadata đóng gói và text đa nguồn được tái dựng, không thay câu hỏi/gold/text/rank/score.
Kết quả kiểm tra hiện tại ở `results/validation.json`; UI demo cổng 18763 có các màn hình so sánh và mở nguồn.
