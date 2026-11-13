"""Extract new source snapshots; OCR scanned PDFs without altering signed originals."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pypdf import PdfReader
from starter.src.ingestion import normalize_text
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'data/multidoc'
SOURCES={
 'nd69':dict(title='Nghị định 69/2024/NĐ-CP — Định danh và xác thực điện tử (snapshot 2024)',url='https://vanban.chinhphu.vn/?pageid=27160&docid=210491',download='https://datafiles.chinhphu.vn/cpp/files/vbpq/2024/6/69-cp.signed.pdf',year=2024),
 'nd42':dict(title='Nghị định 42/2022/NĐ-CP — Thông tin và dịch vụ công trực tuyến (snapshot 2022)',url='https://vanban.chinhphu.vn/?pageid=27160&docid=206001',download='https://datafiles.chinhphu.vn/cpp/files/vbpq/2022/06/42nd.signed.pdf',year=2022)}


def main():
 manifests=[];all_pages=[]
 for source_id,info in SOURCES.items():
  path=OUT/'raw'/f'{source_id}.pdf';digest=hashlib.sha256(path.read_bytes()).hexdigest()
  reader=PdfReader(path);cache=ROOT/'.ocr_cache'/digest[:16];cache.mkdir(parents=True,exist_ok=True)
  def extract(n):
   text=reader.pages[n-1].extract_text() or ''
   engine='pypdf'
   if not text.strip():
    base=cache/f'page-{n:02}';engine='tesseract-vie-200dpi-psm3'
    if not base.with_suffix('.txt').exists():
     subprocess.run(['pdftoppm','-f',str(n),'-l',str(n),'-r','200','-png','-singlefile',str(path),str(base)],check=True,capture_output=True)
     subprocess.run(['tesseract',str(base.with_suffix('.png')),str(base),'-l','vie','--psm','3'],check=True,capture_output=True,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    text=base.with_suffix('.txt').read_text()
   lines=text.splitlines()
   if lines and lines[0].strip().isdigit():lines=lines[1:]
   text=normalize_text('\n'.join(lines))
   print(f'{source_id} page {n}/{len(reader.pages)}: {len(text)} chars',flush=True)
   return dict(document_id=source_id,source=info['url'],page=n,text=text,metadata=dict(language='vi',year=info['year'],document_type='decree',chapter='',chapter_title='Chưa trích xuất chương',chapter_spans=[dict(start=0,end=len(text),chapter='')],extraction=engine))
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:pages=list(pool.map(extract,range(1,len(reader.pages)+1)))
  (OUT/f'{source_id}_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
  manifests.append(dict(source_id=source_id,title=info['title'],source_path_or_url=info['url'],download_url=info['download'],local_path=str(path.relative_to(ROOT)),
    license_or_permission='Official legal instrument downloaded for educational retrieval benchmark; attribution retained to Cục Thông tin và Truyền thông Chính phủ / chinhphu.vn as required by source page. No separate CC license claimed.',
    accessed_at=datetime.now(timezone.utc).isoformat(),source_version=f'Original signed {info["year"]} snapshot; no claim about current legal validity',sha256=digest,physical_pages=len(pages),
    count_rule='All physical pages indexed as distractors; this supplemental experiment does not claim every physical page is a full qualifying content page.',
    normalized_path=f'data/multidoc/{source_id}_pages.json',normalized_sha256=hashlib.sha256((OUT/f'{source_id}_pages.json').read_bytes()).hexdigest(),
    pages=[dict(page=p['page'],characters=len(p['text'])) for p in pages]))
  all_pages+=pages
 # Only first two stories selected in advance. Original book/license stays intact.
 path=OUT/'raw/sherlock.txt';raw=path.read_text();body=raw.split('*** START OF THE PROJECT GUTENBERG EBOOK',1)[1].split('*** END OF THE PROJECT GUTENBERG EBOOK',1)[0]
 headings=list(re.finditer(r'^(I|II|III)\. (A SCANDAL IN BOHEMIA|THE RED-HEADED LEAGUE|A CASE OF IDENTITY)\s*$',body,re.M))
 if len(headings)!=3:raise ValueError(f'Expected first three story headings, found {len(headings)}')
 pages=[]
 for i,m in enumerate(headings[:2]):
  text=normalize_text(body[m.end():headings[i+1].start()]);blocks=[];pending=''
  for paragraph in text.split('\n\n'):
   pending+= ('\n\n' if pending else '')+paragraph
   if len(pending)>=1500:blocks.append(pending);pending=''
  if pending:
   if blocks:blocks[-1]+='\n\n'+pending
   else:blocks=[pending]
  offset=0
  for block in blocks:
   pages.append(dict(document_id='sherlock',source='https://www.gutenberg.org/ebooks/1661',page=len(pages)+1,text=block,
    metadata=dict(language='en',document_type='fiction',chapter=m[1],chapter_title=m[2],chapter_start=offset,chapter_spans=[dict(start=0,end=len(block),chapter=m[1])],extraction='text')))
   offset+=len(block)+2
 (OUT/'sherlock_pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
 manifests.append(dict(source_id='sherlock',title='The Adventures of Sherlock Holmes — stories I–II',source_path_or_url='https://www.gutenberg.org/ebooks/1661',download_url='https://www.gutenberg.org/ebooks/1661.txt.utf-8',local_path='data/multidoc/raw/sherlock.txt',
  license_or_permission='Project Gutenberg declares public domain in USA; complete original text and Gutenberg license retained.',accessed_at=datetime.now(timezone.utc).isoformat(),source_version='Gutenberg #1661 last updated 2023-10-10; first two stories selected before retrieval',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
  physical_pages=None,content_units=len(pages),count_rule='Consecutive normalized paragraphs >=1500 chars, final short remainder merged backwards, within stories I–II; remaining book excluded by predeclared scope.',
  normalized_path='data/multidoc/sherlock_pages.json',normalized_sha256=hashlib.sha256((OUT/'sherlock_pages.json').read_bytes()).hexdigest(),pages=[dict(page=p['page'],characters=len(p['text']),chapter=p['metadata']['chapter'],chapter_start=p['metadata']['chapter_start']) for p in pages]))
 all_pages+=pages
 for m in manifests:
  (OUT/f'{m["source_id"]}_manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
 for p in json.loads((ROOT/'data/pages.json').read_text()):
  all_pages.append(dict(document_id='alice',source='https://www.gutenberg.org/ebooks/11',page=p['page'],text=p['text'],metadata={**p['metadata'],'document_type':'fiction','chapter_spans':[dict(start=0,end=len(p['text']),chapter=p['metadata']['chapter'])]}))
 all_pages+=json.loads((ROOT/'data/vietnamese/pages.json').read_text())
 composed=(json.dumps(all_pages,ensure_ascii=False,indent=2)+'\n').encode()
 (OUT/'manifest.json').write_text(json.dumps(dict(sources=[dict(source_id=m['source_id'],manifest=f'data/multidoc/{m["source_id"]}_manifest.json') for m in manifests],reused_sources=[dict(source_id='alice',manifest='data/manifest.json'),dict(source_id='nd13',manifest='data/vietnamese/manifest.json')],source_count=5,normalized_sources=['data/multidoc/nd69_pages.json','data/multidoc/nd42_pages.json','data/multidoc/sherlock_pages.json','data/pages.json','data/vietnamese/pages.json'],normalized_sha256=hashlib.sha256(composed).hexdigest()),ensure_ascii=False,indent=2)+'\n')
 print('Prepared 5-document corpus:',len(all_pages),'source pages/units',flush=True)


if __name__=='__main__':main()
