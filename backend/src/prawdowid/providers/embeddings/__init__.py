from prawdowid.config import EmbeddingProviderName, Settings
from prawdowid.providers.embeddings.base import EmbeddingProvider
from prawdowid.providers.embeddings.hashing import HashingEmbeddingProvider
from prawdowid.providers.embeddings.sentence_transformers import (
    SentenceTransformersEmbeddingProvider,
)


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    match settings.embedding_provider:
        case EmbeddingProviderName.HASHING:
            return HashingEmbeddingProvider()
        case EmbeddingProviderName.SENTENCE_TRANSFORMERS:
            return SentenceTransformersEmbeddingProvider(model_name=settings.embedding_model)
