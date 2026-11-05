"""Chat and Conversational AI API route."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.api.dependencies import get_db, get_orchestrator
from src.llm.orchestrator import FinancialOrchestrator
from src.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["AI Conversational Assistant"])

@router.post("", response_model=ChatResponse, summary="Send natural language query to FinQuery assistant")
def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator: FinancialOrchestrator = Depends(get_orchestrator)
):
    """
    Processes natural language inquiries:
    1. Intelligently routes query to SQL tools, RAG knowledge, or Hybrid.
    2. Safely executes registered database tools if asking about transactions.
    3. Retrieves semantic knowledge chunks if asking financial questions.
    4. Formulates a grounded, evidence-backed response with citations.
    """
    return orchestrator.process_chat(request, db)
