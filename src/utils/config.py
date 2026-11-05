"""Application configuration module."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if available
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "FinQuery — AI Financial Data Assistant"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DOCUMENTS_DIR: Path = BASE_DIR / "documents" / "financial_knowledge"
    VECTOR_INDEX_DIR: Path = BASE_DIR / "data" / "vector_store"
    DATABASE_PATH: Path = DATA_DIR / "finquery.db"
    TRANSACTIONS_CSV_PATH: Path = DATA_DIR / "transactions.csv"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}")

    # Gemini LLM
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # RAG Settings
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "350"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))

    # API Server
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")

    @classmethod
    def ensure_directories(cls):
        """Ensures that runtime directories exist."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        cls.VECTOR_INDEX_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
