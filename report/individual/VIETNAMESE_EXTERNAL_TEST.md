# Kiểm tra trên nguồn mới — PDF tiếng Việt

## Thiết kế trước khi chạy

Dùng đúng file học viên cung cấp: `/home/ryanphan/Downloads/13nd.signed.pdf`.
Đây là bản scan ký năm 2023 của Nghị định 13/2023/NĐ-CP về bảo vệ dữ liệu cá nhân;
nguồn đối chiếu chính thức: https://chinhphu.vn/default.aspx?docid=207759&pageid=27160 .
Bài này đánh giá **truy xuất theo bản tài liệu được cung cấp**, không khẳng định hiệu lực pháp lý hiện tại
và không sinh tư vấn pháp luật.

Đổi sang tài liệu và ngôn ngữ mới để kiểm tra khả năng khái quát ngoài Alice.
Chốt 20 câu **external_test** trước lần truy xuất đầu, không dùng chúng chọn tham số/model.
Không chia thêm dev vì các cấu hình đã được chốt trên corpus cũ;
không dùng tập này để chỉnh D rồi gọi lại là test độc lập.
Bốn câu có chương do câu hỏi cung cấp: vi01/I, vi06/II, vi18/III, vi19/IV.
Các câu gồm trực tiếp, diễn đạt lại, điều kiện và ngoại lệ; giữ tiếng Việt có dấu, không dịch sang tiếng Anh.
Tác giả câu hỏi/nhãn là Codex AI hỗ trợ; người dùng đã chấp nhận phương pháp đánh giá trong phiên làm việc (xem `results/review_acceptance.json`), không tuyên bố có người chấm độc lập.

Giữ nguyên BGE Small EN v1.5 (384 chiều), reranker ms-marco-MiniLM-L-6-v2,
A fixed 500/overlap50, B đoạn max1000, C=B+filter, D dense20+BM25_20+RRF60+rerank20→top3.
Cả embedding lẫn reranker hiện thiên về tiếng Anh; tokenizer/stopwords BM25 cũng giữ nguyên.
Đây là phép đo chuyển miền/ngôn ngữ, chưa phải cấu hình tối ưu tiếng Việt.

## OCR và nguồn

39 trang vật lý đều không có text extractable qua pypdf.
OCR bằng **Tesseract 5.3.4**, ngôn ngữ `vie`, Poppler render **200 DPI**, PSM 3, bốn workers.
Lưu text sau NFC/chuẩn hóa whitespace và giữ số trang vật lý, không gộp trang thành unit nhân tạo.
Có 28 trang phần nghị định, 1 trang danh mục phụ lục, 10 trang mẫu biểu;
index toàn bộ để các mẫu biểu có thể làm distractor.
**Không tính 39 trang vật lý thành 39 trang nội dung đầy đủ đáp ứng rubric.**
Đây là corpus bổ sung; corpus Alice vẫn giữ nguyên đủ 82 đơn vị hợp lệ của bài gốc.

Đã đọc ảnh trang chứa evidence và ảnh chuyển chương: I ở trang 1, II trang 7,
III giữa trang 24, IV giữa trang 27, phụ lục từ trang 29.
OCR làm hỏng số chương II/III nên giá trị metadata được đối chiếu bằng ảnh,
không đoán dựa trên câu hỏi. Chunk dừng ở ranh giới chương, giữ offset đúng text trang nguồn;
đây là xử lý ranh giới nguồn cho tài liệu mới, áp dụng đều cho A/B/C/D.
Bản scan ký gốc giữ nguyên byte và SHA-256, không OCR ghi đè hoặc flatten chữ ký.
Sau lần chạy, đã bổ sung bản sao nguyên byte tại `data/vietnamese/13nd.signed.pdf` để repo tự chứa dữ liệu. Manifest hiện tại dùng đường dẫn tương đối; manifest tại thời điểm chạy được giữ nguyên byte trong `results/vietnamese/input_snapshots/manifest.json`, với sidecar giải thích thay đổi metadata. Hash và điểm lịch sử không bị viết lại. UI và pipeline ưu tiên bản PDF trong repo.

Không sửa chính tả OCR toàn cục, không sửa theo lỗi retrieval.
Ví dụ OCR đọc “dữ” thành “đữ”, “thể” thành “thê”, “kể” thành “kế”.
Gold evidence giữ nguyên text OCR và đã kiểm tra tồn tại trước truy xuất;
ảnh gốc được dùng kiểm tra ý nghĩa đáp án. Không đo CER/WER vì chưa có bản chép tay toàn văn;
không tuyên bố OCR hoàn hảo hoặc nguyên nhân chính xác của mọi lỗi ranking.

## Kết quả lần chạy đã chốt

| Cấu hình | Hit@1 | Evidence Hit@3 | Chunk |
|---|---|---|---|
| A | 3/20 (15%) | 6/20 (30%) | 154 |
| B | 4/20 (20%) | 11/20 (55%) | 88 |
| C | 5/20 (25%) | 12/20 (60%) | 88 |
| D | 13/20 (65%) | 16/20 (80%) | 88, dùng lại B |

Định nghĩa hit giữ nguyên: đúng document/page và đủ toàn bộ evidence trong **một chunk**.
Lưu 80 trace × top-3 = 240 kết quả; D còn lưu ứng viên và vị trí dense/BM25/logit.
Nạp lại A/B/C hai lần giữ đúng 154/88/88 bản ghi, không trùng.
Vector store `.qdrant_vi/` tách hoàn toàn `.qdrant/` của Alice.
Checksum xác nhận benchmark, kết quả và trace Alice gốc/mở rộng giữ nguyên.

A→B tăng Hit@3 6→11; B→C tăng 11→12, chủ yếu do vi19 giới hạn đúng Chương IV.
C→D tăng 12→16 nhưng D **không thắng mọi câu**: vi10 C có evidence trong top-3, D lại đánh rớt.
Do D thay cả candidate retrieval và reranking, chưa thể tách đóng góp riêng của BM25/RRF/reranker;
cần ablation trên tập dev mới nếu muốn kết luận nhân quả chi tiết.
Không thêm nhãn coherence/grounding thủ công cho lần chạy này và không gọi Hit@3 là độ đúng câu trả lời LLM.

## Bốn lỗi còn lại của D

Cả bốn câu đều có chunk chứa đủ gold trong tập ứng viên rerank; không phải evidence bị cắt mất
hoặc không được lấy vào candidate pool. Reranker xếp chúng dưới top-3:

| Câu | Gold trang | Hạng BM25 | Hạng dense | Hạng sau rerank | Nhận xét |
|---|---|---|---|---|---|
| vi03 | 3 | 2 | ngoài top-20 | 7 | Lẫn định nghĩa Bên Kiểm soát với Bên Xử lý/Bên Kiểm soát và xử lý. |
| vi06 | 9 | 3 | ngoài top-20 | 18 | Không đưa mệnh đề im lặng không phải đồng ý vào top-3. |
| vi10 | 14 | 2 | 2 | 4 | Reranker đẩy evidence hạn xóa xuống sau các mệnh đề 72 giờ khác. |
| vi18 | 26 | 1 | 6 | 5 | Có đúng trang và chủ đề nhưng top-3 thiếu câu ghi/lưu nhật ký hệ thống. |

Đây là chẩn đoán sau khi đọc trace, không chỉnh cấu hình hoặc gold để cải thiện điểm.
vi03 có các vai trò định nghĩa gần nhau, cần người chấm xem xét tính tương đương/nguy cơ mơ hồ;
chỉ số hiện tại vẫn giữ gold đã chốt ở khoản định nghĩa trên trang 3.
Không thể từ một corpus nhỏ tách ảnh hưởng ngôn ngữ, OCR và thể loại văn bản.

D đạt 100% Hit@3 trên Alice nhưng chỉ 80% trên nguồn tiếng Việt này.
Đây là bằng chứng cụ thể rằng kết quả cũ không bảo đảm khái quát sang nguồn khác.
Tập mới vẫn chỉ một văn bản, do AI soạn và tự đối chiếu, chưa có reviewer độc lập;
không coi kết quả là chuẩn khách quan tuyệt đối.

## Tài nguyên và tái lập

Lần chạy không tính OCR: tổng khoảng 38.900 giây.
Thời gian retrieval trung bình, chưa gồm embed query dùng chung:
A 0.687 ms, B 0.561 ms, C 0.645 ms, D 950.791 ms.
D tốn thêm cross-encoder; số đo một lần trên corpus nhỏ, không phải benchmark hiệu năng tổng quát.
Chi phí API 0 USD, chưa tính CPU/điện. Model đã có cache tải từ lần trước.
Không bổ sung model đa ngữ trong lượt đánh giá này để giữ phép thử chuyển miền nguyên trạng.

```bash
# Cần Poppler và Tesseract với language pack vie; giữ PDF ở đường dẫn thực tế.
.venv/bin/python starter/scripts/ocr_vietnamese.py data/vietnamese/13nd.signed.pdf
.venv/bin/python starter/scripts/prepare_vietnamese.py
.venv/bin/python -m starter.src.run_vietnamese
.venv/bin/python -m unittest discover -s tests -v
```

Không chạy lại hai bước chuẩn bị để thay benchmark sau khi đã xem test mà không ghi phiên bản mới.
Các snapshot OCR/benchmark có sẵn nên có thể chỉ chạy `run_vietnamese` để tái lập retrieval.
UI/pipeline đọc `local_path` tương đối và kiểm tra SHA-256 bản PDF đã đóng gói, không phụ thuộc Downloads; kiểm tra SHA-256 nếu tải lại bản chính thức.

Artifacts: `data/vietnamese/manifest.json`, `pages.json`,
`benchmark/vietnamese_questions.json`, `vietnamese_protocol.json`,
`results/vietnamese/{freeze,metrics,statistics,run,error_analysis}.json`, `traces.jsonl`, `tests.txt`.
8 tests đã pass: bao gồm kiểm tra evidence, offset trang/chương, filter,
metric tái tính từ trace và giữ nguyên dữ liệu Alice.
UI có màn hình **Kiểm tra tiếng Việt**, đọc trace đã lưu, mở text OCR theo trang
và liên kết tới ảnh scan PDF gốc trên máy. UI không tự chuyển truy vấn Alice sang corpus tiếng Việt.
