"""Configurable text chunking module with overlap and metadata tracking."""
from typing import List, Dict, Any
from src.utils.logger import logger

class TextChunker:
    def __init__(self, chunk_size_words: int = 180, chunk_overlap_words: int = 40):
        if chunk_overlap_words >= chunk_size_words:
            raise ValueError("chunk_overlap_words must be strictly less than chunk_size_words")
        self.chunk_size = chunk_size_words
        self.chunk_overlap = chunk_overlap_words

    def chunk_document(self, doc_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Chunks a single document into overlapping word windows."""
        text = doc_dict.get("text", "")
        doc_name = doc_dict.get("document_name", "unknown")
        file_path = doc_dict.get("file_path", "")

        words = text.split()
        if not words:
            return []

        chunks = []
        start_idx = 0
        chunk_counter = 0

        while start_idx < len(words):
            end_idx = min(start_idx + self.chunk_size, len(words))
            chunk_words = words[start_idx:end_idx]
            chunk_content = " ".join(chunk_words).strip()

            if chunk_content:
                chunks.append({
                    "chunk_id": f"{doc_name}_chunk_{chunk_counter}",
                    "document_name": doc_name,
                    "file_path": file_path,
                    "chunk_index": chunk_counter,
                    "content": chunk_content,
                    "word_count": len(chunk_words),
                    "char_count": len(chunk_content)
                })
                chunk_counter += 1

            if end_idx >= len(words):
                break
            start_idx += (self.chunk_size - self.chunk_overlap)

        return chunks

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Chunks a collection of documents."""
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        logger.info(f"Generated {len(all_chunks)} chunks from {len(documents)} documents (chunk_size={self.chunk_size}, overlap={self.chunk_overlap}).")
        return all_chunks
