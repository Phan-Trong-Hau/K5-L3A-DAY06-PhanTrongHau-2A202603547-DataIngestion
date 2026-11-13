"""Freeze a new Vietnamese source test and visually verified chapter boundaries."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'data/vietnamese'
pages=json.loads((out/'pages.json').read_text())
titles={'PREAMBLE':'Phần mở đầu','I':'Những quy định chung','II':'Hoạt động bảo vệ dữ liệu cá nhân',
        'III':'Trách nhiệm của cơ quan, tổ chức, cá nhân','IV':'Điều khoản thi hành','APPENDIX':'Phụ lục, biểu mẫu'}
# Source image review confirms chapter II p7 and chapter III p24 despite damaged OCR headings.
changes={1:('Chương I','I'),7:('', 'II'),24:('ChươnNH','III'),27:('Chương IV','IV'),29:('', 'APPENDIX')}
current='PREAMBLE'
for p in pages:
    segments=[];text=p['text'];change=changes.get(p['page'])
    if change:
        marker,new=change
        at=text.find(marker) if marker else 0
        if at<0:raise ValueError(f"Missing chapter boundary on page {p['page']}")
        if at>0:
            # Include noisy heading prefix in the new section, without changing source text.
            at=text.rfind('\n\n',0,at)+2
            segments.append(dict(start=0,end=at,chapter=current))
        current=new
        segments.append(dict(start=at,end=len(text),chapter=current))
    else:segments=[dict(start=0,end=len(text),chapter=current)]
    p['metadata'].update(chapter='/'.join(dict.fromkeys(s['chapter'] for s in segments)),chapter_title=' / '.join(titles[s] for s in dict.fromkeys(s['chapter'] for s in segments)),chapter_spans=segments)
(out/'pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
items=[
(2,'Trong Chương I, dữ liệu cá nhân được chia thành hai nhóm nào?','Dữ liệu cá nhân cơ bản và dữ liệu cá nhân nhạy cảm.','Dữ liệu cá nhân bao gôm đữ liệu cá nhân cơ bản và dữ liệu cá nhân nhạy cảm.','I','direct'),
(2,'Thông tin về nhóm máu có thuộc mục dữ liệu sức khỏe và đời tư trong hồ sơ bệnh án được liệt kê là dữ liệu nhạy cảm không?','Không; mục này loại trừ thông tin về nhóm máu.','b) Tình trạng sức khỏe và đời tư được ghi trong hồ sơ bệnh án, không bao gôm thông tin về nhóm máu;',None,'exception'),
(3,'Tổ chức quyết định mục đích và phương tiện xử lý dữ liệu cá nhân được gọi là bên nào?','Bên Kiểm soát dữ liệu cá nhân.','9. Bên Kiểm soát dữ liệu cá nhân là tổ chức, cá nhân quyết định mục đích và phương tiện xử lý dữ liệu cá nhân.',None,'paraphrase'),
(4,'Có được tự do mua bán dữ liệu cá nhân không, và ngoại lệ được nêu là gì?','Không được mua bán dưới mọi hình thức, trừ trường hợp luật có quy định khác.','Dữ liệu cá nhân không được mua, bán dưới mọi hình thức, trừ trường hợp luật có quy định khác.',None,'exception'),
(7,'Khi chủ thể yêu cầu hạn chế xử lý, thời hạn thực hiện thông thường là bao lâu và có ngoại lệ nào?','Trong 72 giờ sau yêu cầu, trừ trường hợp luật có quy định khác.','b) Việc hạn chế xử lý dữ liệu được thực hiện trong 72 giờ sau khi có yêu cầu của chủ thê dữ liệu, với toàn bộ dữ liệu cá nhân mà chủ thê dữ liệu yêu cầu hạn chê, trừ trường hợp luật có quy định khác.',None,'condition'),
(9,'Trong Chương II, nếu chủ thể không trả lời yêu cầu thì có thể xem đó là đồng ý xử lý dữ liệu không?','Không; im lặng hoặc không phản hồi không được coi là đồng ý.','Sự im lặng hoặc không phản hồi của chủ thê dữ liệu không được coi là sự đồng ý.','II','paraphrase'),
(9,'Nếu muốn xử lý dữ liệu cho nhiều mục đích, bên kiểm soát cần làm gì để chủ thể lựa chọn?','Liệt kê các mục đích để chủ thể đồng ý một hoặc nhiều mục đích.','Khi có nhiều mục đích, Bên Kiểm soát dữ liệu cá nhân, Bên Kiểm soát và xử lý dữ liệu cá nhân liệt kê các mục đích để chủ thể dữ liệu đồng ý với một hoặc nhiều mục đích nêu ra.',None,'condition'),
(10,'Rút lại đồng ý có làm mất tính hợp pháp của việc xử lý đã được đồng ý trước đó không?','Không ảnh hưởng đến tính hợp pháp của việc xử lý đã được đồng ý trước khi rút lại.','Việc rút lại sự đồng ý không ảnh hưởng đến tính hợp pháp của việc xử lý dữ liệu đã được đông ý trước khi rút lại sự đông ý.',None,'paraphrase'),
(12,'Phiếu yêu cầu cung cấp dữ liệu cá nhân phải được thể hiện bằng ngôn ngữ nào?','Tiếng Việt.','Phiếu yêu cầu cung cấp dữ liệu cá nhân phải được thể hiện bằng tiếng Việt',None,'direct'),
(14,'Yêu cầu xóa toàn bộ dữ liệu đã thu thập thường phải được thực hiện trong thời hạn nào?','Trong 72 giờ sau yêu cầu, trừ trường hợp pháp luật có quy định khác.','Việc xóa dữ liệu được thực hiện trong 72 giờ sau khi có yêu cầu của chủ thể đữ liệu với toàn bộ dữ liệu cá nhân mà Bên Kiểm soát dữ liệu cá nhân, Bên Kiểm soát và xử lý dữ liệu cá nhân thu thập được, trừ trường hợp pháp luật có quy định khác.',None,'condition'),
(15,'Khi cần xử lý ngay để bảo vệ tính mạng hoặc sức khỏe, ai phải chứng minh trường hợp khẩn cấp?','Bên Kiểm soát, Bên Xử lý, Bên Kiểm soát và xử lý, Bên thứ ba phải chứng minh trường hợp này.','Trong trường hợp khân cấp, cần xử lý ngay đữ liệu cá nhân có liên quan để bảo vệ tính mạng, sức khỏe của chủ thể dữ liệu hoặc người khác. Bên Kiểm soát đữ liệu cá nhân, Bên Xử lý đữ liệu cá nhân, Bên Kiểm soát và xử lý dữ liệu cá nhân, Bên thứ ba có trách nhiệm chứng minh trường hợp này.',None,'condition'),
(16,'Với trẻ từ đủ 7 tuổi, thông thường cần sự đồng ý của những ai để xử lý dữ liệu và ngoại lệ được viện dẫn là gì?','Cần đồng ý của trẻ và cha, mẹ hoặc người giám hộ; trừ trường hợp Điều 17.','Việc xử lý dữ liệu cá nhân của trẻ em phải có sự đồng ý của trẻ em trong trường hợp trẻ em từ đủ 7 tuổi trở lên và có sự đồng ý của cha, mẹ hoặc người giám hộ theo quy định, trừ trường hợp quy định tại Điều 17 Nghị định này.',None,'exception'),
(17,'Báo cáo vi phạm bảo vệ dữ liệu phải gửi trong bao lâu, theo mẫu nào và nếu chậm thì cần bổ sung gì?','Chậm nhất 72 giờ sau vi phạm, Mẫu số 03; nếu thông báo sau 72 giờ phải kèm lý do chậm, muộn.','chậm nhất 72 giờ sau khi xảy ra hành vi vi phạm theo Mẫu số 03 tại Phụ lục của Nghị định này. Trường hợp thông báo sau 72 giờ thì phải kèm theo lý do thông báo chậm, muộn.',None,'condition'),
(19,'Hồ sơ đánh giá tác động xử lý dữ liệu phải gửi bản chính theo mẫu nào và trong bao nhiêu ngày kể từ khi bắt đầu xử lý?','Mẫu số 04, trong 60 ngày kể từ ngày tiến hành xử lý.','01 bản chính theo Mẫu số 04 tại Phụ lục của Nghị định này trong thời gian 60 ngày kế từ ngày tiến hành xử lý đữ liệu cá nhân.',None,'direct'),
(21,'Bên chuyển dữ liệu ra nước ngoài có bao nhiêu ngày để hoàn thiện hồ sơ sau ngày yêu cầu?','10 ngày kể từ ngày yêu cầu.','Thời gian hoàn thiện hồ sơ dành cho Bên chuyển dữ liệu ra nước ngoài là 10 ngày kế từ ngày yêu cầu.',None,'paraphrase'),
(23,'Cơ quan chuyên trách bảo vệ dữ liệu cá nhân là đơn vị nào thuộc Bộ Công an?','Cục An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao.','Cơ quan chuyên trách bảo vệ dữ liệu cá nhân là Cục An ninh mạng và phòng, chống tội phạm sử dụng công nghệ cao - Bộ Công an',None,'direct'),
(24,'Kinh phí bảo vệ dữ liệu cá nhân của doanh nghiệp do ai bố trí và thực hiện?','Do tổ chức, doanh nghiệp tự bố trí và thực hiện.','Kinh phí bảo vệ dữ liệu cá nhân của tô chức, doanh nghiệp do các tổ chức, doanh nghiệp tự bố trí và thực hiện theo quy định.',None,'paraphrase'),
(26,'Trong Chương III, bên kiểm soát có trách nhiệm ghi lại và lưu trữ loại nhật ký nào?','Nhật ký hệ thống quá trình xử lý dữ liệu cá nhân.','Ghi lại và lưu trữ nhật ký hệ thống quá trình xử lý dữ liệu cá nhân.','III','direct'),
(27,'Trong Chương IV, quy định miễn trừ nhân sự bảo vệ dữ liệu áp dụng bao lâu, và loại doanh nghiệp nào không được áp dụng?','02 năm đầu kể từ thành lập đối với các nhóm được nêu; không áp dụng cho doanh nghiệp trực tiếp kinh doanh hoạt động xử lý dữ liệu cá nhân.',None,'IV','exception'),
(28,'Bộ trưởng nào được giao đôn đốc, kiểm tra và hướng dẫn thực hiện nghị định?','Bộ trưởng Bộ Công an.','Bộ trưởng Bộ Công an đôn đốc, kiểm tra, hướng dẫn việc thực hiện Nghị định này.',None,'direct'),
]
qs=[]
for i,(page,question,answer,quote,chapter,kind) in enumerate(items,1):
    p=pages[page-1]
    if quote is None:
        at=p['text'].index('2. Các đoanh nghiệp siêu nhỏ')
        quote=p['text'][at:]
    if quote not in p['text']:raise ValueError(f'Missing evidence vi{i:02}: {quote}')
    qs.append(dict(id=f'vi{i:02}',split='external_test',question=question,expected_answer=answer,
        gold_source_id='nd13',gold_page=page,evidence_quote=quote,filter={'chapter':chapter} if chapter else {},
        alternatives=[],kind=kind,evidence_review='Codex AI read source scan and OCR; student confirmation pending',
        note='Question refers only to provided 2023 source snapshot; evidence retains OCR spelling.'))
(ROOT/'benchmark/vietnamese_questions.json').write_text(json.dumps(qs,ensure_ascii=False,indent=2)+'\n')
manifest=json.loads((out/'manifest.json').read_text())
manifest.update(local_path='data/vietnamese/13nd.signed.pdf',
    note='39 scanned pages OCR-processed; 28 regulation pages, appendix listing and forms counted separately. Source evidence/chapter transitions reviewed by Codex AI; student confirmation pending.',
    official_source='https://chinhphu.vn/default.aspx?docid=207759&pageid=27160',
    source_version='Signed source 2023; user file SHA-256 recorded; no claim about current legal validity',
    page_groups={'regulation_text':[1,28],'appendix_listing':[29,29],'blank_form_templates':[30,39]},
    count_rule='39 physical scanned pages indexed as provided; only 28 pages carry regulation text. Appendix listing/templates are not claimed as 11 extra full content pages for the lab minimum.',
    chapter_boundaries='AI visual review: I on p1, II p7, III within p24, IV within p27, appendix p29; segment chunks at chapter boundaries and preserve physical-page offsets.',
    ocr_quality='No global spelling correction. Gold passages visually reviewed; OCR variants such as đữ/thê/đông/ kế retained and disclosed.',
    ocr_text_sha256=hashlib.sha256((out/'pages.json').read_bytes()).hexdigest())
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
protocol=dict(status='new document external source test; frozen before first retrieval; no tuning or selection on this dataset',
    corpus='data/vietnamese/pages.json',questions='benchmark/vietnamese_questions.json',language='vi',
    embedding='BAAI/bge-small-en-v1.5 unchanged from English baseline',reranker='Xenova/ms-marco-MiniLM-L-6-v2 unchanged',
    strategies=dict(A='fixed 500 overlap50',B='paragraph max1000',C='B plus input chapter filter',D='B plus dense20 BM25_20 RRF60 rerank20 top3 and input chapter filter'),
    segmentation='physical pages, additionally split chapter transitions for trustworthy filters; chunk offsets remain relative to original normalized OCR page',
    collection_path='.qdrant_vi',top_k=3,metric='exact cosine for dense; unchanged strict single-chunk source/page/full-quote Hit metrics',
    test_count=20,dev_count=0,filter_questions=['vi01','vi06','vi18','vi19'],
    caveats=['New document and language; one scanned source only, authored AI labels pending student review.',
             'English embedding/reranker, unchanged English lexical stopwords; intentional out-of-domain test, not optimized Vietnamese retrieval.',
             'OCR errors can affect ranking; benchmark is evaluated against frozen OCR text, not a perfect human transcription.',
             'All 20 external-test queries are frozen; no parameter search after results.'])
(ROOT/'benchmark/vietnamese_protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+'\n')
print(f'Frozen {len(qs)} Vietnamese external-test questions; {sum(bool(q["filter"]) for q in qs)} filters')
