"""Controlled ablations, multilingual prefix contract, and frozen source-split tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from starter.src.models import Chunk
from starter.src.store import QdrantStore
from starter.src.fusion import FusionRetriever
from starter.src.multilingual import MultilingualEmbedder
from starter.src.evaluation import summarize
from starter.src.corpus import load_multidoc_pages
from starter.src.provenance import verify_recorded_input


class PrefixProbe:
    def __init__(self):self.calls=[]
    def embed(self,texts,**kwargs):
        self.calls.append(list(texts))
        return iter([np.zeros(384) for _ in texts])


class MultidocTests(unittest.TestCase):
    def test_multilingual_explicit_prefixes(self):
        # No semantic score claims; this fixture tests only query/passage preprocessing.
        m=object.__new__(MultilingualEmbedder);m.model=PrefixProbe()
        m.embed_documents(['dữ liệu cá nhân','a detective'])
        m.embed_query('định danh là gì?')
        self.assertEqual(m.model.calls,[['passage: dữ liệu cá nhân','passage: a detective'],['query: định danh là gì?']])

    def test_rrf_ablation_never_calls_cross_encoder(self):
        class ForbiddenReranker:
            def rerank(self,*args,**kwargs):raise AssertionError('RRF-only ablation must not rerank')
        with tempfile.TemporaryDirectory() as d:
            store=QdrantStore(d,2)
            try:
                chunks=[Chunk('a','one','s',1,'định danh điện tử',{'language':'vi'}),Chunk('b','two','s',1,'public service',{'language':'en'})]
                store.upsert('en',chunks,[[1.,0.],[0.,1.]])
                fusion=FusionRetriever(store,dict(base_collection='en',dense_candidates=20,lexical_candidates=20,rerank_candidates=20),reranker=ForbiddenReranker())
                hits,candidates=fusion.search('định danh',[0.,1.],filters={'language':'vi'})
                self.assertEqual(len(candidates),1)
                self.assertEqual(hits[0]['chunk_id'],'a')
                self.assertEqual(hits[0]['score_type'],'rrf_score')
                self.assertAlmostEqual(hits[0]['score'],2/61)
            finally:store.close()

    def test_disjoint_source_split_and_frozen_results(self):
        root=Path.cwd();questions=json.loads((root/'benchmark/multidoc_questions.json').read_text())
        dev={q['gold_source_id'] for q in questions if q['split']=='dev'}
        test={q['gold_source_id'] for q in questions if q['split']=='test'}
        self.assertEqual(dev,{'nd69'});self.assertEqual(test,{'nd42','sherlock'});self.assertFalse(dev&test)
        self.assertEqual(len(questions),45)
        source=load_multidoc_pages(root);lookup={(p['document_id'],p['page']):p for p in source}
        self.assertEqual(len({p['document_id'] for p in source}),5)
        for q in questions:self.assertIn(q['evidence_quote'],lookup[q['gold_source_id'],q['gold_page']]['text'])
        run_path=root/'results/multidoc/run.json'
        if not run_path.exists():self.skipTest('Run multidoc benchmark to verify stored metrics')
        run=json.loads(run_path.read_text())
        for path,digest in run['input_hashes'].items():self.assertTrue(verify_recorded_input(root,path,digest))
        traces=[json.loads(line) for line in (root/'results/multidoc/traces.jsonl').read_text().splitlines()]
        self.assertEqual(len(traces),325)
        self.assertEqual(summarize(traces),json.loads((root/'results/multidoc/metrics.json').read_text()))
        selection=json.loads((root/'results/multidoc/selection.json').read_text())
        self.assertLessEqual(selection['frozen_at'],run['utc'])
        for t in traces:
            self.assertEqual(len(t['hits']),3)
            for h in t['hits']:
                m=h['metadata'];page=lookup[m['document_id'],m['page']]
                self.assertEqual(h['text'],page['text'][m['start']:m['end']])
                if t['filter']:self.assertTrue(all(m[k]==v for k,v in t['filter'].items()))


if __name__=='__main__':unittest.main()
