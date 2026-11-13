"""D: B's unchanged chunks, dense+BM25 candidates, RRF, real cross-encoder.

No gold/evidence/benchmark labels are accepted by the retriever.
BM25 only supplies lexical candidates; dense search remains in Qdrant.
"""
import math
import re
from collections import Counter

STOPWORDS=set('a an the and or but if then of to in on at for by with from as is are was were be been being it its this that these those what which who whom when where why how did do does have has had he she they them his her their i you we me my our your chapter'.split())


def tokenize(text):
    return [t for t in re.findall(r'[^\W_]+',text.lower(),flags=re.UNICODE) if t not in STOPWORDS]


class HybridRetriever:
    model_name='Xenova/ms-marco-MiniLM-L-6-v2'

    def __init__(self, store, config, reranker=None):
        self.store=store
        self.config=config
        self.collection=config['base_collection']
        self.documents=[]
        offset=None
        while True:
            points,offset=store.client.scroll(self.collection,limit=256,offset=offset,with_payload=True,with_vectors=False)
            self.documents.extend(p.payload for p in points)
            if offset is None:break
        if not self.documents:
            raise RuntimeError('B collection is empty. Run the baseline pipeline first.')
        self.documents.sort(key=lambda d:d['chunk_id'])
        self.terms=[Counter(tokenize(d['text'])) for d in self.documents]
        self.lengths=[sum(t.values()) for t in self.terms]
        self.avg_length=sum(self.lengths)/len(self.lengths) or 1
        df=Counter(t for terms in self.terms for t in terms)
        n=len(self.documents)
        self.idf={t:math.log(1+(n-count+0.5)/(count+0.5)) for t,count in df.items()}
        self.reranker=reranker

    def _load_reranker(self):
        if self.reranker is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            self.reranker=TextCrossEncoder(self.config['reranker'].split(' via ')[0],threads=4)

    def lexical(self,question,filters):
        query=set(tokenize(question))
        results=[]
        for d,terms,length in zip(self.documents,self.terms,self.lengths):
            if filters and any(d['metadata'].get(k)!=v for k,v in filters.items()):continue
            score=0.
            for term in query:
                tf=terms.get(term,0)
                if tf:
                    score+=self.idf[term]*tf*2.5/(tf+1.5*(0.25+0.75*length/self.avg_length))
            if score>0:results.append({**d,'bm25_score':score})
        return sorted(results,key=lambda h:(-h['bm25_score'],h['chunk_id']))[:self.config['lexical_candidates']]

    def search(self,question,query_vector,filters=None,top_k=3):
        if top_k<=0:raise ValueError('top_k must be positive')
        if filters and set(filters)-{'chapter','language'}:raise ValueError('Unsupported metadata filter')
        dense=self.store.search(self.collection,query_vector,top_k=self.config['dense_candidates'],filters=filters)
        lexical=self.lexical(question,filters)
        fused={}
        for kind,hits in [('dense',dense),('lexical',lexical)]:
            for rank,h in enumerate(hits,1):
                key=h['chunk_id']
                if key not in fused:
                    fused[key]={**h,'rrf_score':0.,'dense_rank':None,'lexical_rank':None,'dense_score':None,'bm25_score':None}
                f=fused[key]
                f['rrf_score']+=1/(60+rank)
                f[f'{kind}_rank']=rank
                f['dense_score' if kind=='dense' else 'bm25_score']=h['score'] if kind=='dense' else h['bm25_score']
        candidates=sorted(fused.values(),key=lambda h:(-h['rrf_score'],h['chunk_id']))[:self.config['rerank_candidates']]
        if not candidates:return [],[]
        self._load_reranker()
        scores=list(self.reranker.rerank(question,[h['text'] for h in candidates],batch_size=16))
        if len(scores)!=len(candidates) or any(not math.isfinite(float(s)) for s in scores):
            raise RuntimeError('Invalid cross-encoder output; no fallback')
        for h,score in zip(candidates,scores):
            h['score']=float(score)
            h['score_type']='reranker_logit'
        ranked=sorted(candidates,key=lambda h:(-h['score'],-h['rrf_score'],h['chunk_id']))
        return ranked[:top_k],ranked
