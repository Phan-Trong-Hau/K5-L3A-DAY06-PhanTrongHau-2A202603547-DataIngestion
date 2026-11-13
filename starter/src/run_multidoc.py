"""Frozen multi-document controlled ablations; select on dev before held-out documents."""
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import time
from datetime import datetime,timezone
import numpy as np
from .embeddings import MyEmbedder
from .multilingual import MultilingualEmbedder
from .hybrid import HybridRetriever
from .fusion import FusionRetriever
from .store import QdrantStore
from .run_vietnamese import build_chunks
from .evaluation import evaluate_query,summarize
from .corpus import load_multidoc_pages,composed_bytes
ROOT=Path(__file__).resolve().parents[2]
STRATEGIES=('C','D','E','F','G')


def grouped_metrics(traces,key):
    groups={}
    for t in traces:groups.setdefault(t[key],[]).append(t)
    return {name:summarize(rows) for name,rows in groups.items()}


def main():
    out=ROOT/'results/multidoc';out.mkdir(exist_ok=True,parents=True)
    logging.basicConfig(filename=out/'errors.log',level=logging.WARNING,force=True)
    def read(path):return json.loads((ROOT/path).read_text())
    def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    questions=read('benchmark/multidoc_questions.json');pages=load_multidoc_pages(ROOT)
    protocol=read('benchmark/multidoc_protocol.json');manifest=read('data/multidoc/manifest.json')
    lookup={(p['document_id'],p['page']):p for p in pages}
    require_sources={'alice','nd13','nd69','nd42','sherlock'}
    if {p['document_id'] for p in pages}!=require_sources:raise ValueError('Expected all five corpus sources')
    if hashlib.sha256(composed_bytes(ROOT)).hexdigest()!=manifest['normalized_sha256']:raise ValueError('Corpus changed')
    for q in questions:
        if q['evidence_quote'] not in lookup[q['gold_source_id'],q['gold_page']]['text']:raise ValueError('Invalid gold evidence')
    old=[p for pattern in ['results/metrics.json','results/traces.jsonl','results/extension/metrics.json','results/extension/traces.jsonl','results/vietnamese/metrics.json','results/vietnamese/traces.jsonl','benchmark/questions.json','benchmark/extension_holdout.json','benchmark/vietnamese_questions.json'] for p in ROOT.glob(pattern)]
    inputs=old+[ROOT/p for p in ['data/multidoc/manifest.json','data/multidoc/nd69_pages.json','data/multidoc/nd42_pages.json','data/multidoc/sherlock_pages.json','data/pages.json','data/vietnamese/pages.json','benchmark/multidoc_questions.json','benchmark/multidoc_protocol.json','starter/src/fusion.py','starter/src/multilingual.py']]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    save('freeze.json',dict(utc=datetime.now(timezone.utc).isoformat(),hashes=hashes,protocol=protocol))
    started=time.perf_counter();store=None
    try:
        en=MyEmbedder();multi=MultilingualEmbedder()
        store=QdrantStore(str(ROOT/'.qdrant_multidoc'),384)
        chunks=build_chunks(pages,'B');texts=[c.text for c in chunks];stats={}
        cache=ROOT/'.embedding_cache';cache.mkdir(exist_ok=True)
        for collection,model in [('en',en),('multi',multi)]:
            tick=time.perf_counter()
            key=hashlib.sha256(json.dumps([model.model_name,importlib.metadata.version('fastembed'),texts]).encode()).hexdigest()
            path=cache/f'{key}.npy';cached=path.exists()
            vectors=np.load(path).tolist() if cached else model.embed_documents(texts)
            if not cached:np.save(path,vectors)
            store.upsert(collection,chunks,vectors)
            first=store.client.count(collection,exact=True).count
            store.upsert(collection,chunks,vectors)
            second=store.client.count(collection,exact=True).count
            if first!=len(chunks) or second!=first:raise RuntimeError('Repeat ingestion count mismatch')
            stats[collection]=dict(model=model.model_name,dimensions=384,chunks=len(chunks),characters=sum(map(len,texts)),embedding_cache_hit=cached,
                ingest_seconds_including_repeat=time.perf_counter()-tick,count_after_first=first,count_after_repeat=second)
            print(f'{collection}: {len(chunks)} chunks, {stats[collection]["ingest_seconds_including_repeat"]:.2f}s',flush=True)
        base=json.loads((ROOT/'benchmark/extension_protocol.json').read_text());base['base_collection']='en'
        rerank=HybridRetriever(store,base);rerank._load_reranker()
        fusion_en=FusionRetriever(store,base)
        fusion_multi=FusionRetriever(store,{**base,'base_collection':'multi'})
        traces=[]
        def query(q):
            tick=time.perf_counter();v_en=en.embed_query(q['question']);en_time=time.perf_counter()-tick
            tick=time.perf_counter();v_multi=multi.embed_query(q['question']);multi_time=time.perf_counter()-tick
            for s in STRATEGIES:
                tick=time.perf_counter();filters=q['filter'] or None
                if s=='C':hits=store.search('en',v_en,filters=filters);candidates=[]
                elif s=='D':hits,candidates=rerank.search(q['question'],v_en,filters=filters)
                elif s=='E':hits,candidates=fusion_en.search(q['question'],v_en,filters=filters)
                elif s=='F':hits=store.search('multi',v_multi,filters=filters);candidates=[]
                else:hits,candidates=fusion_multi.search(q['question'],v_multi,filters=filters)
                trace=dict(strategy=s,**evaluate_query(q,hits),
                    retrieval_seconds=time.perf_counter()-tick,shared_query_embedding_seconds=multi_time if s in ('F','G') else en_time,
                    applied_filter=filters or {},candidates=candidates)
                traces.append(trace)
            print(f"{q['id']} {q['split']}: "+' '.join(f"{t['strategy']}={int(t['hit3'])}" for t in traces[-5:]),flush=True)
        for q in questions:
            if q['split']=='dev':query(q)
        dev=summarize(traces)
        mean={s:sum(t['retrieval_seconds'] for t in traces if t['strategy']==s)/15 for s in STRATEGIES}
        winner=sorted(STRATEGIES,key=lambda s:(-dev[f'{s}/dev']['hit3']['rate'],-dev[f'{s}/dev']['hit1']['rate'],mean[s],s))[0]
        save('selection.json',dict(strategy=winner,criterion=protocol['selection'],frozen_at=datetime.now(timezone.utc).isoformat(),dev_metrics=dev,mean_dev_retrieval_seconds=mean))
        print('Selected before test:',winner,flush=True)
        for q in questions:
            if q['split']=='test':query(q)
        # Old Vietnamese questions are intentionally diagnostic after the independent-source test.
        for q in read('benchmark/vietnamese_questions.json'):
            query({**q,'split':'diagnostic','kind':'old_vi_diagnostic'})
        for path,digest in hashes.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise RuntimeError(f'Frozen input changed: {path}')
        (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
        save('metrics.json',summarize(traces));save('statistics.json',stats)
        save('by_source.json',grouped_metrics(traces,'gold_source_id'));save('by_kind.json',grouped_metrics(traces,'kind'))
        save('run.json',dict(utc=datetime.now(timezone.utc).isoformat(),input_hashes=hashes,total_seconds=time.perf_counter()-started,
            source_count=5,page_unit_count=len(pages),chunk_count=len(chunks),new_questions=45,diagnostic_questions=20,
            strategies=protocol['strategies'],selected_strategy=winner,
            mean_retrieval_seconds={s:sum(t['retrieval_seconds'] for t in traces if t['strategy']==s)/65 for s in STRATEGIES},
            versions={p:importlib.metadata.version(p) for p in ['fastembed','qdrant-client','onnxruntime','numpy']},api_cost_usd=0,
            note='No tuning on held-out source documents. New labels are source-authored/source-reviewed, not automatically human verified; original content review applies only to its original scope. E5 changes embedding model explicitly, so this is an extension separate from original same-model A/B/C.'))
        cache_root=Path('/tmp/fastembed_cache/models--Xenova--multilingual-e5-small')
        if (cache_root/'refs/main').exists():
            revision=(cache_root/'refs/main').read_text().strip();snapshot=cache_root/'snapshots'/revision
            save('e5_model_snapshot.json',dict(repository='Xenova/multilingual-e5-small',revision=revision,model_file='onnx/model_quantized.onnx',files={str(p.relative_to(snapshot)):hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshot.rglob('*') if p.is_file()}))
        print(json.dumps(summarize(traces),indent=2))
    except Exception:
        logging.exception('Multi-document benchmark failed; no fallback')
        raise
    finally:
        if store:store.close()


if __name__=='__main__':main()
