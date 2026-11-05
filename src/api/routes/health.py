"""Health check and system diagnostics endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.api.dependencies import get_db, get_rag_pipeline, get_orchestrator
from src.utils.config import settings

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("", summary="System Health & Diagnostic Status")
def get_health(
    db: Session = Depends(get_db),
    rag=Depends(get_rag_pipeline),
    orchestrator=Depends(get_orchestrator)
):
    """
    Returns live diagnostic information:
    - Database connectivity and transaction count
    - RAG index state and total indexed vectors
    - LLM operational mode (Live Gemini vs Mock/Demo)
    """
    # Test DB
    db_ok = False
    transaction_count = 0
    try:
        from src.database.models import Transaction
        transaction_count = db.query(Transaction).count()
        db_ok = True
    except Exception as e:
        db_error = str(e)

    # Test RAG
    rag_indexed = rag.vector_store.is_indexed()
    indexed_vectors = rag.vector_store.index.ntotal if rag.vector_store.index else 0

    # Test LLM
    is_live_llm = orchestrator.llm_client.is_live
    llm_mode = f"Live Gemini ({orchestrator.llm_client.model_name})" if is_live_llm else "Mock/Demo Mode (Offline Rule Synthesizer)"

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.VERSION,
        "database": {
            "connected": db_ok,
            "total_transactions": transaction_count,
            "database_url": settings.DATABASE_URL
        },
        "rag_pipeline": {
            "indexed": rag_indexed,
            "indexed_vectors": indexed_vectors,
            "embedding_model": settings.EMBEDDING_MODEL_NAME
        },
        "llm_engine": {
            "is_live": is_live_llm,
            "mode": llm_mode,
            "configured_model": orchestrator.llm_client.model_name
        }
    }
