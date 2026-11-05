"""FAISS vector store index and metadata persistence."""
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import faiss
import numpy as np
from src.utils.config import settings
from src.utils.logger import logger

class VectorStore:
    def __init__(self, index_dir: Optional[Path] = None):
        self.index_dir = Path(index_dir or settings.VECTOR_INDEX_DIR)
        self.index_file = self.index_dir / "faiss_index.bin"
        self.metadata_file = self.index_dir / "chunks_metadata.json"
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []

    def is_indexed(self) -> bool:
        """Checks if both the FAISS index file and metadata exist on disk."""
        return self.index_file.exists() and self.metadata_file.exists()

    def build_index(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray):
        """Builds a new FAISS IndexFlatIP (cosine similarity) from normalized vectors."""
        if len(chunks) != len(embeddings):
            raise ValueError(f"Number of chunks ({len(chunks)}) does not match embeddings length ({len(embeddings)})")

        dim = embeddings.shape[1]
        logger.info(f"Building FAISS IndexFlatIP with dimension {dim} for {len(chunks)} vectors...")

        # faiss.IndexFlatIP with normalized vectors computes cosine similarity
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings)
        self.metadata = chunks
        logger.info(f"FAISS index built. Total indexed vectors: {self.index.ntotal}")

    def save(self):
        """Persists the FAISS index and chunk metadata to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        if self.index is None:
            raise ValueError("Cannot save an uninitialized FAISS index.")

        faiss.write_index(self.index, str(self.index_file.resolve()))
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved FAISS index ({self.index.ntotal} vectors) and metadata to {self.index_dir}")

    def load(self) -> bool:
        """Loads index and metadata from disk if available."""
        if not self.is_indexed():
            logger.warning(f"Vector index not found in {self.index_dir}")
            return False

        try:
            self.index = faiss.read_index(str(self.index_file.resolve()))
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors from {self.index_dir}")
            return True
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            return False

    def search(self, query_vector: np.ndarray, top_k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """
        Executes similarity search.
        Returns list of (chunk_metadata, cosine_similarity_score).
        """
        if self.index is None:
            if not self.load():
                return []

        if query_vector.ndim == 1:
            query_vector = np.expand_dims(query_vector, axis=0)

        # FAISS search returns distances (inner products) and indices
        k = min(top_k, self.index.ntotal)
        if k <= 0:
            return []

        scores, indices = self.index.search(query_vector.astype("float32"), k)

        results = []
        for rank in range(k):
            idx = int(indices[0][rank])
            score = float(scores[0][rank])
            if idx >= 0 and idx < len(self.metadata):
                results.append((self.metadata[idx], score))

        return results
