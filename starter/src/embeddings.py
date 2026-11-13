"""CPU ONNX semantic embeddings. Provider errors propagate."""
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, question: str) -> list[float]: ...


class MyEmbedder:
    def __init__(self, model_name: str = 'BAAI/bge-small-en-v1.5') -> None:
        from fastembed import TextEmbedding
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name, threads=4)
        self.dimensions = len(next(self.model.embed(['dimension probe'])))

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.model.passage_embed(texts, batch_size=32)]

    def embed_query(self, question: str) -> list[float]:
        return next(self.model.query_embed(question)).tolist()
