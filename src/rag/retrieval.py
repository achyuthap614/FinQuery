"""RAG Retrieval Pipeline and Context Construction."""
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from src.rag.ingestion import DocumentIngestion
from src.rag.chunking import TextChunker
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStore
from src.schemas.chat import RAGSourceRecord
from src.utils.config import settings
from src.utils.logger import logger

class RAGPipeline:
    def __init__(
        self,
        documents_dir: Optional[Path] = None,
        vector_store_dir: Optional[Path] = None
    ):
        self.documents_dir = Path(documents_dir or settings.DOCUMENTS_DIR)
        self.vector_store = VectorStore(index_dir=vector_store_dir or settings.VECTOR_INDEX_DIR)
        self.embedding_service = EmbeddingService()
        self.chunker = TextChunker(
            chunk_size_words=settings.CHUNK_SIZE,
            chunk_overlap_words=settings.CHUNK_OVERLAP
        )

        # Attempt to load existing index on startup
        if self.vector_store.is_indexed():
            self.vector_store.load()

    def build_or_refresh_index(self) -> Dict[str, Any]:
        """Ingests all raw documents, generates chunk embeddings, and builds FAISS index."""
        logger.info("Starting knowledge base indexing pipeline...")
        docs = DocumentIngestion.load_documents_from_dir(self.documents_dir)
        if not docs:
            logger.warning("No documents found to index.")
            return {"status": "empty", "documents_count": 0, "chunks_count": 0}

        chunks = self.chunker.chunk_documents(docs)
        if not chunks:
            return {"status": "no_chunks", "documents_count": len(docs), "chunks_count": 0}

        chunk_texts = [c["content"] for c in chunks]
        embeddings = self.embedding_service.generate_embeddings(chunk_texts)

        self.vector_store.build_index(chunks, embeddings)
        self.vector_store.save()

        return {
            "status": "success",
            "documents_count": len(docs),
            "chunks_count": len(chunks),
            "vector_dimension": embeddings.shape[1]
        }

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        min_score: float = 0.20
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Encodes query string, retrieves top_k nearest chunks, and filters by similarity score.
        """
        k = top_k or settings.RAG_TOP_K
        if not self.vector_store.index:
            if not self.vector_store.load():
                # Attempt to build if not exists
                self.build_or_refresh_index()

        query_emb = self.embedding_service.generate_embeddings(query)
        results = self.vector_store.search(query_emb, top_k=k)

        # Filter by minimum cosine similarity threshold
        filtered = [(chunk, score) for chunk, score in results if score >= min_score]
        return filtered

    @staticmethod
    def format_sources(retrieved_items: List[Tuple[Dict[str, Any], float]]) -> List[RAGSourceRecord]:
        """Converts raw retrieved items into standard RAGSourceRecord schema."""
        records = []
        for chunk, score in retrieved_items:
            records.append(RAGSourceRecord(
                document_name=chunk.get("document_name", "unknown"),
                chunk_index=chunk.get("chunk_index", 0),
                content=chunk.get("content", ""),
                similarity_score=round(float(score), 4)
            ))
        return records

    @staticmethod
    def build_context_prompt(retrieved_items: List[Tuple[Dict[str, Any], float]]) -> str:
        """Formats retrieved chunks into evidence blocks for LLM prompt context."""
        if not retrieved_items:
            return "No relevant financial knowledge documents found."

        context_blocks = []
        for i, (chunk, score) in enumerate(retrieved_items, start=1):
            doc = chunk.get("document_name", "Unknown Document")
            chunk_idx = chunk.get("chunk_index", 0)
            text = chunk.get("content", "")
            context_blocks.append(
                f"[Document Source {i}: {doc} (Chunk {chunk_idx}, Similarity: {score:.2f})]\n{text}"
            )
        return "\n\n---\n\n".join(context_blocks)

    @staticmethod
    def is_context_sufficient(retrieved_items: List[Tuple[Dict[str, Any], float]], threshold: float = 0.30) -> bool:
        """Determines if the top retrieved chunk meets the confidence threshold."""
        if not retrieved_items:
            return False
        top_score = retrieved_items[0][1]
        return top_score >= threshold
