"""Embedding generation service using SentenceTransformers."""
import os
from typing import List, Union
import numpy as np

# Set Hugging Face offline mode to avoid remote network lookups once cached
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from sentence_transformers import SentenceTransformer
from src.utils.config import settings
from src.utils.logger import logger

class EmbeddingService:
    _instance = None
    _model = None

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self._load_model()

    def _load_model(self):
        if EmbeddingService._model is None:
            logger.info(f"Loading SentenceTransformer model '{self.model_name}' (offline/local mode)...")
            try:
                # Try loading with local_files_only
                EmbeddingService._model = SentenceTransformer(self.model_name, local_files_only=True)
                dim = EmbeddingService._model.get_embedding_dimension() if hasattr(EmbeddingService._model, "get_embedding_dimension") else EmbeddingService._model.get_sentence_embedding_dimension()
                logger.info(f"Model '{self.model_name}' loaded from cache. Dimension: {dim}")
            except Exception as e_local:
                logger.warning(f"local_files_only load failed ({e_local}), attempting standard load...")
                try:
                    EmbeddingService._model = SentenceTransformer(self.model_name)
                except Exception as e:
                    logger.error(f"Failed to load embedding model: {e}")
                    raise e
        self.model = EmbeddingService._model

    @property
    def dimension(self) -> int:
        if hasattr(self.model, "get_embedding_dimension"):
            return self.model.get_embedding_dimension()
        return self.model.get_sentence_embedding_dimension()

    def generate_embeddings(self, texts: Union[str, List[str]]) -> np.ndarray:
        """
        Generates normalized float32 embeddings for a string or list of strings.
        Normalization ensures Inner Product equals Cosine Similarity.
        """
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.astype("float32")
