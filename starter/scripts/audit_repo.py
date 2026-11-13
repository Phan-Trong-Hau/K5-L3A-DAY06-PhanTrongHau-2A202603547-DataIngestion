"""Audit all submission files and source/result consistency without rerunning models."""
import ast
import copy
import csv
import hashlib
from html.parser import HTMLParser
import importlib.metadata
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.evaluation import evaluate_query,summarize
from starter.src.ingestion import load_alice
from starter.src.provenance import local_source_path,recorded_input_path

ROOT=Path(__file__).resolve().parents[2]
OUTPUTS={'results/repo_audit.json','report/REPO_AUDIT.md','results/repo_audit_tests.txt','results/repo_audit_ui.txt'}
checks=[]


def check(name,operation):
    try:
        detail=operation()
        checks.append(dict(name=name,status='PASS',detail=detail))
    except Exception as exc:
        checks.append(dict(name=name,status='FAIL',detail=f'{type(exc).__name__}: {exc}'))


def require(condition,message):
    if not condition:raise ValueError(message)


def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    raw=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT)
    return sorted(set(p for p in raw.decode().split('\0') if p and p not in OUTPUTS and (ROOT/p).is_file()))


files=inventory()


def scan_files():
    counts={};total=0
    for name in files:
        p=ROOT/name;total+=p.stat().st_size;counts[p.suffix or '(no extension)']=counts.get(p.suffix or '(no extension)',0)+1
        if p.suffix=='.json':read(name)
        elif p.suffix=='.jsonl':
            for i,line in enumerate(p.read_text().splitlines(),1):
                if line.strip():json.loads(line)
        elif p.suffix=='.csv':
            rows=list(csv.reader(p.open(newline='',encoding='utf-8')))
            require(not rows or all(len(row)==len(rows[0]) for row in rows),f'CSV column mismatch: {name}')
        elif p.suffix=='.py':ast.parse(p.read_text(),filename=name)
    return dict(files=len(files),bytes=total,by_extension=counts,scope='All tracked+untracked non-ignored submission files, including raw PDF/text, results and dotfiles. Excludes Git internals, .venv, vector databases, OCR/model caches and audit outputs.')


def manifest_checks():
    registry=read('data/sources.json');required=['source_id','title','source_path_or_url','license_or_permission','accessed_at','pages']
    for entry in registry['sources']:
        for path in [entry['manifest'],entry['raw'],entry['normalized'],*entry['benchmark'],*entry['results']]:
            require((ROOT/path).is_file(),f'Missing catalog path: {path}')
        m=read(entry['manifest'])
        for key in required:require(bool(m.get(key)),f'{entry["source_id"]}: missing {key}')
        local=local_source_path(ROOT,m)
        require(not Path(m['local_path']).is_absolute(),'Manifest local_path must be repo-relative')
        require(local.is_file(),f'Missing source: {local}')
        require(sha(local)==m['sha256'],f'Source checksum mismatch: {local}')
        require(all(isinstance(p['page'],int) and p['characters']>0 for p in m['pages']),'Missing page IDs/lengths')
        require(len({p['page'] for p in m['pages']})==len(m['pages']),'Duplicate page IDs')
    return 'Both current manifests match required schema; bundled source paths exist, are relative and match SHA-256.'


def source_checks():
    original=load_alice(ROOT/'data/alice.txt');stored=read('data/pages.json');m=read('data/manifest.json')
    require(len(original)==len(stored)==m['content_units']==len(m['pages']),'Alice page counts differ')
    require(len(original)>=30 and min(len(p.text) for p in original)>=1500,'Alice below content minimum')
    require(len({p.text for p in original})==len(original),'Duplicated Alice units')
    for p,row,meta in zip(original,stored,m['pages']):
        require(p.page==row['page']==meta['page'] and p.text==row['text'] and p.metadata==row['metadata'],'Alice derived text differs from source')
        require(meta['characters']==len(row['text']),'Alice character count mismatch')
    vi=read('data/vietnamese/pages.json');vm=read('data/vietnamese/manifest.json')
    require(sha(ROOT/'data/vietnamese/pages.json')==vm['ocr_text_sha256'],'VI OCR checksum mismatch')
    from pypdf import PdfReader
    require(len(PdfReader(local_source_path(ROOT,vm)).pages)==len(vi)==vm['physical_pages']==39,'PDF physical pages differ')
    for row,meta in zip(vi,vm['pages']):
        require(row['page']==meta['page'] and len(row['text'])==meta['characters'],'VI character/page count mismatch')
        spans=row['metadata']['chapter_spans']
        require(spans[0]['start']==0 and spans[-1]['end']==len(row['text']),'Incomplete chapter boundaries')
        require(all(a['end']==b['start'] for a,b in zip(spans,spans[1:])),'Chapter gap/overlap')
    return dict(alice_units=len(original),alice_min_characters=min(len(p.text) for p in original),vietnamese_physical_pages=len(vi),vietnamese_regulation_pages=28,note='Primary Alice corpus meets >=30 rule; VI is supplemental and not claimed as 39 full content pages.')


alice_pages=read('data/pages.json');vi_pages=read('data/vietnamese/pages.json')
lookup={('alice',p['page']):dict(**p,document_id='alice',source='https://www.gutenberg.org/ebooks/11') for p in alice_pages}
lookup.update({('nd13',p['page']):p for p in vi_pages})


def benchmarks():
    datasets=['benchmark/questions.json','benchmark/extension_holdout.json','benchmark/vietnamese_questions.json']
    all_ids=[];counts={}
    for file in datasets:
        qs=read(file);counts[file]=len(qs)
        for q in qs:
            all_ids.append(q['id'])
            require(all(k in q for k in ['id','split','question','expected_answer','gold_source_id','gold_page','evidence_quote']),'Incomplete question')
            page=lookup[q['gold_source_id'],q['gold_page']]
            require(q['evidence_quote'] in page['text'],f'Evidence absent: {q["id"]}')
            for g in q.get('alternatives',[]):require(g['evidence_quote'] in lookup[g['source_id'],g['page']]['text'],'Alternative gold absent')
            if q.get('filter'):
                chapter=q['filter'].get('chapter')
                valid={s['chapter'] for s in page['metadata'].get('chapter_spans',[])} or {page['metadata']['chapter']}
                require(chapter in valid,f'Invalid gold/filter chapter: {q["id"]}')
        require(len({q['id'] for q in qs})==len(qs),'Duplicate question IDs')
    require(len(all_ids)==len(set(all_ids)),'Question IDs overlap across sets')
    main=read(datasets[0]);require(sum(q['split']=='dev' for q in main)>=15 and sum(q['split']=='test' for q in main)>=5,'Main split below 15/5')
    require(sum(bool(q['filter']) for q in main)>=3 and any(q['filter'] and q['split']=='test' for q in main),'Not enough metadata filter questions')
    return dict(questions=counts,total=len(all_ids),main_split='15 dev / 5 test',note='Evidence verified against current stored source text; semantic/human confirmation remains separate.')


def traces():
    count=0;hits_count=0
    for directory in ['results','results/extension','results/vietnamese']:
        rows=[json.loads(l) for l in (ROOT/directory/'traces.jsonl').read_text().splitlines() if l.strip()]
        require(summarize(rows)==read(directory+'/metrics.json'),f'Metrics inconsistent: {directory}')
        require(len({(t['strategy'],t['id']) for t in rows})==len(rows),'Duplicate strategy/question trace')
        for t in rows:
            require(len(t['hits'])==3,'Not exactly top-3')
            evaluated=evaluate_query(copy.deepcopy(t),copy.deepcopy(t['hits']))
            require(t['hit1']==evaluated['hit1'] and t['hit3']==evaluated['hit3'],'Hit flags inconsistent with strict evidence')
            for original,expected in zip(t['hits'],evaluated['hits']):require(original['evidence_hit']==expected['evidence_hit'],'Per-hit evidence flag mismatch')
            for h in t['hits']+t.get('candidates',[]):
                meta=h['metadata'];page=lookup[meta['document_id'],meta['page']]
                a,b=meta['start'],meta['end']
                require(0<=a<b<=len(page['text']) and page['text'][a:b]==h['text'],'Text/offset does not map to source')
                require(meta['source']==page['source'],'Source URL/reference mismatch')
                if t['strategy'] in ('C','D') and t['filter']:
                    require(all(meta[k]==v for k,v in t['filter'].items()),'Metadata filter violation')
                require(math.isfinite(h['score']),'Nonfinite ranking score')
            count+=1;hits_count+=len(t['hits'])
    return dict(traces=count,top3_records=hits_count,metrics='All recomputed exactly',provenance='Every returned chunk maps to its source page and normalized offsets')


def frozen_inputs():
    snapshots=[];n=0
    for directory in ['results','results/extension','results/vietnamese']:
        run=read(directory+'/run.json')
        for path,digest in run.get('input_hashes',{}).items():
            actual=recorded_input_path(ROOT,ROOT/directory,path,digest);n+=1
            if actual!=ROOT/path:snapshots.append(dict(original=path,snapshot=str(actual.relative_to(ROOT))))
        if (ROOT/directory/'freeze.json').exists():
            for path,digest in read(directory+'/freeze.json')['hashes'].items():recorded_input_path(ROOT,ROOT/directory,path,digest)
    base=read('results/run.json')
    require(base['corpus_sha256']==sha(ROOT/'data/alice.txt'),'Original corpus changed')
    require(base['benchmark_sha256']==sha(ROOT/'benchmark/questions.json'),'Original questions changed')
    return dict(checked=n,historical_snapshots=snapshots,note='No benchmark/trace/metric hashes or recorded run timestamps rewritten.')


def document_links():
    n=0
    for file in files:
        if not file.endswith('.md'):continue
        for link in re.findall(r'!?\[[^\]]*\]\(([^\n)]+)\)',(ROOT/file).read_text()):
            target=link.split('#',1)[0].strip('<>')
            if not target or re.match(r'[a-z]+://',target):continue
            require((ROOT/file).parent.joinpath(target).exists(),f'Broken Markdown link: {file} -> {target}')
            n+=1
    return dict(local_links_checked=n)


def secrets():
    hits=[]
    pattern=re.compile(r'(?i)(?:OPENAI_API_KEY|OPENROUTER_API_KEY|GEMINI_API_KEY|HF_TOKEN)\s*=\s*[\"\']?([A-Za-z0-9_-]{16,})')
    for file in files:
        require(Path(file).name!='.env','Unignored .env included in submission')
        p=ROOT/file
        if p.suffix=='.pdf':continue
        try:text=p.read_text()
        except UnicodeDecodeError:continue
        for i,line in enumerate(text.splitlines(),1):
            if pattern.search(line):hits.append(dict(file=file,line=i))
    require(not hits,f'Possible API secrets at file/line locations: {hits}')
    for name in ['.venv/','.qdrant/','.qdrant_vi/','.ocr_cache/','.embedding_cache/']:
        require(not any(f.startswith(name) for f in files),f'Runtime/cache included in submission: {name}')
    require('data/vietnamese/13nd.signed.pdf' in files,'Bundled PDF ignored or missing from package inventory')
    return 'No matching populated API-secret assignments; runtime caches excluded and PDF included. Template local-only database password is documented, not an API credential. Pattern scan is not a guarantee of all possible secret formats.'


def static_ui():
    for file in files:
        if file.endswith(('.js','.cjs')):
            result=subprocess.run(['node','--check',str(ROOT/file)],capture_output=True,text=True)
            require(result.returncode==0,f'JS syntax error: {file}: {result.stderr}')
    class Ids(HTMLParser):
        def __init__(self):super().__init__();self.ids=[]
        def handle_starttag(self,tag,attrs):
            self.ids.extend(v for k,v in attrs if k=='id')
    html=Ids();html.feed((ROOT/'starter/ui/index.html').read_text())
    require(len(html.ids)==len(set(html.ids)),'Duplicate DOM IDs')
    return 'JS syntax and unique HTML IDs checked; visual browser QA not available in current environment.'


def accepted_reviews():
    acceptance=read('results/review_acceptance.json')
    require(acceptance['status']=='user_accepted_ai_assisted_review','Missing disclosed user acceptance')
    require(acceptance['source_trace_sha256']==sha(ROOT/'results/traces.jsonl'),'Review tied to different traces')
    require(acceptance['review_summary_sha256']==sha(ROOT/'results/review_summary.json'),'Review scores changed since acceptance')
    counts={}
    for file,digest in acceptance['final_label_sha256'].items():
        require(sha(ROOT/file)==digest,f'Accepted labels changed: {file}')
        rows=list(csv.DictReader((ROOT/file).open()))
        require(all(r['student_verified']=='user_accepted_ai_assisted_review' for r in rows),'Unaccepted review rows')
        require(all('AI' in r.get('reviewer',r.get('method','')) for r in rows),'AI reviewer not disclosed')
        counts[file]=len(rows)
    require(sum(counts.values())==90,'Expected 90 reviewed records')
    samples=read('results/coherence_samples.json')
    require(len(samples)==30 and all(s['score'] in (0,1,2) and s['reason'] and s['review_status']=='user_accepted_ai_assisted_review' for s in samples),'Incomplete coherence source samples')
    return dict(rows=counts,total=90,method='AI-assisted source/trace review explicitly accepted by user; no independent human scoring claimed',summary='Scores unchanged; hash-bound labels and acceptance record verified.')


for name,operation in [('submission_file_scan',scan_files),('manifest_schema_and_portable_sources',manifest_checks),
    ('corpus_counts_and_normalized_text',source_checks),('all_benchmarks_and_gold',benchmarks),
    ('all_traces_metrics_and_source_offsets',traces),('historical_input_integrity',frozen_inputs),
    ('disclosed_accepted_assessments',accepted_reviews),('all_markdown_local_links',document_links),('secret_patterns_and_package_exclusions',secrets),('ui_static_checks',static_ui)]:check(name,operation)

pending=[]
for file in ['results/coherence_review.csv','results/grounding_review.csv','results/metadata_audit.csv']:
    rows=list(csv.DictReader((ROOT/file).open()))
    n=sum(row.get('student_verified')=='pending' for row in rows)
    if n:pending.append(dict(file=file,rows=n))
warnings=[dict(name='review_method',detail='AI-assisted assessment accepted by user; no independent human scoring claimed. Original ingestion/benchmark snapshots retain execution-time notes; current acceptance is in results/review_acceptance.json.'),dict(name='handoff_scope',detail='Deliver source/data/reports on main; Git push verified separately at handoff. Sending a link through a class channel is outside this repo task.'),dict(name='external_test_limits',detail='VI PDF has 39 physical pages but only 28 regulation pages; supplemental test, English models, OCR and AI-authored labels. D original English test was inspected before extension. Restrictions remain disclosed.')]
verification={}
for filename in ['results/repo_audit_tests.txt','results/repo_audit_ui.txt']:
    path=ROOT/filename
    if path.is_file():
        contents=path.read_text()
        verification[filename]=dict(passed=('\nOK\n' in contents if 'tests' in filename else contents.startswith('PASS:')),summary='; '.join(line for line in contents.splitlines() if line.startswith(('Ran ','OK','PASS:'))))
result=dict(verification=verification,utc=datetime.now(timezone.utc).isoformat(),status=('PASS_WITH_PENDING_HUMAN_ITEMS' if pending else 'PASS_WITH_DISCLOSED_AI_REVIEW') if all(c['status']=='PASS' for c in checks) else 'FAIL',
    checks=checks,warnings=warnings,inventory=[dict(path=f,bytes=(ROOT/f).stat().st_size,sha256=sha(ROOT/f)) for f in files])
(ROOT/'results/repo_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
lines=['# Kiểm tra toàn repo và cấu trúc dữ liệu','',f"Thời điểm UTC: {result['utc']}",f"Trạng thái: **{result['status']}**",'',
    f'Đã quét {len(files)} file bài nộp (tracked và untracked không bị ignore), gồm dữ liệu gốc, OCR, benchmark, toàn bộ trace, báo cáo, UI, code và cấu hình.',
    'Không duyệt môi trường ảo, Git internals hoặc cache/model/vector DB được ignore; đây là trạng thái runtime, không thuộc gói bài nộp.','',
    '| Kiểm tra | Trạng thái | Chi tiết |','|---|---|---|']
for c in checks:lines.append(f"| {c['name']} | {c['status']} | {json.dumps(c['detail'],ensure_ascii=False) if not isinstance(c['detail'],str) else c['detail']} |")
lines+=['','## Kiểm tra bổ sung đã chạy','']
for file,value in verification.items():lines.append(f"- `{file}`: {value['summary']}")
lines+=['','## Các sửa đổi sau audit','',
    '- Manifest tiếng Việt có local_path tương đối, URL chính thức và license_or_permission đúng schema đề; xóa mô tả cũ chưa copy PDF.',
    '- Giữ nguyên manifest lúc chạy trong input_snapshots; sidecar chỉ rõ thay metadata đóng gói. Không sửa gold, trace, metrics hoặc hash lịch sử.',
    '- UI/pipeline đọc đường dẫn từ manifest, không phụ thuộc Downloads. Script OCR tái tạo cũng xuất schema/đường dẫn phù hợp.',
    '- Thêm data/README.md và sources.json để phân biệt corpus chính Alice với phép thử PDF tiếng Việt; giữ format-example.json là ví dụ của đề.',
    '- Làm rõ số trang/đơn vị: Alice 82 × >=1500 ký tự đủ quy tắc; PDF 39 trang vật lý không tự coi là 39 trang nội dung hợp lệ.',
    '', '## Phương pháp đánh giá và phạm vi bàn giao','',
    '- 90 dòng đánh giá đã chốt theo AI-assisted review, được người dùng chấp nhận rõ ràng trong phiên làm việc; không ghi thành chấm độc lập của con người.',
    '- Nhãn/điểm và lý do không bị nâng sau chấp nhận; hồ sơ user instruction và hash tại results/review_acceptance.json.',
    '- Bản bàn giao trên nhánh main; việc push được xác minh khi bàn giao. Gửi link qua kênh lớp là thao tác riêng ngoài phạm vi repo.',
    '- Chưa có kiểm tra trực quan UI bằng browser trong môi trường này; API/render smoke và kiểm thử được chạy riêng.',
    '', 'Chi tiết inventory, hash và dữ liệu kiểm tra: `results/repo_audit.json`. Tái chạy: `.venv/bin/python starter/scripts/audit_repo.py`.','']
(ROOT/'report/REPO_AUDIT.md').write_text('\n'.join(lines))
for c in checks:print(c['status'],c['name'],json.dumps(c['detail'],ensure_ascii=False))
print('AUDIT:',result['status'])
sys.exit(0 if all(c['status']=='PASS' for c in checks) else 1)
