"""RRF-only ablation of the existing hybrid retriever; no cross-encoder."""
from .hybrid import HybridRetriever


class FusionRetriever(HybridRetriever):
    def search(self,question,query_vector,filters=None,top_k=3):
        if top_k<=0:raise ValueError('top_k must be positive')
        if filters and set(filters)-{'chapter','language'}:raise ValueError('Unsupported metadata filter')
        dense=self.store.search(self.collection,query_vector,top_k=self.config['dense_candidates'],filters=filters)
        lexical=self.lexical(question,filters)
        fused={}
        for kind,hits in [('dense',dense),('lexical',lexical)]:
            for rank,h in enumerate(hits,1):
                if h['chunk_id'] not in fused:
                    fused[h['chunk_id']]={**h,'rrf_score':0.,'dense_rank':None,'lexical_rank':None,'dense_score':None,'bm25_score':None}
                row=fused[h['chunk_id']]
                row['rrf_score']+=1/(60+rank)
                row[f'{kind}_rank']=rank
                row['dense_score' if kind=='dense' else 'bm25_score']=h['score'] if kind=='dense' else h['bm25_score']
        ranked=sorted(fused.values(),key=lambda h:(-h['rrf_score'],h['chunk_id']))[:self.config['rerank_candidates']]
        for h in ranked:h.update(score=h['rrf_score'],score_type='rrf_score')
        return ranked[:top_k],ranked
