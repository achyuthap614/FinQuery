"""FinQuery FastAPI Application Entry Point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from src.database.database import init_db
from src.rag.retrieval import RAGPipeline
from src.api.routes import health, transactions, analytics, chat, rag
from src.utils.config import settings
from src.utils.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle handler."""
    logger.info("Initializing FinQuery backend application...")
    # 1. Initialize SQLite tables
    init_db()

    # 2. Verify or build RAG index
    rag_pipeline = RAGPipeline()
    if not rag_pipeline.vector_store.is_indexed():
        logger.info("RAG vector index not found on startup. Triggering initial build...")
        rag_pipeline.build_or_refresh_index()
    else:
        logger.info("RAG vector index verified on disk.")

    logger.info(f"FinQuery Backend ready on {settings.API_HOST}:{settings.API_PORT}")
    yield
    logger.info("Shutting down FinQuery backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    **FinQuery** is an AI-powered financial data assistant that provides accurate, evidence-backed
    answers to natural language queries about financial transactions and financial education.

    ### Key Capabilities:
    * **SQL-based Retrieval:** Query verified personal transactions, spending trends, and statistical anomaly detection.
    * **RAG-based Retrieval:** Semantic vector search across verified financial knowledge base documents using FAISS and Sentence Transformers.
    * **LLM Tool Calling:** Safe execution of strictly whitelisted financial tools with Pydantic validation (No arbitrary code or SQL).
    * **Deterministic Anti-Hallucination:** Answers grounded in verified database calculations with transparent evidence trails.
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Streamlit frontend and local clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(rag.router, prefix="/api")

@app.get("/", include_in_schema=False)
def root():
    """Redirect root path to interactive Swagger documentation."""
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
