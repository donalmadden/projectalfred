"""
RAG engine over the handover corpus.

Phase 4 implementation will:
- Index handover documents at section boundaries
- Embed chunks using a configurable embedding model
- Retrieve relevant chunks by semantic similarity
"""
from alfred.schemas.agent import RAGChunk


def index_corpus(corpus_path: str, index_path: str, embedding_model: str) -> int:
    raise NotImplementedError


def retrieve(query: str, index_path: str, top_k: int = 5) -> list[RAGChunk]:
    raise NotImplementedError
