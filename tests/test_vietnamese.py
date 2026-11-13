"""Frozen source-test, chapter boundary, physical-page provenance regressions."""
import hashlib
import json
from pathlib import Path
import unittest
from starter.src.run_vietnamese import build_chunks
from starter.src.evaluation import summarize
from starter.src.provenance import verify_recorded_input,local_source_path


class VietnameseTests(unittest.TestCase):
    def test_source_evidence_and_chunk_offsets(self):
        pages=json.loads(Path('data/vietnamese/pages.json').read_text())
        questions=json.loads(Path('benchmark/vietnamese_questions.json').read_text())
        self.assertEqual(len(pages),39)
        self.assertEqual(len(questions),20)
        for q in questions:
            self.assertIn(q['evidence_quote'],pages[q['gold_page']-1]['text'])
            self.assertEqual(q['split'],'external_test')
        for strategy in 'AB':
            chunks=build_chunks(pages,strategy)
            self.assertEqual(len(chunks),len({c.chunk_id for c in chunks}))
            for c in chunks:
                row=pages[c.page-1];a,b=c.metadata['start'],c.metadata['end']
                self.assertEqual(c.text,row['text'][a:b])
                self.assertTrue(any(span['start']<=a<b<=span['end'] and span['chapter']==c.metadata['chapter'] for span in row['metadata']['chapter_spans']))
            for row in pages:
                covered=set()
                for c in chunks:
                    if c.page==row['page']:covered.update(range(c.metadata['start'],c.metadata['end']))
                self.assertTrue(all(i in covered for i,char in enumerate(row['text']) if not char.isspace()))

    def test_packaged_source_is_portable_and_unchanged(self):
        manifest=json.loads(Path('data/vietnamese/manifest.json').read_text())
        for key in ['source_id','title','source_path_or_url','local_path','license_or_permission','accessed_at','pages']:
            self.assertTrue(manifest.get(key))
        self.assertFalse(Path(manifest['local_path']).is_absolute())
        source=local_source_path(Path.cwd(),manifest)
        self.assertTrue(source.is_file())
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),manifest['sha256'])

    def test_frozen_metrics_and_filter_constraints(self):
        run=json.loads(Path('results/vietnamese/run.json').read_text())
        for path,digest in run['input_hashes'].items():
            self.assertTrue(verify_recorded_input(Path.cwd(),path,digest))
        traces=[json.loads(line) for line in Path('results/vietnamese/traces.jsonl').read_text().splitlines()]
        self.assertEqual(len(traces),80)
        self.assertEqual(summarize(traces),json.loads(Path('results/vietnamese/metrics.json').read_text()))
        for t in traces:
            self.assertEqual(len(t['hits']),3)
            if t['strategy'] in 'CD' and t['filter']:
                for h in t['hits']+t['candidates']:
                    self.assertTrue(all(h['metadata'][k]==v for k,v in t['filter'].items()))
        # Explicitly retain an observed regression: reranker can demote a correct dense result.
        q=[t for t in traces if t['id']=='vi10']
        self.assertTrue(next(t for t in q if t['strategy']=='C')['hit3'])
        self.assertFalse(next(t for t in q if t['strategy']=='D')['hit3'])


if __name__=='__main__':unittest.main()
