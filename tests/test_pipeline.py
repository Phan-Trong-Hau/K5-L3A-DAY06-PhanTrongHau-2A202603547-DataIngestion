"""Boundary/evidence regressions and real persistent vector-store integration."""
import tempfile
import unittest
from pathlib import Path
from starter.src.models import DocumentPage, Chunk
from starter.src.chunking import fixed_size, by_paragraph
from starter.src.ingestion import normalize_text, load_alice
from starter.src.evaluation import evaluate_query, summarize
from starter.src.store import QdrantStore


class PipelineTests(unittest.TestCase):
    def test_chunk_boundaries_and_coverage(self):
        page = DocumentPage('d','s',1,'one two three\n\nfour five six\n\n'+'long '*40, {'chapter':'I'})
        for chunks in [fixed_size(page,30,5), by_paragraph(page,30)]:
            self.assertTrue(all(0<len(c.text)<=30 for c in chunks))
            covered = set()
            for c in chunks:
                a,b=c.metadata['start'],c.metadata['end']
                self.assertEqual(c.text,page.text[a:b])
                covered.update(range(a,b))
            self.assertTrue(all(i in covered for i,c in enumerate(page.text) if not c.isspace()))
        self.assertRaises(ValueError, fixed_size, page, 30, 30)
        self.assertRaises(ValueError, by_paragraph, page, 0)

    def test_evidence_requires_complete_quote_and_correct_location(self):
        q=dict(id='q',gold_source_id='d',gold_page=1,evidence_quote='if X then Y')
        def hit(text,page=1):
            return dict(text=text,metadata=dict(document_id='d',page=page))
        self.assertFalse(evaluate_query(q,[hit('then Y')])['hit3'])
        self.assertFalse(evaluate_query(q,[hit('if X then Y',2)])['hit3'])
        self.assertTrue(evaluate_query(q,[hit('if X then Y')])['hit1'])
        q['alternatives']=[dict(source_id='d',page=2,evidence_quote='X implies Y')]
        self.assertTrue(evaluate_query(q,[hit('X implies Y',2)])['hit3'])
        self.assertFalse(evaluate_query(q,[])['hit1'])

    def test_persistent_store_filter_replacement_and_cosine(self):
        # Synthetic vectors ONLY test database semantics; never used in experiment.
        with tempfile.TemporaryDirectory() as d:
            store=QdrantStore(d,2)
            chunks=[Chunk('one','d','s',1,'first',{'chapter':'I'}),Chunk('two','d','s',2,'second',{'chapter':'II'})]
            store.upsert('test',chunks,[[1.,0.],[0.,1.]])
            self.assertEqual(store.search('test',[1.,0.])[0]['chunk_id'],'one')
            self.assertEqual(store.search('test',[1.,0.],filters={'chapter':'II'})[0]['chunk_id'],'two')
            store.upsert('test',chunks[:1],[[1.,0.]])
            self.assertEqual(store.client.count('test').count,1)
            store.close()
            store=QdrantStore(d,2)
            self.assertEqual(store.search('test',[1.,0.])[0]['text'],'first')
            self.assertEqual(store.search('test',[1.,0.],filters={'chapter':'II'}),[])
            self.assertRaises(ValueError,store.search,'test',[1.,0.],3,{'page':1})
            store.close()

    def test_corpus_and_unicode(self):
        self.assertEqual(normalize_text('e\u0301  x\r\n\r\ny'), 'é x\n\ny')
        pages=load_alice(Path('data/alice.txt'))
        self.assertGreaterEqual(len(pages),30)
        self.assertTrue(all(len(p.text)>=1500 for p in pages))
        self.assertEqual(len({p.page for p in pages}),len(pages))


if __name__=='__main__':
    unittest.main()
