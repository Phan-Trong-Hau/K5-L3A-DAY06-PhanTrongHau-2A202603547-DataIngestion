"""Run the frozen, reproducible three-strategy ingestion benchmark."""
import argparse
import hashlib
import importlib.metadata
import json
import logging
import platform
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from .ingestion import load_alice
from .chunking import fixed_size, by_paragraph
from .embeddings import MyEmbedder
from .store import QdrantStore
from .evaluation import evaluate_query, summarize

ROOT = Path(__file__).resolve().parents[2]


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'results')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=out/'errors.log', level=logging.WARNING, force=True)
    store = None
    try:
        protocol = json.loads((ROOT/'benchmark/protocol.json').read_text())
        questions = json.loads((ROOT/'benchmark/questions.json').read_text())
        manifest = json.loads((ROOT/'data/manifest.json').read_text())
        if hashlib.sha256((ROOT/'data/alice.txt').read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError('Corpus changed; regenerate manifest and re-verify benchmark')
        pages = load_alice(ROOT/'data/alice.txt')
        lookup = {(p.document_id,p.page): p for p in pages}
        for q in questions:
            if q['evidence_quote'] not in lookup[q['gold_source_id'],q['gold_page']].text:
                raise ValueError(f"Invalid evidence {q['id']}")
        if sum(q['split']=='dev' for q in questions)<15 or sum(q['split']=='test' for q in questions)<5:
            raise ValueError('Insufficient benchmark split')
        start = time.perf_counter()
        embedder = MyEmbedder()
        store = QdrantStore(str(ROOT/'.qdrant'), embedder.dimensions)
        chunks_by_strategy, stats = {}, {}
        # Cache keyed by model, installed provider version AND complete ordered texts.
        cache_dir = ROOT/'.embedding_cache'
        cache_dir.mkdir(exist_ok=True)
        for strategy, config in protocol['strategies'].items():
            tick = time.perf_counter()
            chunks = [c for p in pages for c in (fixed_size(p, config['size'], config['overlap'])
                if config['chunking']=='fixed' else by_paragraph(p, config['max_size']))]
            texts = [c.text for c in chunks]
            key = hashlib.sha256(json.dumps([embedder.model_name, importlib.metadata.version('fastembed'), texts]).encode()).hexdigest()
            cache = cache_dir/f'{key}.npy'
            cached = cache.exists()
            vectors = np.load(cache).tolist() if cached else embedder.embed_documents(texts)
            if not cached:
                np.save(cache, vectors)
            store.upsert(strategy, chunks, vectors)
            count1 = store.client.count(strategy, exact=True).count
            store.upsert(strategy, chunks, vectors)
            count2 = store.client.count(strategy, exact=True).count
            if count1 != len(chunks) or count2 != count1:
                raise RuntimeError('Re-ingestion duplicate check failed')
            lengths = [len(c.text) for c in chunks]
            stats[strategy] = dict(chunks=len(chunks), characters=sum(lengths),
                min_chars=min(lengths), mean_chars=float(np.mean(lengths)), max_chars=max(lengths),
                p50_chars=float(np.median(lengths)), p95_chars=float(np.percentile(lengths,95)),
                ingest_seconds_including_repeat=time.perf_counter()-tick, embedding_cache_hit=cached,
                count_after_first=count1, count_after_repeat=count2, api_cost_usd=0)
            chunks_by_strategy[strategy] = chunks
            print(f'{strategy}: {len(chunks)} chunks, repeat count {count2}', flush=True)
        query_vectors = {q['id']: embedder.embed_query(q['question']) for q in questions}
        traces = []
        for strategy in protocol['strategies']:
            for q in questions:
                if q['split'] == 'dev':
                    hits = store.search(strategy, query_vectors[q['id']], filters=q['filter'] if strategy=='C' else None)
                    traces.append(dict(strategy=strategy, **evaluate_query(q, hits)))
        dev_metrics = summarize(traces)
        winner = sorted(protocol['strategies'], key=lambda s: (-dev_metrics[f'{s}/dev']['hit3']['rate'],
            -dev_metrics[f'{s}/dev']['hit1']['rate'], stats[s]['chunks'], s))[0]
        save(out/'selection.json', dict(strategy=winner, criterion=protocol['selection'],
            frozen_at=datetime.now(timezone.utc).isoformat(), dev_metrics=dev_metrics))
        for strategy in protocol['strategies']:
            for q in questions:
                if q['split']=='test':
                    hits = store.search(strategy, query_vectors[q['id']], filters=q['filter'] if strategy=='C' else None)
                    traces.append(dict(strategy=strategy, **evaluate_query(q,hits)))
        (out/'traces.jsonl').write_text(''.join(json.dumps(t,ensure_ascii=False)+'\n' for t in traces))
        save(out/'metrics.json', summarize(traces))
        save(out/'statistics.json', stats)
        samples = []
        for s,chunks in chunks_by_strategy.items():
            for p in pages[:10]:
                offset = len(p.text)//2
                covering = [asdict(c) for c in chunks if c.page==p.page and c.metadata['start']<=offset<c.metadata['end']]
                samples.append(dict(strategy=s,page=p.page,offset=offset,chunks=covering,
                    score=None,reason='',reviewer='pending student review'))
        save(out/'coherence_samples.json', samples)
        save(out/'run.json', dict(started_model=embedder.model_name,dimensions=embedder.dimensions,
            utc=datetime.now(timezone.utc).isoformat(),python=platform.python_version(),
            versions={p:importlib.metadata.version(p) for p in ['fastembed','qdrant-client','onnxruntime','numpy']},
            benchmark_sha256=hashlib.sha256((ROOT/'benchmark/questions.json').read_bytes()).hexdigest(),
            corpus_sha256=manifest['sha256'], total_seconds=time.perf_counter()-start,
            search='exact cosine',provider='FastEmbed ONNX CPU',api_cost_usd=0,
            note='Costs exclude CPU/electricity; ingest times include two snapshot writes; C reuses B embedding cache.'))
        print(json.dumps(summarize(traces),indent=2))
        print(f'Dev-selected strategy: {winner}')
    except Exception:
        logging.exception('Pipeline failed; no mock fallback')
        raise
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    main()
