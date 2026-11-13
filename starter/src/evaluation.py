"""Strict source+unit+complete evidence metrics, separate from human judgments."""
from collections import defaultdict
from typing import Any
from .ingestion import normalize_text


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    golds = question.get('alternatives', []) + [{'source_id': question['gold_source_id'],
        'page': question['gold_page'], 'evidence_quote': question['evidence_quote']}]
    for hit in hits:
        m = hit['metadata']
        hit['evidence_hit'] = any(m['document_id'] == g['source_id'] and m['page'] == g['page']
            and normalize_text(g['evidence_quote']) in normalize_text(hit['text']) for g in golds)
    return {**question, 'hits': hits, 'hit1': bool(hits and hits[0]['evidence_hit']),
            'hit3': any(h['evidence_hit'] for h in hits[:3])}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    groups = defaultdict(list)
    for t in traces:
        groups[f"{t['strategy']}/{t['split']}"].append(t)
    return {k: {'n': len(ts), **{metric: {'hits': sum(t[metric] for t in ts),
        'rate': sum(t[metric] for t in ts)/len(ts)} for metric in ('hit1', 'hit3')}} for k, ts in groups.items()}
