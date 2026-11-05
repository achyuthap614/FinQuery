"""Document ingestion and text preprocessing for financial knowledge base."""
from pathlib import Path
from typing import List, Dict, Any
from src.utils.logger import logger
import re

class DocumentIngestion:
    @staticmethod
    def clean_text(text: str) -> str:
        """Cleans and standardizes raw document text."""
        # Normalize newlines and whitespace
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse excessive consecutive spaces
        text = re.sub(r"[ \t]+", " ", text)
        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def load_documents_from_dir(cls, directory_path: Path) -> List[Dict[str, Any]]:
        """Loads all .txt and .md files from target directory."""
        documents = []
        dir_p = Path(directory_path)
        if not dir_p.exists() or not dir_p.is_dir():
            logger.warning(f"Documents directory '{directory_path}' does not exist.")
            return documents

        file_patterns = ["*.txt", "*.md"]
        file_paths = []
        for pat in file_patterns:
            file_paths.extend(dir_p.glob(pat))

        for fp in sorted(file_paths):
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    raw_content = f.read()
                cleaned = cls.clean_text(raw_content)
                if cleaned:
                    documents.append({
                        "document_name": fp.name,
                        "file_path": str(fp.resolve()),
                        "text": cleaned,
                        "char_count": len(cleaned)
                    })
                    logger.info(f"Loaded document '{fp.name}' ({len(cleaned)} chars).")
            except Exception as e:
                logger.error(f"Failed to load document {fp}: {e}")

        logger.info(f"Loaded {len(documents)} financial documents successfully.")
        return documents
