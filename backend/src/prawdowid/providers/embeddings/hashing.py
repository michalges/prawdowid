import hashlib
import itertools
from dataclasses import dataclass

import numpy as np

from prawdowid.core.text import get_content_stems, normalize_for_match
from prawdowid.providers.embeddings.base import EmbeddingKind, EmbeddingMatrix, get_normalized_rows


@dataclass(frozen=True)
class HashingEmbeddingProvider:
    """Offline, dependency-free embeddings: hashed stems + character trigrams. Weaker than a neural
    model, but deterministic, instant and good enough for tests and keyless demos."""

    dimensions: int = 1024

    @property
    def model_id(self) -> str:
        return f"hashing/stems+char3-{self.dimensions}"

    def embed(self, texts: list[str], kind: EmbeddingKind) -> EmbeddingMatrix:
        matrix = np.zeros((len(texts), self.dimensions), dtype=np.float32)
        for row, text in enumerate(texts):
            for feature, weight in self._get_features(text):
                matrix[row, self._get_bucket(feature)] += weight
        return get_normalized_rows(matrix)

    def _get_features(self, text: str) -> list[tuple[str, float]]:
        stems = get_content_stems(text)
        features = [(f"w:{stem}", 1.0) for stem in stems]
        features += [(f"b:{first}_{second}", 0.5) for first, second in itertools.pairwise(stems)]
        normalized = normalize_for_match(text)
        features += [
            (f"c:{normalized[i : i + 3]}", 0.2) for i in range(max(len(normalized) - 2, 0))
        ]
        return features

    def _get_bucket(self, feature: str) -> int:
        digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
        return int.from_bytes(digest, "little") % self.dimensions
