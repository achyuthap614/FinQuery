"""Tests for RAG pipeline, ingestion, chunking, embeddings, and vector retrieval."""
import pytest
from pathlib import Path
from src.rag.ingestion import DocumentIngestion
from src.rag.chunking import TextChunker
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore
from src.rag.retrieval import RAGPipeline
from src.utils.config import settings

def test_document_ingestion():
    docs = DocumentIngestion.load_documents_from_dir(settings.DOCUMENTS_DIR)
    assert len(docs) >= 5
    for d in docs:
        assert "document_name" in d
        assert "text" in d
        assert len(d["text"]) > 100

def test_text_chunking():
    chunker = TextChunker(chunk_size_words=50, chunk_overlap_words=10)
    sample_doc = {
        "document_name": "test_doc.txt",
        "file_path": "/fake/path/test_doc.txt",
        "text": " ".join([f"word{i}" for i in range(120)])
    }
    chunks = chunker.chunk_document(sample_doc)
    assert len(chunks) == 3
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["word_count"] == 50
    # Next chunk starts at 40 (50 - 10)
    assert "word40" in chunks[1]["content"]

def test_embeddings_generation():
    service = EmbeddingService()
    text = "What is compound interest and the rule of 72?"
    emb = service.generate_embeddings(text)
    assert emb.shape == (1, service.dimension)
    assert emb.dtype == "float32"

def test_rag_retrieval_relevance():
    pipeline = RAGPipeline()
    # Query about compound interest
    results = pipeline.retrieve("Explain compound interest and the formula", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "compound_interest" in top_chunk["document_name"].lower()
    assert score > 0.40  # High semantic cosine similarity

def test_rag_retrieval_etf_vs_mutual_funds():
    pipeline = RAGPipeline()
    results = pipeline.retrieve("What is the difference between an ETF and a mutual fund?", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert "mutual_funds_vs_etfs" in top_chunk["document_name"].lower()
    assert score > 0.40

def test_insufficient_context_detection():
    # If a query is completely unrelated to personal finance, score should be low
    pipeline = RAGPipeline()
    results = pipeline.retrieve("Quantum chromodynamics quark gluon plasma", top_k=1, min_score=0.85)
    assert len(results) == 0  # Below strict threshold
