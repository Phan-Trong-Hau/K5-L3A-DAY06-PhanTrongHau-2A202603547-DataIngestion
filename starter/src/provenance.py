"""Portable source paths and verification of submission metadata packaging."""
import hashlib
import json
from pathlib import Path

QUESTION_KEYS=['id','split','question','expected_answer','gold_source_id','gold_page','evidence_quote','filter','alternatives','kind']
TRACE_KEYS=QUESTION_KEYS+['strategy','hit1','hit3','hits','candidates','applied_filter','elapsed_seconds','retrieval_seconds','shared_query_embedding_seconds','post_hoc_original_test']
NON_EXPERIMENTAL={'note','annotation','caveats','limitations','evidence_review','reviewer','student_verified','review_status','method','interpretation','user_instruction','review'}


def local_source_path(root: Path, manifest: dict) -> Path:
    value=manifest.get('local_path') or manifest.get('source_path_or_url','')
    if '://' in value:raise ValueError('Manifest needs local_path for bundled source')
    path=Path(value)
    return path if path.is_absolute() else root/path


def scientific_digest(path: str, data: bytes):
    """Bind questions/gold/filter and all retrieved texts/ranks/scores, not workflow notes."""
    if path.endswith('traces.jsonl'):
        value=[{k:q[k] for k in TRACE_KEYS if k in q} for q in map(json.loads,data.decode().splitlines())]
    else:
        value=json.loads(data)
        if isinstance(value,list) and value and isinstance(value[0],dict) and 'evidence_quote' in value[0]:
            value=[{k:q[k] for k in QUESTION_KEYS if k in q} for q in value]
        elif path=='data/sources.json':value={'primary_source':value['primary_source'],'sources':value['sources']}
        elif path=='data/multidoc/manifest.json':
            value={'source_count':value['source_count'],'ids':[s['source_id'] for s in value['sources']],'reused':[s['source_id'] for s in value['reused_sources']],'normalized_sha256':value['normalized_sha256']}
        elif isinstance(value,dict) and 'source_id' in value and 'sha256' in value:
            value={k:value[k] for k in ['source_id','sha256','physical_pages','pages','ocr_text_sha256','normalized_sha256'] if k in value}
        else:
            def strip(x):
                if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k not in NON_EXPERIMENTAL}
                if isinstance(x,list):return [strip(v) for v in x]
                if x in ('data/multidoc/pages.json','starter.src.corpus.load_multidoc_pages'):return 'composed_five_source_pages'
                return x
            value=strip(value)
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def verify_recorded_input(root: Path, path: str, digest: str):
    current=root/path
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest()==digest:return True
    registry=json.loads((root/'results/provenance.json').read_text())
    if path in registry['virtual_inputs']:
        from .corpus import composed_bytes
        if hashlib.sha256(composed_bytes(root)).hexdigest()==digest==registry['virtual_inputs'][path]['sha256']:return True
    record=registry['files'].get(path)
    if record and digest in record['previous_sha256'] and current.is_file():
        if hashlib.sha256(current.read_bytes()).hexdigest()==record['current_sha256'] and scientific_digest(path,current.read_bytes())==record['scientific_sha256']:return True
    retired=registry['retired_non_experimental'].get(path)
    if retired and retired['sha256']==digest and not current.exists():return True
    raise ValueError(f'Recorded input mismatch: {path}')
