"""RAG Knowledge Base management and query endpoints."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Body
from src.api.dependencies import get_rag_pipeline
from src.rag.retrieval import RAGPipeline
from src.schemas.chat import RAGSourceRecord
from src.utils.config import settings

router = APIRouter(prefix="/rag", tags=["RAG Financial Knowledge"])

@router.post("/query", response_model=List[RAGSourceRecord], summary="Direct semantic query of knowledge base")
def query_knowledge_base(
    query: str = Body(..., embed=True, description="Financial education question"),
    top_k: int = Body(3, embed=True, ge=1, le=10),
    min_score: float = Body(0.20, embed=True, ge=0.0, le=1.0),
    rag: RAGPipeline = Depends(get_rag_pipeline)
):
    """Retrieves relevant knowledge base chunks using FAISS cosine similarity."""
    results = rag.retrieve(query=query, top_k=top_k, min_score=min_score)
    return rag.format_sources(results)

@router.post("/reindex", summary="Re-ingest and re-index all knowledge documents")
def reindex_knowledge_base(rag: RAGPipeline = Depends(get_rag_pipeline)):
    """Triggers document parsing, chunking, embedding generation, and FAISS index save."""
    result = rag.build_or_refresh_index()
    return {"message": "Knowledge base reindexed successfully", "details": result}

@router.get("/documents", summary="List indexed knowledge base documents")
def list_knowledge_documents():
    """Lists all financial education documents stored in the knowledge repository."""
    docs_dir = settings.DOCUMENTS_DIR
    files_info = []
    if docs_dir.exists():
        for fp in sorted(docs_dir.glob("*.txt")):
            try:
                content = fp.read_text(encoding="utf-8")
                # Grab title or first non-empty line
                lines = [l.strip("# ").strip() for l in content.split("\n") if l.strip()]
                title = lines[0] if lines else fp.name
                files_info.append({
                    "filename": fp.name,
                    "title": title,
                    "size_bytes": fp.stat().st_size,
                    "char_count": len(content),
                    "summary_snippet": content[:220] + "..." if len(content) > 220 else content
                })
            except Exception as e:
                files_info.append({"filename": fp.name, "error": str(e)})

    return {"total_documents": len(files_info), "documents": files_info}
