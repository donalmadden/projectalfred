"""Tests for the RAG indexing + retrieval tool."""
from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from alfred.tools import rag


def _hash_vector(text: str, dim: int = 32) -> list[float]:
    """Deterministic low-dim embedding: bucket bytes of sha256 into `dim` slots."""
    digest = hashlib.sha256(text.lower().encode("utf-8")).digest()
    vec = [0.0] * dim
    for i, b in enumerate(digest):
        vec[i % dim] += float(b)
    # L2 normalize
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _fake_embedder_factory(model_name: str):
    def embed(texts: list[str]) -> list[list[float]]:
        return [_hash_vector(t) for t in texts]

    return embed


@pytest.fixture(autouse=True)
def _install_fake_embedder():
    original = rag._embedder_factory
    rag.set_embedder(_fake_embedder_factory)
    yield
    rag.set_embedder(original)


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "doc_alpha.md").write_text(
        "# Title\n\n"
        "## Context\n\nAlpha introduces the widget refactor and its motivation.\n\n"
        "## Decisions\n\nAlpha decided to deprecate the legacy adapter.\n"
    )
    (root / "doc_beta.md").write_text(
        "# Title\n\n"
        "## Post-Mortem\n\nBeta recounts the deployment incident and root cause.\n\n"
        "## Forward Plan\n\nBeta proposes rollout gates for the next release.\n"
    )
    return root


def test_chunk_splits_at_level_two_headers() -> None:
    text = (
        "preamble line\n\n"
        "## First\ncontent one\n\n"
        "## Second\ncontent two\n"
    )
    chunks = rag._chunk_markdown(text, "doc_x")
    assert [c["section_header"] for c in chunks] == ["PREAMBLE", "First", "Second"]
    assert all(c["document_id"] == "doc_x" for c in chunks)
    assert "content one" in chunks[1]["content"]


def test_chunk_handles_no_headers() -> None:
    chunks = rag._chunk_markdown("just a paragraph", "doc_y")
    assert len(chunks) == 1
    assert chunks[0]["section_header"] == "PREAMBLE"


def test_index_corpus_returns_chunk_count(corpus: Path, tmp_path: Path) -> None:
    index_path = str(tmp_path / "index")
    n = rag.index_corpus(str(corpus), index_path, embedding_model="fake-model")
    assert n == 6  # 2 docs × (1 preamble + 2 sections)


def test_retrieve_returns_top_k_ordered(corpus: Path, tmp_path: Path) -> None:
    index_path = str(tmp_path / "index")
    rag.index_corpus(str(corpus), index_path, embedding_model="fake-model")

    results = rag.retrieve(
        "Alpha decided to deprecate the legacy adapter.",
        index_path,
        top_k=2,
    )
    assert len(results) == 2
    assert all(r.document_id for r in results)
    # The exact-match chunk should be the top hit.
    assert "deprecate" in results[0].content
    assert results[0].relevance_score >= results[1].relevance_score


def test_retrieve_respects_top_k(corpus: Path, tmp_path: Path) -> None:
    index_path = str(tmp_path / "index")
    rag.index_corpus(str(corpus), index_path, embedding_model="fake-model")
    results = rag.retrieve("anything", index_path, top_k=3)
    assert len(results) <= 3


def test_index_is_rebuilt_on_reindex(corpus: Path, tmp_path: Path) -> None:
    index_path = str(tmp_path / "index")
    rag.index_corpus(str(corpus), index_path, embedding_model="fake-model")
    n2 = rag.index_corpus(str(corpus), index_path, embedding_model="fake-model")
    assert n2 == 6  # still 6 — collection was dropped and rebuilt, not appended
