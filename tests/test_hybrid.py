"""Hybrid behavior tests; synthetic vectors/reranker are test fixtures only."""
import json
import tempfile
import unittest
from pathlib import Path
from starter.src.hybrid import HybridRetriever,tokenize
from starter.src.models import Chunk
from starter.src.store import QdrantStore
from starter.src.provenance import verify_recorded_input


class FixtureReranker:
    def rerank(self,query,documents,batch_size=16):
        return [-1. if 'pepper' in text else -8. for text in documents]


class HybridTests(unittest.TestCase):
    def test_union_dedup_reranking_and_both_branch_filters(self):
        config=dict(base_collection='B',dense_candidates=20,lexical_candidates=20,rerank_candidates=20)
        with tempfile.TemporaryDirectory() as path:
            store=QdrantStore(path,2)
            try:
                chunks=[Chunk('dense','d','s',1,'a story about a cake',{'chapter':'I'}),
                        Chunk('answer','d','s',2,'the cook said pepper',{'chapter':'I'}),
                        Chunk('outside','d','s',3,'pepper pepper cook',{'chapter':'II'})]
                store.upsert('B',chunks,[[1.,0.],[0.,1.],[1.,0.]])
                hybrid=HybridRetriever(store,config,reranker=FixtureReranker())
                hits,candidates=hybrid.search('What did the cook say?', [1.,0.],filters={'chapter':'I'})
                self.assertEqual(hits[0]['chunk_id'],'answer')
                self.assertEqual(hits[0]['score'],-1.)
                self.assertEqual(hits[0]['score_type'],'reranker_logit')
                self.assertEqual(len({h['chunk_id'] for h in candidates}),len(candidates))
                self.assertTrue(all(h['metadata']['chapter']=='I' for h in candidates))
                self.assertIsNotNone(hits[0]['dense_rank'])
                self.assertIsNotNone(hits[0]['lexical_rank'])
                self.assertTrue(all(h['metadata']['chapter']=='I' for h in hybrid.lexical('cook',{'chapter':'I'})))
                self.assertEqual(hybrid.search('pepper',[1.,0.],filters={'chapter':'XII'}),([],[]))
                self.assertRaises(ValueError,hybrid.search,'cook',[1.,0.],{'page':2})
            finally:store.close()

    def test_preserved_baseline_and_extension_trace_contract(self):
        import hashlib
        run=json.loads(Path('results/extension/run.json').read_text())
        for path,digest in run['input_hashes'].items():
            self.assertTrue(verify_recorded_input(Path.cwd(),path,digest))
        traces=[json.loads(line) for line in Path('results/extension/traces.jsonl').read_text().splitlines()]
        self.assertEqual(len(traces),60)
        self.assertEqual(sum(t['strategy']=='D' for t in traces),30)
        for t in traces:
            self.assertEqual(len(t['hits']),3)
            if t['strategy']=='D':
                self.assertTrue(all(h['score_type']=='reranker_logit' for h in t['hits']))
                if t['filter']:
                    self.assertTrue(all(all(h['metadata'][k]==v for k,v in t['filter'].items()) for h in t['candidates']))
        self.assertNotIn('the',tokenize('The Cook, PEPPER!'))
        self.assertIn('pepper',tokenize('The Cook, PEPPER!'))


if __name__=='__main__':unittest.main()
