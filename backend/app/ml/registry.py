from dataclasses import dataclass

from fastembed import TextEmbedding
from fastembed.common.model_description import ModelSource, PoolingType
from fastembed.rerank.cross_encoder import TextCrossEncoder


@dataclass(frozen=True)
class DenseModelSpec:
    key: str
    hf_repo: str
    model_file: str
    dim: int
    pooling: PoolingType
    query_prefix: str
    description: str


@dataclass(frozen=True)
class RerankerSpec:
    key: str
    hf_repo: str
    model_file: str
    description: str


DENSE_MODELS: dict[str, DenseModelSpec] = {
    "arctic-embed-xs-int8": DenseModelSpec(
        key="arctic-embed-xs-int8",
        hf_repo="Snowflake/snowflake-arctic-embed-xs",
        model_file="onnx/model_quantized.onnx",
        dim=384,
        pooling=PoolingType.CLS,
        # Arctic embed is trained with an instruction prefix on queries only.
        query_prefix="Represent this sentence for searching relevant passages: ",
        description="Snowflake Arctic Embed XS (22M params, 6 layers), int8",
    ),
    "bge-small-en-v1.5-int8": DenseModelSpec(
        key="bge-small-en-v1.5-int8",
        hf_repo="Xenova/bge-small-en-v1.5",
        model_file="onnx/model_quantized.onnx",
        dim=384,
        pooling=PoolingType.CLS,
        query_prefix="Represent this sentence for searching relevant passages: ",
        description="BAAI bge-small-en-v1.5 (33M params, 12 layers), int8",
    ),
}

RERANKERS: dict[str, RerankerSpec] = {
    "ms-marco-minilm-l6-int8": RerankerSpec(
        key="ms-marco-minilm-l6-int8",
        hf_repo="Xenova/ms-marco-MiniLM-L-6-v2",
        model_file="onnx/model_quantized.onnx",
        description="MS MARCO MiniLM-L6 cross-encoder (22M params), int8",
    ),
}

_registered = False


def register_custom_models() -> None:
    """fastembed only knows its built-in model list, so the quantized
    variants have to be registered once per process before loading."""
    global _registered
    if _registered:
        return
    for spec in DENSE_MODELS.values():
        TextEmbedding.add_custom_model(
            model=f"papermind/{spec.key}",
            pooling=spec.pooling,
            normalization=True,
            sources=ModelSource(hf=spec.hf_repo),
            dim=spec.dim,
            model_file=spec.model_file,
        )
    for spec in RERANKERS.values():
        TextCrossEncoder.add_custom_model(
            model=f"papermind/{spec.key}",
            sources=ModelSource(hf=spec.hf_repo),
            model_file=spec.model_file,
        )
    _registered = True
