"""Persistent Qdrant local store; exact cosine retrieval with payload filters."""
import uuid
from dataclasses import asdict
from qdrant_client import QdrantClient, models


class QdrantStore:
    def __init__(self, path: str, dimensions: int):
        self.client = QdrantClient(path=path)
        self.dimensions = dimensions

    def upsert(self, strategy, chunks, vectors):
        if len(chunks) != len(vectors) or any(len(v) != self.dimensions for v in vectors):
            raise ValueError('Chunk/vector count or dimensions mismatch')
        # Full snapshot replacement removes obsolete chunks on corpus/config changes.
        if self.client.collection_exists(strategy):
            self.client.delete_collection(strategy)
        self.client.create_collection(strategy, vectors_config=models.VectorParams(size=self.dimensions, distance=models.Distance.COSINE))
        points = []
        for c, v in zip(chunks, vectors):
            payload = asdict(c)
            payload['metadata'] = {**c.metadata, 'document_id': c.document_id, 'source': c.source, 'page': c.page}
            points.append(models.PointStruct(id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)), vector=v, payload=payload))
        for start in range(0, len(points), 128):
            self.client.upsert(strategy, points[start:start+128], wait=True)

    def search(self, strategy, query_vector, top_k=3, filters=None):
        if len(query_vector) != self.dimensions or top_k <= 0:
            raise ValueError('Invalid query dimensions/top_k')
        if filters and set(filters)-{'chapter', 'language'}:
            raise ValueError('Unsupported filter field')
        query_filter = models.Filter(must=[models.FieldCondition(key=f'metadata.{k}', match=models.MatchValue(value=v))
            for k, v in filters.items()]) if filters else None
        points = self.client.query_points(strategy, query=query_vector, query_filter=query_filter,
            limit=top_k, search_params=models.SearchParams(exact=True)).points
        return [{**p.payload, 'score': p.score} for p in points]

    def close(self):
        self.client.close()
