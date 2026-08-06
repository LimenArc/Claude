"""Group same-story-different-outlet items together.

Local sentence-transformers embeddings when available, TF-IDF otherwise. Both
paths end in the same single-link agglomeration over a cosine similarity
matrix, so the fallback behaves like the real thing, just with a looser
threshold (bag-of-words similarity scores lower for the same pair of stories).
"""

from __future__ import annotations

import logging
from collections import Counter

import numpy as np

from .config import ClusterConfig
from .models import Cluster, Item

log = logging.getLogger(__name__)

_EMBEDDER_CACHE: dict[str, object] = {}


def _cluster_text(item: Item) -> str:
    """Title carries most of the signal; a little body disambiguates."""
    body = " ".join(item.text.split()[:80])
    return f"{item.title}. {body}"


def load_embedder(model_name: str):
    """Return a sentence-transformers model, or None if unavailable."""
    if model_name in _EMBEDDER_CACHE:
        return _EMBEDDER_CACHE[model_name]
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        log.info("sentence-transformers not installed; clustering falls back to TF-IDF")
        _EMBEDDER_CACHE[model_name] = None
        return None
    try:
        model = SentenceTransformer(model_name)
    except Exception as exc:  # no local weights, no network, OOM...
        log.warning("could not load embedding model %s (%s); falling back to TF-IDF", model_name, exc)
        model = None
    _EMBEDDER_CACHE[model_name] = model
    return model


def embed(texts: list[str], model_name: str) -> tuple[np.ndarray | None, str]:
    """Embed texts, returning (matrix, method). Rows are L2-normalised."""
    model = load_embedder(model_name)
    if model is None:
        return None, "tfidf"
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32), "embeddings"


def tfidf_matrix(texts: list[str]) -> np.ndarray:
    """Character n-gram TF-IDF.

    Character n-grams beat word n-grams here by a wide margin: news headlines
    describe the same event with different morphology ("raises rates" vs "rate
    rise"), which word features miss entirely. Measured on same-story pairs,
    char_wb 3-5 scores 0.37-0.77 while unrelated stories stay under 0.15.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True
    )
    matrix = vectorizer.fit_transform(texts)
    # TfidfVectorizer already L2-normalises rows, so the dot product is cosine.
    return np.asarray(matrix.todense(), dtype=np.float32)


def similarity_matrix(items: list[Item], cfg: ClusterConfig) -> tuple[np.ndarray, float]:
    """Pairwise cosine similarity plus the threshold appropriate to the method."""
    texts = [_cluster_text(i) for i in items]
    vectors, method = embed(texts, cfg.embedding_model)
    if vectors is None:
        vectors = tfidf_matrix(texts)
        threshold = cfg.tfidf_threshold
    else:
        threshold = cfg.cosine_threshold
    log.info("clustering %d items via %s (threshold %.2f)", len(items), method, threshold)
    return vectors @ vectors.T, threshold


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def _category(items: list[Item]) -> str:
    """Majority category, ties broken by source weight.

    A story that runs in both a world-news and a tech feed should be filed
    where most of its coverage sits, so category quotas stay meaningful.
    """
    counts = Counter(i.category for i in items)
    top = max(counts.values())
    contenders = {c for c, n in counts.items() if n == top}
    if len(contenders) == 1:
        return contenders.pop()
    best = max((i for i in items if i.category in contenders), key=lambda i: i.source_weight)
    return best.category


def cluster_items(items: list[Item], cfg: ClusterConfig) -> list[Cluster]:
    """Single-link agglomeration of items into story clusters."""
    if not items:
        return []
    if len(items) == 1:
        return [Cluster(items=list(items), category=items[0].category)]

    sims, threshold = similarity_matrix(items, cfg)
    max_span = cfg.max_cluster_span_hours * 3600.0
    uf = _UnionFind(len(items))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if sims[i, j] < threshold:
                continue
            if abs((items[i].published - items[j].published).total_seconds()) > max_span:
                continue
            uf.union(i, j)

    groups: dict[int, list[Item]] = {}
    for index, item in enumerate(items):
        groups.setdefault(uf.find(index), []).append(item)

    clusters = [Cluster(items=group, category=_category(group)) for group in groups.values()]
    clusters.sort(key=lambda c: (-c.corroboration, -c.hn_points))
    log.info("%d items collapsed into %d clusters", len(items), len(clusters))
    return clusters
