"""One frozen A/B/C/D evaluation on scanned Vietnamese PDF, separate from Alice."""
import hashlib
import importlib.metadata
import json
import logging
import time
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from .models import DocumentPage
from .chunking import fixed_size,by_paragraph,make_chunk
from .embeddings import MyEmbedder
from .evaluation import evaluate_query,summarize
from .hybrid import HybridRetriever
from .store import QdrantStore
from .provenance import local_source_path

ROOT=Path(__file__).resolve().parents[2]


def build_chunks(pages,strategy):
    chunks=[]
    for row in pages:
        page=DocumentPage(row['document_id'],row['source'],row['page'],row['text'],row['metadata'])
        for span in page.metadata['chapter_spans']:
            start,end=span['start'],span['end']
            metadata={**page.metadata,'chapter':span['chapter']}
            metadata.pop('chapter_spans',None)
            segment=replace(page,text=page.text[start:end],metadata=metadata)
            local=fixed_size(segment,500,50) if strategy=='A' else by_paragraph(segment,1000)
            for chunk in local:
                original=replace(page,metadata=metadata)
                chunks.append(make_chunk(original,start+chunk.metadata['start'],start+chunk.metadata['end']))
    return chunks


def main():
    out=ROOT/'results/vietnamese';out.mkdir(exist_ok=True,parents=True)
    logging.basicConfig(filename=out/'errors.log',level=logging.WARNING,force=True)
    read=lambda path:json.loads((ROOT/path).read_text())
    pages=read('data/vietnamese/pages.json')
    manifest=read('data/vietnamese/manifest.json')
    questions=read('benchmark/vietnamese_questions.json')
    protocol=read('benchmark/vietnamese_protocol.json')
    if hashlib.sha256((ROOT/'data/vietnamese/pages.json').read_bytes()).hexdigest()!=manifest['ocr_text_sha256']:
        raise ValueError('OCR snapshot changed; benchmark must be reviewed again')
    source=local_source_path(ROOT,manifest)
    if not source.is_file():
        raise FileNotFoundError(f'Bundled PDF is missing: {source}')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['sha256']:
        raise ValueError('Signed original PDF has changed')
    for q in questions:
        if q['evidence_quote'] not in pages[q['gold_page']-1]['text']:
            raise ValueError(f"Evidence invalid: {q['id']}")
    inputs=['data/vietnamese/pages.json','data/vietnamese/manifest.json','benchmark/vietnamese_questions.json',
        'benchmark/vietnamese_protocol.json','benchmark/extension_protocol.json','results/traces.jsonl','results/metrics.json','results/extension/metrics.json','results/extension/traces.jsonl']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in inputs}
    def save(name,data):
        (out/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    save('freeze.json',dict(utc=datetime.now(timezone.utc).isoformat(),hashes=hashes,
        note='New source test; A/B/C/D frozen before first retrieval; no model or parameter selection here'))
    store=None;started=time.perf_counter()
    try:
        embedder=MyEmbedder()
        store=QdrantStore(str(ROOT/'.qdrant_vi'),embedder.dimensions)
        stats={};cache=ROOT/'.embedding_cache';cache.mkdir(exist_ok=True)
        for s in 'ABC':
            tick=time.perf_counter();chunks=build_chunks(pages,s);texts=[c.text for c in chunks]
            key=hashlib.sha256(json.dumps([embedder.model_name,importlib.metadata.version('fastembed'),texts]).encode()).hexdigest()
            path=cache/f'{key}.npy';cached=path.exists()
            vectors=np.load(path).tolist() if cached else embedder.embed_documents(texts)
            if not cached:np.save(path,vectors)
            store.upsert(s,chunks,vectors)
            n1=store.client.count(s,exact=True).count
            store.upsert(s,chunks,vectors)
            n2=store.client.count(s,exact=True).count
            if n1!=len(chunks) or n2!=n1:raise RuntimeError('Duplicate ingestion check failed')
            stats[s]=dict(chunks=len(chunks),characters=sum(map(len,texts)),min_chars=min(map(len,texts)),max_chars=max(map(len,texts)),
                ingest_seconds_including_repeat=time.perf_counter()-tick,embedding_cache_hit=cached,
                count_after_first=n1,count_after_repeat=n2,api_cost_usd=0)
            print(f'VI {s}: {len(chunks)} chunks; repeated count {n2}',flush=True)
        config=read('benchmark/extension_protocol.json')
        hybrid=HybridRetriever(store,config)
        tick=time.perf_counter();hybrid._load_reranker();load_seconds=time.perf_counter()-tick
        stats['D']=dict(chunks=stats['B']['chunks'],base_collection='B',additional_embeddings=0,reranker_load_seconds=load_seconds,api_cost_usd=0)
        traces=[]
        for q in questions:
            tick=time.perf_counter();vector=embedder.embed_query(q['question']);embed_seconds=time.perf_counter()-tick
            for s in 'ABCD':
                tick=time.perf_counter();filters=q['filter'] if s in 'CD' else None
                if s=='D':hits,candidates=hybrid.search(q['question'],vector,filters=filters or None)
                else:hits=store.search(s,vector,filters=filters or None);candidates=[]
                t=dict(strategy=s,**evaluate_query(q,hits),retrieval_seconds=time.perf_counter()-tick,
                    shared_query_embedding_seconds=embed_seconds,applied_filter=filters or {},candidates=candidates)
                traces.append(t)
                print(f"VI {s} {q['id']}: hit1={t['hit1']} hit3={t['hit3']}",flush=True)
        for path,digest in hashes.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise RuntimeError(f'Input mutated: {path}')
        (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
        save('metrics.json',summarize(traces));save('statistics.json',stats)
        save('run.json',dict(utc=datetime.now(timezone.utc).isoformat(),protocol=protocol,input_hashes=hashes,
            dimensions=embedder.dimensions,model=embedder.model_name,reranker=hybrid.model_name,
            total_seconds=time.perf_counter()-started,api_cost_usd=0,
            mean_retrieval_seconds={s:sum(t['retrieval_seconds'] for t in traces if t['strategy']==s)/len(questions) for s in 'ABCD'},
            versions={p:importlib.metadata.version(p) for p in ['fastembed','qdrant-client','onnxruntime','pypdf']},
            note='OCR and source chapter boundaries frozen before retrieval. No manual grounding/coherence scores assigned. Original Alice artifacts untouched.'))
        print(json.dumps(summarize(traces),indent=2))
    except Exception:
        logging.exception('Vietnamese evaluation failed; no fallback')
        raise
    finally:
        if store:store.close()


if __name__=='__main__':main()
