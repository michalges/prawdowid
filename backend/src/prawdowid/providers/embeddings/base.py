from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

type EmbeddingKind = Literal["query", "passage"]
type EmbeddingMatrix = NDArray[np.float32]


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    def embed(self, texts: list[str], kind: EmbeddingKind) -> EmbeddingMatrix:
        """Returns L2-normalized rows, one per text."""
        ...


def get_normalized_rows(matrix: NDArray[np.floating]) -> EmbeddingMatrix:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (matrix / norms).astype(np.float32)
