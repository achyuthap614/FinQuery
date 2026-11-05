"""Pydantic schemas for Chat, Tool Execution, and RAG interactions."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message author role: 'user', 'assistant', 'system'")
    content: str = Field(..., description="Message textual content")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's natural language financial query", json_schema_extra={"example": "How much did I spend on food this month?"})
    conversation_id: Optional[str] = Field("default", description="Session identifier for multi-turn chat")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Recent conversation history")

class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None

class RAGSourceRecord(BaseModel):
    document_name: str
    chunk_index: int
    content: str
    similarity_score: float

class RoutingDecision(BaseModel):
    route: str = Field(..., description="'sql_tool', 'rag_knowledge', 'hybrid', or 'direct_conversation'")
    confidence: float
    reason: str
    identified_intent: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    routing: RoutingDecision
    tools_called: List[ToolCallRecord] = []
    rag_sources: List[RAGSourceRecord] = []
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Verified numerical or document evidence")
    model_used: str = "mock-rule-orchestrator"
