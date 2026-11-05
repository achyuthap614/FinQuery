# FinQuery — AI Financial Data Assistant 💎

FinQuery is a production-grade, portfolio-quality AI financial assistant that empowers users to query their personal financial transactions and explore financial literacy principles using natural language.

Designed with a clean, decoupled architecture, FinQuery distinguishes between:
1. **SQL-based Retrieval & Tool Calling:** Computes verified calculations (spending, income, net balance, top expenses, month-over-month comparisons, statistical anomaly detection) directly from SQLite with strict anti-hallucination guarantees.
2. **Retrieval-Augmented Generation (RAG):** Answers financial literacy questions (compound interest, ETFs vs mutual funds, 50/30/20 budgeting, emergency funds, debt snowball vs avalanche, inflation, retirement accounts) using a local FAISS vector store and Sentence Transformers (`all-MiniLM-L6-v2`).
3. **Intelligent Router & LLM Integration:** Powered by Google's official `google-genai` SDK with an automatic fallback mock engine for testing and offline environments.

---

## 🌟 Key Features

* **Strict Anti-Hallucination Guardrails:** The LLM never invents numbers. All transaction metrics come from database execution evidence with verifiable calculation trails.
* **Security-First Tool Calling:** No arbitrary SQL or Python execution. Tools are strictly registered with Pydantic schema validation.
* **Intelligent Query Routing:** Automatically determines whether an inquiry requires a database tool (`sql_tool`), knowledge retrieval (`rag_knowledge`), both (`hybrid`), or general conversation (`direct_conversation`).
* **Statistical Anomaly Detection:** Identifies unusually high spending using transparent sample standard deviations and Z-scores per category, avoiding opaque buzzwords.
* **Self-Contained Local RAG:** FAISS vector store with offline cached embeddings (`all-MiniLM-L6-v2`), complete with chunking, overlap, and document citations.
* **Enterprise Dashboard:** Built with Streamlit and Plotly, featuring interactive KPI cards, monthly trend graphs, category donut charts, anomaly explorers, statement uploaders, and live chat with tool transparency.

---

## 🏗️ Technology Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.11+) | Async REST API, OpenAPI/Swagger docs, dependency injection |
| **Database & ORM** | SQLite + SQLAlchemy 2.0 | Persistent relational storage for financial records |
| **Data Validation** | Pydantic v2 | Strict schema validation, sanitization, and type safety |
| **Data Processing** | Pandas & NumPy | Vector normalization and data manipulations |
| **LLM & Tool Calling**| Gemini 2.5 Flash (`google-genai`) | Natural language understanding and response synthesis |
| **Vector Store** | FAISS (`faiss-cpu`) | High-performance cosine similarity vector search |
| **Embeddings** | Sentence Transformers (`all-MiniLM-L6-v2`) | Semantic text representation (384-dimensional vectors) |
| **Frontend** | Streamlit + Plotly | Interactive modern analytics dashboard and AI chat interface |
| **Testing** | Pytest + FastAPI TestClient | 39 automated unit, integration, and security tests |
| **Containerization** | Docker & Docker Compose | Multi-container reproducible deployment |

---

## 📁 Repository Structure

```text
FinQuery/
├── data/
│   ├── transactions.csv             # Seed dataset (200+ realistic transactions)
│   ├── finquery.db                  # SQLite database
│   └── vector_store/                # FAISS vector index & metadata
│       ├── faiss_index.bin
│       └── chunks_metadata.json
├── documents/
│   └── financial_knowledge/         # Vetted financial education documents
│       ├── budgeting_methods.txt
│       ├── compound_interest.txt
│       ├── debt_management_strategies.txt
│       ├── emergency_funds.txt
│       ├── inflation_and_purchasing_power.txt
│       ├── mutual_funds_vs_etfs.txt
│       └── retirement_accounts.txt
├── src/
│   ├── api/                         # FastAPI routes and dependencies
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── transactions.py
│   │       ├── analytics.py
│   │       ├── chat.py
│   │       └── rag.py
│   ├── database/                    # SQLAlchemy models & connection
│   │   ├── database.py
│   │   └── models.py
│   ├── schemas/                     # Pydantic v2 request/response schemas
│   │   ├── transaction.py
│   │   ├── analytics.py
│   │   └── chat.py
│   ├── services/                    # Core business logic
│   │   ├── transaction_service.py
│   │   └── analytics_service.py
│   ├── tools/                       # Safe registered financial tools
│   │   └── financial_tools.py
│   ├── rag/                         # Ingestion, chunking, embeddings, FAISS
│   │   ├── ingestion.py
│   │   ├── chunking.py
│   │   ├── embeddings.py
│   │   ├── vector_store.py
│   │   └── retrieval.py
│   ├── llm/                         # Gemini SDK client, prompts & orchestrator
│   │   ├── client.py
│   │   ├── prompts.py
│   │   └── orchestrator.py
│   └── utils/                       # Configuration & logging
│       ├── config.py
│       └── logger.py
├── frontend/
│   └── app.py                       # Streamlit UI dashboard & AI chat
├── tests/                           # 39 Pytest automated tests
│   ├── conftest.py
│   ├── test_transactions.py
│   ├── test_analytics.py
│   ├── test_tools.py
│   ├── test_rag.py
│   ├── test_routing.py
│   └── test_api.py
├── scripts/
│   ├── seed_data.py                 # Generates synthetic data and seeds DB
│   └── build_rag_index.py           # Ingests documents and builds FAISS index
├── main.py                          # FastAPI server entry point
├── requirements.txt                 # Pinned dependencies
├── .env.example                     # Sample environment configuration
├── Dockerfile                       # Multi-stage container definition
├── docker-compose.yml               # Service orchestration
├── ARCHITECTURE.md                  # Detailed architectural design & flowcharts
└── INTERVIEW_PREPARATION.md         # Comprehensive MCA & interview Q&A guide
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
* Python 3.11 or higher
* Git

### 2. Clone and Setup Environment
```bash
git clone https://github.com/your-username/FinQuery.git
cd FinQuery

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optional)* Add your Gemini API key from [Google AI Studio](https://aistudio.google.com/):
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
> **Note:** If `GEMINI_API_KEY` is not provided, FinQuery automatically runs in its deterministic **Mock/Demo Mode**, allowing complete offline testing and demonstration!

### 4. Seed Database & Build Vector Store
```bash
# Seed 200+ realistic synthetic transactions into SQLite
PYTHONPATH=. python scripts/seed_data.py

# Ingest educational documents and build the FAISS vector index
PYTHONPATH=. python scripts/build_rag_index.py
```

### 5. Run the Application
Open two terminal windows:

**Terminal 1 — Backend (FastAPI):**
```bash
PYTHONPATH=. uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive Swagger docs will be live at: [http://localhost:8000/docs](http://localhost:8000/docs)

**Terminal 2 — Frontend (Streamlit):**
```bash
streamlit run frontend/app.py --server.port 8501
```
Open your browser at: [http://localhost:8501](http://localhost:8501)

---

## 🐳 Docker Deployment

Run both backend and frontend with Docker Compose:
```bash
docker-compose up --build
```
* Backend API: `http://localhost:8000`
* Streamlit UI: `http://localhost:8501`

---

## 🧪 Running Automated Tests

Run the complete 39-test suite:
```bash
PYTHONPATH=. pytest -v tests/
```
All 39 unit and integration tests execute with zero external network dependencies in under 5 seconds!

---

## 💬 Demonstration Workflow for Interviews

1. **System Health:** Open [http://localhost:8000/api/health](http://localhost:8000/api/health) to show that SQLite, FAISS vectors, and LLM routes are initialized.
2. **Executive Dashboard:** Navigate to `http://localhost:8501` to view live KPI metric cards (Total Income: $36,622.84, Total Expenses: $28,071.20, Net Balance: $8,551.64, Savings Rate: 23.4%) and Plotly charts.
3. **Transaction Tool Calling:** In the AI Assistant tab, ask:
   * *"How much did I spend on Groceries?"* ➔ Shows routing to `SQL_TOOL`, executes `get_category_spending`, returns $6,666.60 across 54 transactions with database evidence.
   * *"Show my top five expenses."* ➔ Shows routing to `SQL_TOOL`, executes `get_largest_transactions`, returns the $2,350 MacBook and $1,650 rent records.
4. **Statistical Anomaly Detection:** Ask:
   * *"Is my spending unusually high compared with previous months?"* ➔ Flags 6 outliers with exact Z-scores (e.g., $745 anniversary banquet dinner at 15.89x category average).
5. **RAG Knowledge Retrieval:** Ask:
   * *"What is compound interest and the rule of 72?"* ➔ Shows routing to `RAG_KNOWLEDGE`, retrieves chunks from `compound_interest.txt`, provides mathematical formulation.
   * *"Explain the difference between mutual funds and ETFs."* ➔ Retrieves `mutual_funds_vs_etfs.txt` with similarity scores.
6. **Hybrid Query:** Ask:
   * *"How much did I spend on dining, and explain the 50/30/20 budgeting rule?"* ➔ Shows routing to `HYBRID`, executes SQL tool for dining ($3,890.34) and retrieves RAG context from `budgeting_methods.txt`.
7. **Missing Evidence Safety:** Ask:
   * *"What are quantum chromodynamics black holes?"* ➔ Demonstrates refusal to hallucinate, explicitly stating that supporting evidence is absent from the knowledge base.

---

## 🔒 Security & Privacy

* **Read-Only Analytics:** FinQuery is an educational prototype and does not initiate payments, bank connections, or money transfers.
* **No Arbitrary SQL/Code:** The LLM cannot execute raw SQL or Python. It interacts only through registered, Pydantic-validated tool functions.
* **Data Sanitization:** CSV imports are validated against regex date formats and numeric amounts, blocking malformed rows and preventing SQL injections.
* **Duplicate Detection:** Transactions compute a SHA-256 fingerprint from `(date, amount, category, description, type)` to prevent duplicate entries.
* **Credential Hygiene:** API keys are loaded via environment variables and excluded from Git commits via `.gitignore`.
