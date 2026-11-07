"""FinQuery — AI Financial Data Assistant
Streamlit Frontend Application.
"""
import io
import os
import re
from pathlib import Path
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# Application Configuration & Theming
# ==========================================
st.set_page_config(
    page_title="FinQuery — AI Financial Data Assistant",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Base URL (configured via environment or defaults to local backend)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Custom CSS for modern financial analytics aesthetic
st.markdown("""
<style>
    /* Main container styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2.5rem;
    }

    /* Top Navigation Tabs Container - shifted down by ~25px to clear header and prevent top clipping */
    div[data-testid="stTabs"],
    .stTabs {
        margin-top: 25px;
    }
    
    /* Metric Cards */
    .kpi-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        margin-bottom: 1rem;
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #888888;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #00C853;
    }
    
    /* Routing Badges */
    .badge-sql {
        background-color: #1565C0;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-rag {
        background-color: #6A1B9A;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-hybrid {
        background-color: #E65100;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-direct {
        background-color: #37474F;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    /* Chat Message Typography & Heading Hierarchy */
    [data-testid="stChatMessage"] h1,
    .stChatMessage h1 {
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        line-height: 1.35 !important;
        margin-top: 0.75rem !important;
        margin-bottom: 0.35rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] h2,
    .stChatMessage h2 {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
        margin-top: 0.65rem !important;
        margin-bottom: 0.3rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] h3,
    .stChatMessage h3 {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
        margin-top: 0.55rem !important;
        margin-bottom: 0.25rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5,
    [data-testid="stChatMessage"] h6,
    .stChatMessage h4,
    .stChatMessage h5,
    .stChatMessage h6 {
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
        margin-top: 0.45rem !important;
        margin-bottom: 0.2rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] p,
    .stChatMessage p {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
        font-weight: 400 !important;
        margin-top: 0 !important;
        margin-bottom: 0.5rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] li,
    .stChatMessage li {
        font-size: 0.95rem !important;
        line-height: 1.55 !important;
        font-weight: 400 !important;
        margin-bottom: 0.25rem !important;
        color: inherit !important;
    }
    
    [data-testid="stChatMessage"] ul,
    [data-testid="stChatMessage"] ol,
    .stChatMessage ul,
    .stChatMessage ol {
        margin-top: 0.25rem !important;
        margin-bottom: 0.5rem !important;
        padding-left: 1.25rem !important;
    }

    [data-testid="stChatMessage"] strong,
    .stChatMessage strong {
        font-weight: 600 !important;
    }

    [data-testid="stChatMessage"] hr,
    .stChatMessage hr {
        margin: 0.8rem 0 !important;
        border-color: rgba(128, 128, 128, 0.25) !important;
    }

    [data-testid="stChatMessage"] code,
    .stChatMessage code {
        font-size: 0.85rem !important;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Markdown Formatting & Typography Helper
# ==========================================
def _load_known_headings():
    headings = []
    docs_dir = Path("documents/financial_knowledge")
    if docs_dir.exists():
        for f in docs_dir.glob("*.txt"):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    if line.startswith("#"):
                        headings.append(line.strip())
            except Exception:
                pass
    headings.sort(key=len, reverse=True)
    return headings

KNOWN_HEADINGS = _load_known_headings()

def format_chat_markdown(text: str) -> str:
    """
    Cleans and structures Markdown responses:
    - Separates document headings from body paragraphs so an entire response is never inside an <h1> or <h2>.
    - Formats inline subheadings, bullet points, and numbered lists.
    - Preserves already well-formed Markdown responses (e.g. SQL tool analytics, greetings, normal paragraphs).
    """
    if not text:
        return ""
        
    has_section_header = "### 📚 Financial Knowledge Explanation" in text or "## 📖 Financial Knowledge Concept" in text
    
    # 1. Format known headings with proper surrounding newlines and nested hierarchy
    for h in KNOWN_HEADINGS:
        pattern = re.escape(h) + r'(?:\s+|\n+|$)'
        target_h = h
        if has_section_header:
            if h.startswith("## "):
                target_h = "#### " + h[3:]
            elif h.startswith("# "):
                target_h = "### " + h[2:]
        text = re.sub(pattern, f"\n\n{target_h}\n\n", text)
        
    # 2. Format any remaining inline headings (e.g. ' ## Some Heading ')
    def inline_heading_repl(m):
        h_str = m.group(1)
        if has_section_header and h_str.startswith("## "):
            h_str = "#### " + h_str[3:]
        return f"\n\n{h_str}\n\n"
    text = re.sub(r'(?<=\S)\s+(#{1,6}\s+[^\n]+)', inline_heading_repl, text)
    
    # 3. Format inline bullet points (e.g. ' - A = ...' or ' - 50% for Needs: ...')
    text = re.sub(r'(?<=\S)\s+-\s+([A-Za-z0-9%\"\'\`\(\$])', r'\n- \1', text)
    
    # 4. Format inline numbered lists (e.g. ' 1. Item ... 2. Item ...')
    text = re.sub(r'(?<=[.:;!?\)])\s+(\d+\.\s+[A-Za-z\"\'\`])', r'\n\1', text)
    
    # 5. Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    
    # 6. Safety guard: ensure no heading line contains an entire paragraph (> 75 chars without newline)
    lines = text.split('\n')
    cleaned_lines = []
    for l in lines:
        m = re.match(r'^(#{1,6})\s+(.*)$', l)
        if m and len(m.group(2)) > 75:
            hashes = m.group(1)
            content = m.group(2)
            punct_match = re.search(r'[:.!?]\s+', content[:75])
            if punct_match:
                split_pt = punct_match.end()
                cleaned_lines.append(f"{hashes} {content[:split_pt].strip()}")
                cleaned_lines.append("")
                cleaned_lines.append(content[split_pt:].strip())
            else:
                w = content.split()
                if len(w) > 7:
                    cleaned_lines.append(f"{hashes} {' '.join(w[:5])}")
                    cleaned_lines.append("")
                    cleaned_lines.append(' '.join(w[5:]))
                else:
                    cleaned_lines.append(l)
        else:
            cleaned_lines.append(l)
            
    return '\n'.join(cleaned_lines)


# ==========================================
# Backend API Communication Utilities
# ==========================================
@st.cache_data(ttl=5)
def fetch_health():
    try:
        res = requests.get(f"{API_BASE_URL}/api/health", timeout=3)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=5)
def fetch_summary():
    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/summary", timeout=5)
        return res.json() if res.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=5)
def fetch_categories():
    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/categories", timeout=5)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

@st.cache_data(ttl=5)
def fetch_monthly_trends():
    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/monthly", timeout=5)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

@st.cache_data(ttl=5)
def fetch_largest_expenses(limit=5):
    try:
        res = requests.get(f"{API_BASE_URL}/api/analytics/largest?limit={limit}&transaction_type=expense", timeout=5)
        return res.json() if res.status_code == 200 else []
    except Exception:
        return []

def send_chat_query(message: str):
    try:
        payload = {"message": message}
        res = requests.post(f"{API_BASE_URL}/api/chat", json=payload, timeout=20)
        return res.json() if res.status_code == 200 else {"error": res.text}
    except Exception as e:
        return {"error": f"Failed to connect to backend API: {str(e)}"}


# ==========================================
# Sidebar: System Status & Controls
# ==========================================
with st.sidebar:
    st.title("💎 FinQuery")
    st.caption("AI-Powered Financial Data Assistant")
    st.divider()

    health_info = fetch_health()
    if health_info:
        st.success("🟢 Backend Connected", icon="✅")
        st.markdown(f"**Database:** {health_info['database']['total_transactions']} records")
        st.markdown(f"**RAG Vectors:** {health_info['rag_pipeline']['indexed_vectors']} vectors")
        st.markdown(f"**LLM Mode:** `{health_info['llm_engine']['mode']}`")
    else:
        st.error("🔴 Backend Disconnected\nEnsure FastAPI is running on port 8000.")

    st.divider()
    st.subheader("⚙️ Settings")
    api_url_input = st.text_input("Backend API URL", value=API_BASE_URL)
    if api_url_input != API_BASE_URL:
        API_BASE_URL = api_url_input
        st.rerun()

    st.caption("FinQuery is an educational prototype. Numerical values come from verified SQLite transactions.")


# ==========================================
# Main Application Tabs
# ==========================================
tab_dashboard, tab_chat, tab_transactions, tab_upload, tab_analytics, tab_knowledge = st.tabs([
    "📊 Executive Dashboard",
    "💬 AI Assistant",
    "💳 Transactions",
    "📤 Upload Statement",
    "🔍 Deep Analytics",
    "📚 Knowledge Base (RAG)"
])


# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_dashboard:
    st.title("Executive Financial Overview")
    summary = fetch_summary()

    if summary:
        # Top KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="Total Income",
                value=f"${summary['total_income']:,.2f}",
                delta=f"{summary['total_transactions']} txns"
            )
        with col2:
            st.metric(
                label="Total Expenses",
                value=f"${summary['total_expenses']:,.2f}",
                delta="-Outflows",
                delta_color="inverse"
            )
        with col3:
            net_val = summary['net_balance']
            delta_color = "normal" if net_val >= 0 else "inverse"
            st.metric(
                label="Net Balance",
                value=f"${net_val:,.2f}",
                delta="Surplus" if net_val >= 0 else "Deficit",
                delta_color=delta_color
            )
        with col4:
            st.metric(
                label="Savings Rate",
                value=f"{summary['savings_rate_percent']:.1f}%",
                delta="Target: >20%"
            )

        st.divider()

        # Visualizations Row
        col_charts_left, col_charts_right = st.columns([3, 2])

        # Monthly Income vs Expenses Trend
        with col_charts_left:
            st.subheader("📈 Monthly Income vs. Expenses")
            monthly_data = fetch_monthly_trends()
            if monthly_data:
                df_monthly = pd.DataFrame(monthly_data)
                fig_monthly = go.Figure()
                fig_monthly.add_trace(go.Bar(
                    x=df_monthly['month'],
                    y=df_monthly['income'],
                    name='Income',
                    marker_color='#00C853'
                ))
                fig_monthly.add_trace(go.Bar(
                    x=df_monthly['month'],
                    y=df_monthly['expenses'],
                    name='Expenses',
                    marker_color='#E53935'
                ))
                fig_monthly.add_trace(go.Scatter(
                    x=df_monthly['month'],
                    y=df_monthly['net'],
                    name='Net Balance',
                    mode='lines+markers',
                    line=dict(color='#2196F3', width=3)
                ))
                fig_monthly.update_layout(
                    barmode='group',
                    xaxis_title="Month",
                    yaxis_title="Amount ($USD)",
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_monthly, use_container_width=True)
            else:
                st.info("No monthly trend data available.")

        # Category Breakdown Donut Chart
        with col_charts_right:
            st.subheader("🏷️ Category Spending Breakdown")
            cat_data = fetch_categories()
            if cat_data:
                df_cat = pd.DataFrame(cat_data)
                fig_cat = px.pie(
                    df_cat,
                    names='category',
                    values='total_amount',
                    hole=0.45,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_cat.update_traces(textposition='inside', textinfo='percent+label')
                fig_cat.update_layout(
                    showlegend=False,
                    margin=dict(l=20, r=20, t=30, b=20)
                )
                st.plotly_chart(fig_cat, use_container_width=True)
            else:
                st.info("No category data available.")

        # Largest Expenses Table
        st.divider()
        st.subheader("🔝 Top 5 Largest Expenses")
        largest = fetch_largest_expenses(limit=5)
        if largest:
            df_largest = pd.DataFrame(largest)[["date", "amount", "category", "description", "payment_method"]]
            df_largest["amount"] = df_largest["amount"].apply(lambda x: f"${x:,.2f}")
            df_largest.columns = ["Date", "Amount", "Category", "Description", "Payment Method"]
            st.dataframe(df_largest, use_container_width=True, hide_index=True)

    else:
        st.warning("⚠️ No financial data loaded. Please upload a CSV in the 'Upload Statement' tab.")


# ==========================================
# TAB 2: AI FINANCIAL ASSISTANT (CHAT)
# ==========================================
with tab_chat:
    st.title("FinQuery Conversational Assistant")
    st.markdown("Ask anything about your personal transaction records or general financial principles.")

    # Initialize chat session history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 **Hello! I am FinQuery, your AI Financial Data Assistant.**\n\nI can analyze your transactions with database tools, or explain personal finance concepts using our verified knowledge base. Try one of the suggested prompts below or type your own question!",
                "metadata": None
            }
        ]

    # Quick Prompt Chips
    st.markdown("**Sample Inquiries:**")
    prompt_cols = st.columns(3)
    sample_prompts = [
        "How much did I spend on Groceries?",
        "What is my total income and net balance?",
        "Show my top 5 largest expenses.",
        "Is my spending unusually high?",
        "What is compound interest and the rule of 72?",
        "How much did I spend on dining, and explain the 50/30/20 rule?"
    ]
    
    clicked_prompt = None
    for idx, prompt_text in enumerate(sample_prompts):
        col_idx = idx % 3
        with prompt_cols[col_idx]:
            if st.button(prompt_text, key=f"btn_prompt_{idx}", use_container_width=True):
                clicked_prompt = prompt_text

    st.divider()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(format_chat_markdown(msg["content"]))
            if msg.get("metadata"):
                meta = msg["metadata"]
                # Display Route Badge
                route = meta.get("route", "")
                badge_class = {
                    "sql_tool": "badge-sql",
                    "rag_knowledge": "badge-rag",
                    "hybrid": "badge-hybrid",
                    "direct_conversation": "badge-direct"
                }.get(route, "badge-direct")
                
                st.markdown(f"<span class='{badge_class}'>ROUTE: {route.upper()}</span> &nbsp; <small>Model: {meta.get('model_used', 'Mock Engine')}</small>", unsafe_allow_html=True)

                # Tool Calls Expander
                if meta.get("tools_called"):
                    with st.expander("🛠️ Tool Calling Evidence (Database Verified)", expanded=False):
                        for tool in meta["tools_called"]:
                            st.write(f"**Tool:** `{tool['tool_name']}`")
                            st.write("**Arguments:**", tool.get("arguments"))
                            st.json(tool.get("result"))

                # RAG Sources Expander
                if meta.get("rag_sources"):
                    with st.expander("📚 Knowledge Base Citations (FAISS)", expanded=False):
                        for src in meta["rag_sources"]:
                            st.markdown(f"- 📄 **{src['document_name']}** (Chunk {src['chunk_index']} | Cosine Similarity: `{src['similarity_score']:.2f}`)")
                            st.caption(f"\"{src['content'][:250]}...\"")

    # Chat Input handler
    user_input = st.chat_input("Ask a question about your spending, income, or financial concepts...")
    prompt_to_submit = clicked_prompt or user_input

    if prompt_to_submit:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": prompt_to_submit})
        with st.chat_message("user"):
            st.markdown(prompt_to_submit)

        # Get Assistant response
        with st.chat_message("assistant"):
            with st.spinner("FinQuery is analyzing and verifying evidence..."):
                response_data = send_chat_query(prompt_to_submit)

            if "error" in response_data:
                st.error(f"Error: {response_data['error']}")
            else:
                answer = response_data.get("answer", "No response received.")
                formatted_answer = format_chat_markdown(answer)
                st.markdown(formatted_answer)

                routing_info = response_data.get("routing", {})
                route = routing_info.get("route", "direct_conversation")
                badge_class = {
                    "sql_tool": "badge-sql",
                    "rag_knowledge": "badge-rag",
                    "hybrid": "badge-hybrid",
                    "direct_conversation": "badge-direct"
                }.get(route, "badge-direct")

                st.markdown(f"<span class='{badge_class}'>ROUTE: {route.upper()}</span> &nbsp; <small>Model: {response_data.get('model_used')}</small>", unsafe_allow_html=True)

                if response_data.get("tools_called"):
                    with st.expander("🛠️ Tool Calling Evidence (Database Verified)", expanded=False):
                        for tool in response_data["tools_called"]:
                            st.write(f"**Tool:** `{tool['tool_name']}`")
                            st.write("**Arguments:**", tool.get("arguments"))
                            st.json(tool.get("result"))

                if response_data.get("rag_sources"):
                    with st.expander("📚 Knowledge Base Citations (FAISS)", expanded=False):
                        for src in response_data["rag_sources"]:
                            st.markdown(f"- 📄 **{src['document_name']}** (Chunk {src['chunk_index']} | Cosine Similarity: `{src['similarity_score']:.2f}`)")
                            st.caption(f"\"{src['content'][:250]}...\"")

                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": formatted_answer,
                    "metadata": {
                        "route": route,
                        "tools_called": response_data.get("tools_called"),
                        "rag_sources": response_data.get("rag_sources"),
                        "model_used": response_data.get("model_used")
                    }
                })


# ==========================================
# TAB 3: TRANSACTIONS BROWSER & FILTER
# ==========================================
with tab_transactions:
    st.title("Transaction History")
    
    # Filter Row
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        f_type = st.selectbox("Transaction Type", ["All", "expense", "income"])
    with f_col2:
        f_category = st.text_input("Category Filter", placeholder="e.g. Groceries")
    with f_col3:
        f_search = st.text_input("Search Merchant/Notes", placeholder="e.g. Amazon, Netflix")
    with f_col4:
        f_limit = st.selectbox("Rows per page", [25, 50, 100, 200], index=1)

    # Query Backend
    params = f"?limit={f_limit}"
    if f_type != "All":
        params += f"&transaction_type={f_type}"
    if f_category:
        params += f"&category={f_category}"
    if f_search:
        params += f"&search_query={f_search}"

    try:
        t_res = requests.get(f"{API_BASE_URL}/api/transactions{params}", timeout=5)
        if t_res.status_code == 200:
            data_resp = t_res.json()
            total_records = data_resp["total"]
            tx_list = data_resp["transactions"]

            st.caption(f"Showing {len(tx_list)} of {total_records} transactions matching criteria.")

            if tx_list:
                df_tx = pd.DataFrame(tx_list)[["id", "date", "amount", "category", "description", "transaction_type", "payment_method", "account"]]
                df_tx["amount"] = df_tx["amount"].apply(lambda x: f"${x:,.2f}")
                df_tx.columns = ["ID", "Date", "Amount", "Category", "Description", "Type", "Payment Method", "Account"]
                st.dataframe(df_tx, use_container_width=True, hide_index=True)

                # Export CSV button
                csv_bytes = df_tx.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Filtered Transactions as CSV",
                    data=csv_bytes,
                    file_name="finquery_filtered_transactions.csv",
                    mime="text/csv"
                )
            else:
                st.info("No transactions found matching your filters.")
    except Exception as e:
        st.error(f"Failed to fetch transactions: {e}")


# ==========================================
# TAB 4: CSV UPLOAD & STATEMENT INGESTION
# ==========================================
with tab_upload:
    st.title("Upload Financial Statements")
    st.markdown("Upload bank or credit card statements in CSV format to import transactions into FinQuery.")

    st.info("Expected columns: `date` (YYYY-MM-DD or DD/MM/YYYY), `amount`, `category`, `description`, `transaction_type` (income/expense).")

    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file is not None:
        if st.button("🚀 Process & Ingest Statement", type="primary"):
            with st.spinner("Parsing, validating, and checking duplicates..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                try:
                    up_res = requests.post(f"{API_BASE_URL}/api/transactions/upload", files=files, timeout=15)
                    if up_res.status_code == 200:
                        res_data = up_res.json()
                        st.success("✅ Statement Processed Successfully!")
                        
                        uc1, uc2, uc3, uc4 = st.columns(4)
                        uc1.metric("Total Processed", res_data["total_processed"])
                        uc2.metric("New Records Inserted", res_data["inserted_count"])
                        uc3.metric("Duplicates Skipped", res_data["duplicate_count"])
                        uc4.metric("Invalid Records", res_data["invalid_count"])

                        if res_data["errors"]:
                            with st.expander("⚠️ View Parse/Validation Warnings", expanded=True):
                                for err in res_data["errors"]:
                                    st.write(f"- Row {err['row']}: {err['error']}")

                        # Refresh cache
                        fetch_summary.clear()
                        fetch_categories.clear()
                        fetch_monthly_trends.clear()
                    else:
                        st.error(f"Upload failed: {up_res.text}")
                except Exception as e:
                    st.error(f"Error communicating with upload endpoint: {e}")

    st.divider()
    st.subheader("🔄 Demo Reset & Seeding")
    col_demo1, col_demo2 = st.columns(2)
    with col_demo1:
        if st.button("🌱 Reload 200+ Synthetic Demo Transactions"):
            with st.spinner("Seeding database..."):
                try:
                    # Clear and reload
                    with open("data/transactions.csv", "rb") as f:
                        files = {"file": ("transactions.csv", f.read(), "text/csv")}
                    requests.delete(f"{API_BASE_URL}/api/transactions/all")
                    requests.post(f"{API_BASE_URL}/api/transactions/upload", files=files)
                    st.success("Demo dataset loaded successfully!")
                    fetch_summary.clear()
                    fetch_categories.clear()
                    fetch_monthly_trends.clear()
                    st.rerun()
                except Exception as ex:
                    st.error(f"Failed to load demo dataset: {ex}")


# ==========================================
# TAB 5: DEEP ANALYTICS & ANOMALY DETECTION
# ==========================================
with tab_analytics:
    st.title("Deep Financial Analytics & Anomaly Detection")

    # Section 1: Unusual Spending Anomaly Detection
    st.subheader("⚠️ Statistical Spending Anomaly Detection")
    st.caption("Transparent Z-Score standard deviation calculation flags transactions that deviate significantly from category norms.")

    threshold = st.slider("Z-Score Sensitivity Threshold", min_value=1.5, max_value=3.5, value=2.0, step=0.1)
    try:
        anom_res = requests.get(f"{API_BASE_URL}/api/analytics/unusual?threshold_z={threshold}", timeout=5)
        if anom_res.status_code == 200:
            anom_data = anom_res.json()
            st.markdown(f"**Detection Method:** `{anom_data['method']}`")
            st.markdown(f"**Outliers Found:** **{anom_data['total_anomalies_found']}** anomalous transactions detected.")

            if anom_data["anomalies"]:
                for a in anom_data["anomalies"]:
                    with st.container():
                        st.error(
                            f"**${a['amount']:,.2f}** for *{a['description']}* ({a['category']}) on {a['date']}\n\n"
                            f"➔ {a['reason']} | Historical category mean: ${a['category_average']:,.2f} | Std Dev: ${a['category_std_dev']:,.2f} (Z = {a['z_score']:.2f})"
                        )
            else:
                st.success("✅ All transactions are within expected standard deviations. No spending spikes detected.")
    except Exception as e:
        st.error(f"Failed to run anomaly detection: {e}")

    st.divider()

    # Section 2: Month-over-Month Comparison Tool
    st.subheader("📊 Month-over-Month Comparative Analytics")
    monthly_data = fetch_monthly_trends()
    if monthly_data and len(monthly_data) >= 2:
        available_months = [m["month"] for m in monthly_data]
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            m1 = st.selectbox("Baseline Month", available_months, index=max(0, len(available_months) - 2))
        with comp_col2:
            m2 = st.selectbox("Comparison Month", available_months, index=len(available_months) - 1)

        if m1 != m2:
            try:
                comp_res = requests.get(f"{API_BASE_URL}/api/analytics/compare?month1={m1}&month2={m2}", timeout=5)
                if comp_res.status_code == 200:
                    c_data = comp_res.json()
                    diff = c_data["expense_difference"]
                    pct = c_data.get("expense_percentage_change") or 0.0

                    m_col1, m_col2, m_col3 = st.columns(3)
                    m_col1.metric(f"{m1} Expenses", f"${c_data['month1_expenses']:,.2f}")
                    m_col2.metric(f"{m2} Expenses", f"${c_data['month2_expenses']:,.2f}")
                    m_col3.metric(
                        "Spending Delta",
                        f"${abs(diff):,.2f}",
                        delta=f"{pct:+.1f}%",
                        delta_color="inverse" if diff > 0 else "normal"
                    )

                    # Category delta table
                    if c_data.get("category_breakdown"):
                        st.markdown("**Category Shifts:**")
                        df_deltas = pd.DataFrame(c_data["category_breakdown"])
                        df_deltas["month1_amount"] = df_deltas["month1_amount"].apply(lambda x: f"${x:,.2f}")
                        df_deltas["month2_amount"] = df_deltas["month2_amount"].apply(lambda x: f"${x:,.2f}")
                        df_deltas["difference"] = df_deltas["difference"].apply(lambda x: f"${x:+,.2f}")
                        df_deltas.columns = ["Category", f"{m1} Spend", f"{m2} Spend", "Dollar Shift", "% Change"]
                        st.dataframe(df_deltas, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Failed to execute monthly comparison: {e}")
        else:
            st.info("Select two different months to compare spending shifts.")


# ==========================================
# TAB 6: KNOWLEDGE BASE (RAG)
# ==========================================
with tab_knowledge:
    st.title("📚 Financial Knowledge Base (RAG Repository)")
    st.markdown("Semantic vector search across vetted public financial education documents using FAISS and Sentence Transformers.")

    # Search Knowledge Base Directly
    rag_query = st.text_input("🔍 Search Knowledge Base Semantically", placeholder="e.g. How does compound interest work?")
    if rag_query:
        try:
            r_res = requests.post(f"{API_BASE_URL}/api/rag/query", json={"query": rag_query, "top_k": 3}, timeout=5)
            if r_res.status_code == 200:
                results = r_res.json()
                st.markdown(f"**Retrieved {len(results)} relevant chunks:**")
                for r in results:
                    with st.expander(f"📄 {r['document_name']} (Chunk {r['chunk_index']} — Score: {r['similarity_score']:.2f})", expanded=True):
                        st.markdown(format_chat_markdown(r["content"]))
            else:
                st.error(f"Search failed: {r_res.text}")
        except Exception as e:
            st.error(f"Error querying RAG: {e}")

    st.divider()
    st.subheader("📂 Vetted Educational Documents Ingested")
    try:
        doc_res = requests.get(f"{API_BASE_URL}/api/rag/documents", timeout=5)
        if doc_res.status_code == 200:
            docs = doc_res.json()["documents"]
            for d in docs:
                with st.expander(f"📖 {d.get('title', d['filename'])}", expanded=False):
                    st.caption(f"Filename: `{d['filename']}` | Size: {d['size_bytes']} bytes")
                    st.write(d.get("summary_snippet", ""))
    except Exception as e:
        st.error(f"Failed to list documents: {e}")
