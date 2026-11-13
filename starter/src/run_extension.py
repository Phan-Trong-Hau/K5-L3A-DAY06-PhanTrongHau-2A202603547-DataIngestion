"""Evaluate post-hoc D and a newly frozen 10-question holdout, preserving baseline."""
import hashlib
import importlib.metadata
import json
import logging
import time
from datetime import datetime,timezone
from pathlib import Path
from .embeddings import MyEmbedder
from .evaluation import evaluate_query,summarize
from .hybrid import HybridRetriever
from .ingestion import load_alice
from .store import QdrantStore

ROOT=Path(__file__).resolve().parents[2]


def main():
    out=ROOT/'results/extension';out.mkdir(exist_ok=True,parents=True)
    logging.basicConfig(filename=out/'errors.log',level=logging.WARNING,force=True)
    read=lambda path:json.loads((ROOT/path).read_text())
    config=read('benchmark/extension_protocol.json')
    original=read('benchmark/questions.json')
    holdout=read('benchmark/extension_holdout.json')
    pages={(p.document_id,p.page):p for p in load_alice(ROOT/'data/alice.txt')}
    for q in original+holdout:
        if q['evidence_quote'] not in pages[q['gold_source_id'],q['gold_page']].text:
            raise ValueError(f"Evidence not verified: {q['id']}")
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
        [ROOT/'results/traces.jsonl',ROOT/'results/metrics.json',ROOT/'benchmark/extension_protocol.json',ROOT/'benchmark/extension_holdout.json']}
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    save('freeze.json',dict(utc=datetime.now(timezone.utc).isoformat(),hashes=hashes,status='pre-run; original test already inspected'))
    started=time.perf_counter();store=None
    try:
        embedder=MyEmbedder()
        store=QdrantStore(str(ROOT/'.qdrant'),embedder.dimensions)
        retriever=HybridRetriever(store,config)
        model_start=time.perf_counter();retriever._load_reranker();model_seconds=time.perf_counter()-model_start
        traces=[];timings=[]
        for q in original+holdout:
            tick=time.perf_counter()
            vector=embedder.embed_query(q['question'])
            hits,candidates=retriever.search(q['question'],vector,filters=q['filter'] or None)
            duration=time.perf_counter()-tick
            trace=dict(strategy='D',**evaluate_query(q,hits),elapsed_seconds=duration,
                candidates=candidates,post_hoc_original_test=q['split']=='test')
            traces.append(trace);timings.append(duration)
            print(f"D {q['id']} {q['split']}: hit1={trace['hit1']} hit3={trace['hit3']} ({duration:.3f}s)",flush=True)
            if q['split']=='holdout':
                for s in 'ABC':
                    tick=time.perf_counter()
                    hits=store.search(s,vector,filters=q['filter'] if s=='C' else None)
                    traces.append(dict(strategy=s,**evaluate_query(q,hits),elapsed_seconds=time.perf_counter()-tick))
        for path,digest in hashes.items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:
                raise RuntimeError(f'Input changed during experiment: {path}')
        (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
        save('metrics.json',summarize(traces))
        save('run.json',dict(utc=datetime.now(timezone.utc).isoformat(),config=config,input_hashes=hashes,
            reranker_load_seconds=model_seconds,total_seconds=time.perf_counter()-started,
            d_mean_query_seconds=sum(timings)/len(timings),candidate_document_count=len(retriever.documents),
            versions={p:importlib.metadata.version(p) for p in ['fastembed','onnxruntime','qdrant-client']},
            api_cost_usd=0,note='Baseline A/B/C artifacts untouched. Original test diagnostic after inspection; fresh holdout same corpus, small sample. No human coherence/grounding labels generated for D.'))
        print(json.dumps(summarize(traces),indent=2))
    except Exception:
        logging.exception('Extension failed; no fallback')
        raise
    finally:
        if store:store.close()


if __name__=='__main__':main()
