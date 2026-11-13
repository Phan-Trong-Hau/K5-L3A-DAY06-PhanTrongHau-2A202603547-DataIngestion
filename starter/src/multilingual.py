"""Multilingual E5-small ONNX INT8 with explicit retrieval prefixes.
Source usage: https://huggingface.co/intfloat/multilingual-e5-small
ONNX export: https://huggingface.co/Xenova/multilingual-e5-small
"""
from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource,PoolingType


class MultilingualEmbedder:
    model_name='Xenova/multilingual-e5-small'
    dimensions=384

    def __init__(self):
        if not any(m['model']==self.model_name for m in TextEmbedding.list_supported_models()):
            TextEmbedding.add_custom_model(model=self.model_name,pooling=PoolingType.MEAN,normalization=True,
                sources=ModelSource(hf=self.model_name),dim=384,model_file='onnx/model_quantized.onnx',
                description='Multilingual E5-small INT8, mean pool, L2 normalize; explicit query/passage prefixes',
                license='mit',size_in_gb=0.118)
        self.model=TextEmbedding(self.model_name,threads=4)

    def embed_documents(self,texts):
        return [v.tolist() for v in self.model.embed(['passage: '+t for t in texts],batch_size=16)]

    def embed_query(self,question):
        return next(self.model.embed(['query: '+question])).tolist()
