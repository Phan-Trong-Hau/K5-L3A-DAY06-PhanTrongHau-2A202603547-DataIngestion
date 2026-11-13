"""Materialize disclosed AI-reviewed labels and objective metadata audit.
Labels below were assigned after reading actual sampled chunks/top-3 traces;
they are not inferred from exact-match retrieval metrics. The user has accepted the disclosed AI-assisted assessment; see review_acceptance.json.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.ingestion import load_alice
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'results'
if hashlib.sha256((out/'traces.jsonl').read_bytes()).hexdigest() != '597d7c1fe07cc6db3203303eca324716b6732485d12fb45c175a7569144dc698':
    raise ValueError('Traces changed: re-review content; stored AI labels apply only to the original run')

acceptance_path=out/'review_acceptance.json'
acceptance=json.loads(acceptance_path.read_text()) if acceptance_path.exists() else {}
review_status='user_accepted_ai_assisted_review' if acceptance.get('status')=='user_accepted_ai_assisted_review' and acceptance.get('source_trace_sha256')==hashlib.sha256((out/'traces.jsonl').read_bytes()).hexdigest() else 'pending'

def write(name, rows):
    with (out/name).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader();writer.writerows(rows)

reasons_a=[
'Bắt đầu giữa từ daisy-chain, kết thúc giữa watch; vẫn hiểu Alice gặp Rabbit nhưng mất mạch.',
'Đầu cắt mất chủ ngữ jar, cuối cắt lời dẫn; nội dung lọ marmalade chỉ còn một phần ngữ cảnh.',
'Đầu nối câu hỏi từ chunk trước, cuối cắt hội thoại với Dinah; hiểu một phần.',
'Đầu mất phần giới thiệu bàn, cuối cắt câu mở cửa; đoạn chìa khóa vẫn đọc được.',
'Đầu cắt lời dẫn Drink me, cuối cắt điều kiện cảnh báo dùng dao; thiếu trọn lập luận.',
'Cả hai chunk bao phủ vị trí đều cắt giữa câu; lời tự khuyên và lý do chơi hai vai không trọn.',
'Đầu mất đối tượng đôi chân, cuối cắt địa chỉ; khó hiểu nếu đứng riêng.',
'Đầu mất phần Alice cầm quạt, cuối cắt mô tả Ada; chỉ giữ một phần tự vấn danh tính.',
'Đầu cắt bối cảnh Mabel, cuối cắt lời cô đơn; vẫn hiểu điều kiện nhưng thiếu mở/kết.',
'Đầu là đuôi câu trước, cuối cắt hồi tưởng bãi biển; thiếu kết luận về hồ nước mắt.'
]
reasons_b=[
'Giữ đoạn Rabbit lấy đồng hồ và Alice theo xuống hang, có chủ thể và diễn biến.',
'Đoạn giếng, lọ rỗng và phản ứng Alice trọn vẹn, không cắt câu.',
'Độc thoại giải thích Dinah là mèo và kết thúc cú rơi, có đủ diễn biến.',
'Giới thiệu bàn, chìa khóa và cửa nhỏ trong một đoạn hoàn chỉnh.',
'Giữ điều kiện kiểm tra poison, lý do và hành động uống trong cùng chunk.',
'Lời tự khuyên và giải thích trò đóng hai người trọn ý.',
'Alice lớn lên, đôi chân xa dần và địa chỉ quà tặng cùng một chunk.',
'Có chủ thể Alice, quạt, bối cảnh và tự vấn danh tính đầy đủ.',
'Giữ bài thơ và phản ứng nhưng thiếu bài thơ đúng để hiểu vì sao Alice nhận mình là Mabel.',
'Giữ diễn biến rơi vào nước, xác nhận hồ nước mắt và phản ứng của Alice.'
]
samples=json.loads((out/'coherence_samples.json').read_text())
rows=[]
for s in samples:
    page=s['page'];paragraph=s['strategy']!='A'
    rows.append(dict(strategy=s['strategy'],page=page,offset=s['offset'],chunk_ids=';'.join(c['chunk_id'] for c in s['chunks']),
        score=(1 if page==9 else 2) if paragraph else 1,
        reason=(reasons_b if paragraph else reasons_a)[page-1],reviewer='Codex AI-assisted content review',student_verified=review_status))
write('coherence_review.csv',rows)
for sample,row in zip(samples,rows):
    sample.update(score=row['score'],reason=row['reason'],reviewer=row['reviewer'],review_status=review_status)
(out/'coherence_samples.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2)+'\n')
traces=[json.loads(l) for l in (out/'traces.jsonl').read_text().splitlines()]
grounding={
 'q16':(2,'Top-1 nêu đúng Duchess’s cook cầm pepper-box, có source/unit để đối chiếu.'),
 'q17':(2,'Top-1 A có câu hỏi về thành phần tarts và câu cook trả lời Pepper, mostly.'),
 'q18':(2,'Top-1 giữ Rule Forty-two cùng điều kiện hơn một mile high.'),
 'q19':(2,'Top-1 giữ người nói Queen và thứ tự sentence trước verdict.'),
 'q20':(2,'Top-1 giữ bài vè gán hành vi lấy tarts cho Knave of Hearts.')}
ground_rows=[];metadata_rows=[]
pages={p.page:p for p in load_alice(ROOT/'data/alice.txt')}
for t in traces:
    if t['split']!='test':continue
    score,reason=grounding[t['id']]
    if t['id']=='q17' and t['strategy']!='A':
        score,reason=0,'Đã đọc cả top-3: nói mustard, suy diễn tarts và bài vè trộm bánh; không có phát biểu của cook về pepper.'
    ground_rows.append(dict(strategy=t['strategy'],question_id=t['id'],score=score,reason=reason,
        reviewer='Codex AI-assisted content review',student_verified=review_status))
    for rank,h in enumerate(t['hits'],1):
        m=h['metadata'];p=pages[m['page']]
        good=m['source']==p.source and m['document_id']==p.document_id and m['chapter']==p.metadata['chapter'] and p.text[m['start']:m['end']]==h['text']
        follows=all(m[k]==v for k,v in t['filter'].items()) if t['filter'] else ''
        metadata_rows.append(dict(strategy=t['strategy'],question_id=t['id'],rank=rank,chunk_id=h['chunk_id'],page=m['page'],chapter=m['chapter'],
            complete_and_correct=good,filter_compliant=follows,
            method='Source/offset validation plus AI review of displayed test traces; AI-assisted assessment; user acceptance recorded separately in review_acceptance.json',student_verified=review_status))
write('grounding_review.csv',ground_rows)
write('metadata_audit.csv',metadata_rows)
summary={}
for s in 'ABC':
    co=[r['score'] for r in rows if r['strategy']==s]
    gr=[r['score'] for r in ground_rows if r['strategy']==s]
    meta=[r for r in metadata_rows if r['strategy']==s]
    filtered=[t for t in traces if t['strategy']==s and t['split']=='test' and t['filter']]
    summary[s]=dict(coherence_mean=sum(co)/len(co),coherence_n=len(co),grounding_mean=sum(gr)/len(gr),
        grounding_counts={str(i):gr.count(i) for i in range(3)},metadata_correct=sum(r['complete_and_correct'] for r in meta),metadata_n=len(meta),
        filter_queries_compliant=sum(all(all(h['metadata'][k]==v for k,v in t['filter'].items()) for h in t['hits']) for t in filtered),filter_queries_n=len(filtered))
(out/'review_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
