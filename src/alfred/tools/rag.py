"""
RAG engine over the handover corpus.

Documents are split at level-2 (`##`) section boundaries; each chunk carries
its source document id and section header. Chunks are embedded and persisted
to a Chroma collection on disk. Retrieval returns the top-k chunks by
semantic similarity.

Embeddings are computed here and passed to Chroma as raw vectors — we do not
register a Chroma-side embedding function. This keeps the module independent
of Chroma's evolving embedding-function API surface and lets tests inject a
deterministic embedder via `set_embedder`.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from alfred.schemas.agent import RAGChunk

_COLLECTION_NAME = "handovers"
_EMBEDDING_MODEL_METADATA_KEY = "embedding_model"


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(r"(?m)^##\s+(.+)$")


def _chunk_markdown(text: str, document_id: str) -> list[dict[str, str]]:
    """Split markdown into chunks at level-2 header boundaries.

    Each chunk is the header line plus all content up to the next `##` header.
    Any preamble before the first `##` is emitted as a single "PREAMBLE" chunk.
    """
    chunks: list[dict[str, str]] = []
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        stripped = text.strip()
        if stripped:
            chunks.append(
                {
                    "document_id": document_id,
                    "section_header": "PREAMBLE",
                    "content": stripped,
                }
            )
        return chunks

    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            chunks.append(
                {
                    "document_id": document_id,
                    "section_header": "PREAMBLE",
                    "content": preamble,
                }
            )

    for i, m in enumerate(matches):
        header = m.group(1).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            chunks.append(
                {
                    "document_id": document_id,
                    "section_header": header,
                    "content": content,
                }
            )
    return chunks


# ---------------------------------------------------------------------------
# Embedder — replaceable for tests
# ---------------------------------------------------------------------------

Embedder = Callable[[list[str]], list[list[float]]]


def _default_embedder(model_name: str) -> Embedder:
    """Default: sentence-transformers SentenceTransformer.encode."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)

    def embed(texts: list[str]) -> list[list[float]]:
        vectors = model.encode(texts, normalize_embeddings=True)
        return [list(map(float, v)) for v in vectors]

    return embed


_embedder_factory: Callable[[str], Embedder] = _default_embedder
_EMBEDDER_CACHE: dict[str, Embedder] = {}


def set_embedder(factory: Callable[[str], Embedder]) -> None:
    """Replace the embedder factory. Tests use this to inject a deterministic fake."""
    global _embedder_factory
    _embedder_factory = factory
    _EMBEDDER_CACHE.clear()


def _make_embedder(model_name: str) -> Embedder:
    if model_name not in _EMBEDDER_CACHE:
        _EMBEDDER_CACHE[model_name] = _embedder_factory(model_name)
    return _EMBEDDER_CACHE[model_name]


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


def _iter_markdown_files(corpus_path: str) -> Iterable[Path]:
    root = Path(corpus_path)
    if root.is_file():
        yield root
        return
    yield from sorted(root.rglob("*.md"))


def index_corpus(corpus_path: str, index_path: str, embedding_model: str) -> int:
    """Chunk, embed, and persist the handover corpus. Returns the chunk count.

    If a collection already exists at `index_path` it is deleted and rebuilt.
    """
    import chromadb

    Path(index_path).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=index_path)
    try:
        client.delete_collection(_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=_COLLECTION_NAME,
        metadata={_EMBEDDING_MODEL_METADATA_KEY: embedding_model},
    )

    all_chunks: list[dict[str, str]] = []
    for path in _iter_markdown_files(corpus_path):
        all_chunks.extend(_chunk_markdown(path.read_text(), path.stem))

    if not all_chunks:
        return 0

    embedder = _make_embedder(embedding_model)
    documents = [c["content"] for c in all_chunks]
    embeddings = embedder(documents)

    collection.add(
        ids=[f"{c['document_id']}::{i}" for i, c in enumerate(all_chunks)],
        documents=documents,
        embeddings=embeddings,
        metadatas=[
            {"document_id": c["document_id"], "section_header": c["section_header"]}
            for c in all_chunks
        ],
    )
    return len(all_chunks)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _distance_to_score(distance: Optional[float]) -> float:
    if distance is None:
        return 0.0
    return max(0.0, 1.0 - float(distance))


def retrieve(query: str, index_path: str, top_k: int = 5) -> list[RAGChunk]:
    """Return the top-k chunks most similar to `query`."""
    import chromadb

    client = chromadb.PersistentClient(path=index_path)
    collection = client.get_collection(_COLLECTION_NAME)

    model_name = (collection.metadata or {}).get(_EMBEDDING_MODEL_METADATA_KEY, "")
    embedder = _make_embedder(model_name) if model_name else _make_embedder("")
    query_embedding = embedder([query])[0]

    raw: dict[str, Any] = collection.query(
        query_embeddings=[query_embedding], n_results=top_k
    )

    documents = (raw.get("documents") or [[]])[0]
    metadatas = (raw.get("metadatas") or [[]])[0]
    distances = (raw.get("distances") or [[None] * len(documents)])[0]

    return [
        RAGChunk(
            document_id=str(meta.get("document_id", "")),
            section_header=str(meta.get("section_header", "")),
            content=str(doc),
            relevance_score=_distance_to_score(dist),
        )
        for doc, meta, dist in zip(documents, metadatas, distances)
    ]
