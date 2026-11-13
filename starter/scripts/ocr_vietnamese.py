"""Read-only OCR of a scanned PDF; preserves the signed original unchanged."""
import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.ingestion import normalize_text
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('pdf',type=Path,nargs='?',default=ROOT/'data/vietnamese/13nd.signed.pdf')
    args=parser.parse_args()
    source=args.pdf.resolve();out=ROOT/'data/vietnamese';out.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'.ocr_cache';cache.mkdir(exist_ok=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    bundled=out/'13nd.signed.pdf'
    if bundled.exists() and hashlib.sha256(bundled.read_bytes()).hexdigest()!=digest:
        raise ValueError('Bundled PDF has different contents; use a new corpus/version instead of replacing it silently')
    if source!=bundled.resolve():shutil.copy2(source,bundled)
    cache=cache/digest[:16];cache.mkdir(exist_ok=True)
    count=len(PdfReader(source).pages)
    def ocr(page):
        base=cache/f'page-{page:02}'
        if not base.with_suffix('.txt').exists():
            subprocess.run(['pdftoppm','-f',str(page),'-l',str(page),'-r','200','-png','-singlefile',str(source),str(base)],check=True,capture_output=True)
            subprocess.run(['tesseract',str(base.with_suffix('.png')),str(base),'-l','vie','--psm','3'],check=True,capture_output=True,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
        raw=base.with_suffix('.txt').read_text()
        # Keep OCR paragraph structure, remove standalone printed page numbers.
        lines=raw.splitlines()
        if lines and lines[0].strip().isdigit():lines=lines[1:]
        text=normalize_text('\n'.join(lines))
        print(f'OCR {page}/{count}: {len(text)} chars',flush=True)
        return dict(document_id='nd13',source='user-provided:13nd.signed.pdf',page=page,text=text,metadata={'language':'vi'})
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pages=list(pool.map(ocr,range(1,count+1)))
    (out/'pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2)+'\n')
    manifest=dict(source_id='nd13',title='Nghị định 13/2023/NĐ-CP — Bảo vệ dữ liệu cá nhân (bản ký 2023)',
        source_path_or_url='https://chinhphu.vn/default.aspx?docid=207759&pageid=27160',
        local_path='data/vietnamese/13nd.signed.pdf',original_path_at_ingestion=str(source),
        license_or_permission='Official regulation supplied by the user for this lab; user authorized storing the unchanged PDF in the repository.',
        accessed_at=datetime.now(timezone.utc).isoformat(),sha256=digest,physical_pages=count,
        ocr_engine=subprocess.check_output(['tesseract','--version'],text=True).splitlines()[0],
        ocr_language='vie',render_dpi=200,psm=3,extracted_text_pages=0,
        note='All pages scanned; derived OCR text may contain errors. Tests refer to this 2023 snapshot, not current legal advice. Corpus size/content-page assessment pending visual review.',
        pages=[dict(page=p['page'],characters=len(p['text'])) for p in pages])
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
