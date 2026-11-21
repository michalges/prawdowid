from dataclasses import dataclass, field
from typing import Any

import numpy as np

from prawdowid.providers.embeddings.base import (
    EmbeddingError,
    EmbeddingKind,
    EmbeddingMatrix,
    get_normalized_rows,
)

E5_PREFIXES: dict[EmbeddingKind, str] = {"query": "query: ", "passage": "passage: "}


@dataclass
class SentenceTransformersEmbeddingProvider:
    """Local neural embeddings (optional extra `embeddings`). Runs on-premises: no data leaves the
    host. e5 models expect `query:` / `passage:` prefixes."""

    model_name: str
    _model: Any = field(default=None, init=False, repr=False)

    @property
    def model_id(self) -> str:
        return f"sentence-transformers/{self.model_name}"

    @property
    def dimensions(self) -> int:
        return int(self._get_model().get_sentence_embedding_dimension())

    def embed(self, texts: list[str], kind: EmbeddingKind) -> EmbeddingMatrix:
        prefix = E5_PREFIXES[kind] if "e5" in self.model_name.lower() else ""
        vectors = self._get_model().encode(
            [prefix + text for text in texts], batch_size=32, show_progress_bar=False
        )
        return get_normalized_rows(np.asarray(vectors, dtype=np.float32))

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise EmbeddingError(
                    "sentence-transformers is not installed: `uv sync --extra embeddings`"
                ) from error
            self._model = SentenceTransformer(self.model_name)
        return self._model
