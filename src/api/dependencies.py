"""FastAPI dependencies module."""
from typing import Generator
from sqlalchemy.orm import Session
from src.database.database import SessionLocal
from src.llm.orchestrator import FinancialOrchestrator
from src.llm.client import GeminiClient
from src.rag.retrieval import RAGPipeline

# Singletons for memory efficiency
_rag_pipeline_instance = None
_orchestrator_instance = None

def get_db() -> Generator[Session, None, None]:
    """Provides a thread-safe database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_rag_pipeline() -> RAGPipeline:
    """Provides or initializes the shared RAGPipeline instance."""
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = RAGPipeline()
    return _rag_pipeline_instance

def get_orchestrator() -> FinancialOrchestrator:
    """Provides or initializes the FinancialOrchestrator instance."""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        rag = get_rag_pipeline()
        client = GeminiClient()
        _orchestrator_instance = FinancialOrchestrator(gemini_client=client, rag_pipeline=rag)
    return _orchestrator_instance
