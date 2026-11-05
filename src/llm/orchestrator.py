"""Financial Orchestrator and Query Router.

Orchestrates:
1. Intelligent intent classification (SQL Tool vs RAG vs Hybrid vs Direct Chat).
2. Safe financial tool calling with strict validation.
3. RAG context retrieval with source document citations.
4. Response synthesis using Live Gemini or High-Fidelity Mock Engine.
5. Strict anti-hallucination guarantees (grounded in DB evidence).
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from src.llm.client import GeminiClient
from src.llm.prompts import (
    FINANCIAL_ANALYST_SYSTEM_PROMPT,
    RAG_KNOWLEDGE_SYSTEM_PROMPT,
    HYBRID_SYSTEM_PROMPT
)
from src.tools.financial_tools import execute_financial_tool, TOOL_REGISTRY
from src.rag.retrieval import RAGPipeline
from src.schemas.chat import (
    ChatRequest,
    ChatResponse,
    RoutingDecision,
    ToolCallRecord,
    RAGSourceRecord
)
from src.utils.logger import logger

class FinancialOrchestrator:
    def __init__(self, gemini_client: Optional[GeminiClient] = None, rag_pipeline: Optional[RAGPipeline] = None):
        self.llm_client = gemini_client or GeminiClient()
        self.rag_pipeline = rag_pipeline or RAGPipeline()

    def route_query(self, message: str) -> RoutingDecision:
        """
        Classifies user query into 'sql_tool', 'rag_knowledge', 'hybrid', or 'direct_conversation'.
        Uses robust semantic heuristics and intent keyword boundaries.
        """
        msg = message.lower().strip()

        # Check for direct conversational pleasantries
        greetings = {"hi", "hello", "hey", "good morning", "good evening", "who are you", "what can you do", "help"}
        if msg in greetings or msg.startswith("hi ") or msg.startswith("hello ") or msg.startswith("hey "):
            return RoutingDecision(
                route="direct_conversation",
                confidence=0.98,
                reason="User offered a standard greeting or capability inquiry.",
                identified_intent="greeting"
            )

        # Explicit educational concepts (RAG targets)
        rag_concepts = [
            "compound interest", "rule of 72", "mutual fund", "mutual funds",
            "etf", "etfs", "50/30/20", "zero-based", "emergency fund", "emergency funds",
            "snowball", "avalanche", "inflation", "consumer price index", "cpi",
            "purchasing power", "401k", "ira", "traditional vs roth", "roth",
            "nominal return", "real return", "nominal vs real", "budgeting method",
            "budget rule", "how to budget", "index fund", "time value of money"
        ]

        # Explicit personal transaction targets (SQL targets)
        personal_spending_keywords = [
            "how much did i", "how much have i", "how much i spent", "my spending",
            "my income", "my balance", "my expenses", "my top", "my largest",
            "what did i spend", "total income", "total expenses", "net balance",
            "unusual spending", "unusually high", "largest transactions", "biggest transactions",
            "top 5 expenses", "top 5 transactions", "top 10 expenses", "top 3 expenses",
            "spending on", "spent on", "cost of", "compare my", "compare spending between"
        ]

        # Single word SQL indicators
        has_personal_pronoun = any(p in msg.split() for p in ["i", "my", "mine", "we", "our"])
        has_trans_term = any(t in msg for t in ["spend", "spent", "spending", "income", "earned", "balance", "transactions", "groceries", "dining", "rent", "utilities"])

        has_sql_signal = any(k in msg for k in personal_spending_keywords) or (has_personal_pronoun and has_trans_term)
        has_rag_signal = any(c in msg for c in rag_concepts)

        # Check for definition queries e.g. "what is compound interest", "explain etf"
        if any(msg.startswith(stem) for stem in ["what is ", "what are ", "explain ", "define "]):
            # If asking about personal finances ("what is my income", "what is my spending"), it's SQL
            if has_personal_pronoun or "total income" in msg or "total expenses" in msg or "net balance" in msg:
                has_sql_signal = True
            elif has_rag_signal or not has_trans_term:
                has_rag_signal = True

        if has_sql_signal and has_rag_signal:
            return RoutingDecision(
                route="hybrid",
                confidence=0.92,
                reason="Query contains inquiries about both personal transactions and general financial knowledge.",
                identified_intent="hybrid_personal_and_educational"
            )
        elif has_sql_signal:
            return RoutingDecision(
                route="sql_tool",
                confidence=0.95,
                reason="Query is focused on user's actual financial records, spending totals, or calculations.",
                identified_intent="database_transaction_query"
            )
        elif has_rag_signal:
            return RoutingDecision(
                route="rag_knowledge",
                confidence=0.95,
                reason="Query asks for general financial concepts, definitions, or educational strategies.",
                identified_intent="financial_knowledge_query"
            )
        else:
            # Fallback
            if any(term in msg for term in ["spend", "expense", "transaction", "income", "cost"]):
                return RoutingDecision(
                    route="sql_tool",
                    confidence=0.75,
                    reason="Inferred personal transaction query from keywords.",
                    identified_intent="database_transaction_query"
                )
            elif any(term in msg for term in ["money", "dollar", "card", "account", "invest", "finance", "debt"]):
                return RoutingDecision(
                    route="rag_knowledge",
                    confidence=0.70,
                    reason="Inferred general financial inquiry from contextual keywords.",
                    identified_intent="financial_knowledge_fallback"
                )
            return RoutingDecision(
                route="direct_conversation",
                confidence=0.60,
                reason="Query does not explicitly target database transactions or indexed financial knowledge.",
                identified_intent="general_conversation"
            )

    def extract_and_execute_tools(self, message: str, db: Session) -> Tuple[List[ToolCallRecord], Dict[str, Any]]:
        """
        Parses intent and executes appropriate registered database tool(s).
        Returns list of ToolCallRecords and consolidated evidence dict.
        """
        msg = message.lower()
        records: List[ToolCallRecord] = []
        evidence: Dict[str, Any] = {}

        # 1. Compare monthly spending: check for two months (e.g., 2026-07 and 2026-08, or "july and august")
        month_matches = re.findall(r"\b(20\d{2}-\d{2})\b", msg)
        if len(month_matches) >= 2 and ("compare" in msg or "difference" in msg or "between" in msg):
            args = {"month1": month_matches[0], "month2": month_matches[1]}
            res = execute_financial_tool("compare_monthly_spending", args, db)
            records.append(ToolCallRecord(
                tool_name="compare_monthly_spending",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["monthly_comparison"] = res["result"]
            return records, evidence

        # 2. Unusual spending detection
        if any(term in msg for term in ["unusual", "anomaly", "abnormal", "spike", "unusually high", "suspicious"]):
            args = {"threshold_std": 2.0}
            res = execute_financial_tool("get_unusual_spending", args, db)
            records.append(ToolCallRecord(
                tool_name="get_unusual_spending",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["unusual_spending"] = res["result"]
            return records, evidence

        # 3. Largest / Top transactions
        if any(term in msg for term in ["largest", "highest", "biggest", "top 5", "top five", "top 10", "top ten", "top expenses"]):
            limit = 5
            if "top 10" in msg or "top ten" in msg:
                limit = 10
            elif "top 3" in msg or "top three" in msg:
                limit = 3
            t_type = "income" if ("income" in msg or "earnings" in msg) else "expense"
            args = {"limit": limit, "transaction_type": t_type}
            res = execute_financial_tool("get_largest_transactions", args, db)
            records.append(ToolCallRecord(
                tool_name="get_largest_transactions",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["largest_transactions"] = res["result"]
            return records, evidence

        # 4. Net balance / Savings rate
        if any(term in msg for term in ["net balance", "balance", "how much is left", "savings rate", "remaining"]):
            args = {}
            res = execute_financial_tool("get_net_balance", args, db)
            records.append(ToolCallRecord(
                tool_name="get_net_balance",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["net_balance"] = res["result"]
            return records, evidence

        # 5. Total income
        if ("income" in msg or "earned" in msg or "salary" in msg) and not any(term in msg for term in ["spend", "expense"]):
            args = {}
            if month_matches:
                # Filter by month range
                m = month_matches[0]
                args = {"start_date": f"{m}-01", "end_date": f"{m}-31"}
            res = execute_financial_tool("get_total_income", args, db)
            records.append(ToolCallRecord(
                tool_name="get_total_income",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["total_income"] = res["result"]
            return records, evidence

        # 6. Category spending or specific category (e.g. food, groceries, rent, dining, shopping, travel, utilities)
        known_categories = [
            "groceries", "food", "dining", "rent", "utilities", "entertainment",
            "travel", "shopping", "healthcare", "health", "subscriptions", "investment"
        ]
        matched_cat = None
        for cat in known_categories:
            if re.search(rf"\b{cat}\b", msg):
                matched_cat = cat.capitalize()
                break

        if matched_cat or "category" in msg or "categories" in msg:
            args = {"category": matched_cat}
            if month_matches:
                m = month_matches[0]
                args["start_date"] = f"{m}-01"
                args["end_date"] = f"{m}-31"
            res = execute_financial_tool("get_category_spending", args, db)
            records.append(ToolCallRecord(
                tool_name="get_category_spending",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["category_spending"] = res["result"]
            return records, evidence

        # 7. Monthly summary
        if "monthly" in msg or (month_matches and "summary" in msg):
            args = {"month": month_matches[0] if month_matches else None}
            res = execute_financial_tool("get_monthly_summary", args, db)
            records.append(ToolCallRecord(
                tool_name="get_monthly_summary",
                arguments=args,
                result=res.get("result"),
                success=res.get("success", False),
                error=res.get("error")
            ))
            if res.get("success"):
                evidence["monthly_summary"] = res["result"]
            return records, evidence

        # 8. Default fallback for spending: get_total_expenses
        args = {}
        if month_matches:
            m = month_matches[0]
            args = {"start_date": f"{m}-01", "end_date": f"{m}-31"}
        res = execute_financial_tool("get_total_expenses", args, db)
        records.append(ToolCallRecord(
            tool_name="get_total_expenses",
            arguments=args,
            result=res.get("result"),
            success=res.get("success", False),
            error=res.get("error")
        ))
        if res.get("success"):
            evidence["total_expenses"] = res["result"]
        return records, evidence

    def synthesize_mock_response(
        self,
        message: str,
        route: RoutingDecision,
        tools_called: List[ToolCallRecord],
        rag_sources: List[RAGSourceRecord],
        evidence: Dict[str, Any]
    ) -> str:
        """
        High-fidelity deterministic response synthesizer for Mock/Demo mode.
        Outputs rich, accurate, and evidence-grounded markdown text.
        """
        if route.route == "direct_conversation":
            return (
                "👋 **Hello! I am FinQuery — your AI Financial Data Assistant.**\n\n"
                "I can assist you in two key ways:\n"
                "1. **Analyze Your Transactions:** Ask questions about your spending, income, net balance, top expenses, category breakdowns, or unusual anomalies (e.g., *'How much did I spend this month?'* or *'Show my top 5 expenses'*).\n"
                "2. **Financial Knowledge (RAG):** Ask about personal finance principles, budgeting strategies, and investing fundamentals (e.g., *'What is compound interest?'* or *'Explain Mutual Funds vs ETFs'*).\n\n"
                "How can I assist your financial analysis today?"
            )

        if route.route == "sql_tool":
            parts = []
            if "total_income" in evidence:
                inc = evidence["total_income"]
                parts.append(
                    f"### 💵 Total Income Summary\n"
                    f"- **Total Income:** **${inc.get('value', 0.0):,.2f}**\n"
                    f"- **Transactions Analyzed:** {inc.get('transactions_analyzed', 0)}\n"
                    f"- *Evidence:* Verified from database records where `transaction_type = 'income'`."
                )

            elif "total_expenses" in evidence:
                exp = evidence["total_expenses"]
                parts.append(
                    f"### 💳 Total Expenses Summary\n"
                    f"- **Total Spending:** **${exp.get('value', 0.0):,.2f}**\n"
                    f"- **Transactions Analyzed:** {exp.get('transactions_analyzed', 0)}\n"
                    f"- *Evidence:* Verified from database records where `transaction_type = 'expense'`."
                )

            elif "net_balance" in evidence:
                nb = evidence["net_balance"]
                parts.append(
                    f"### ⚖️ Net Financial Balance\n"
                    f"- **Total Income:** ${nb.get('total_income', 0.0):,.2f}\n"
                    f"- **Total Expenses:** ${nb.get('total_expenses', 0.0):,.2f}\n"
                    f"- **Net Balance:** **${nb.get('net_balance', 0.0):,.2f}**\n"
                    f"- **Savings Rate:** **{nb.get('savings_rate_percent', 0.0):.1f}%**\n"
                    f"- *Evidence:* Calculated directly as `Total Income - Total Expenses`."
                )

            elif "category_spending" in evidence:
                cat_data = evidence["category_spending"]
                queried = cat_data.get("category_queried", "all")
                items = cat_data.get("breakdown", [])
                tot = cat_data.get("total_spending", 0.0)

                if queried != "all":
                    if items:
                        item = items[0]
                        parts.append(
                            f"### 🏷️ Spending on {queried}\n"
                            f"- **Total Spent:** **${item.get('total_amount', 0.0):,.2f}**\n"
                            f"- **Number of Transactions:** {item.get('transaction_count', 0)}\n"
                            f"- **Share of Total Expenses:** {item.get('percentage_of_total', 0.0):.1f}%\n"
                            f"- *Evidence:* Sum of verified `{queried}` expenses in the database."
                        )
                    else:
                        parts.append(
                            f"### 🏷️ Spending on {queried}\n"
                            f"No transactions found for category **{queried}** in the database records."
                        )
                else:
                    parts.append(f"### 🏷️ Category Spending Breakdown (Total: ${tot:,.2f})\n")
                    for it in items[:6]:
                        parts.append(f"- **{it['category']}:** ${it['total_amount']:,.2f} ({it['percentage_of_total']:.1f}% | {it['transaction_count']} transactions)")
                    parts.append("\n*Evidence:* Database aggregation grouped by category.")

            elif "largest_transactions" in evidence:
                lt = evidence["largest_transactions"]
                records = lt.get("largest_transactions", [])
                parts.append(f"### 🔝 Top {len(records)} Largest Transactions\n")
                for i, r in enumerate(records, start=1):
                    parts.append(f"{i}. **${r['amount']:,.2f}** — {r['description']} (*{r['category']}*, {r['date']})")
                parts.append("\n*Evidence:* Transaction records ordered by amount descending.")

            elif "monthly_comparison" in evidence:
                mc = evidence["monthly_comparison"]
                diff = mc.get("expense_difference", 0.0)
                arrow = "📈 increased" if diff > 0 else "📉 decreased"
                parts.append(
                    f"### 📊 Spending Comparison: {mc['month1']} vs. {mc['month2']}\n"
                    f"- **{mc['month1']} Expenses:** ${mc['month1_expenses']:,.2f}\n"
                    f"- **{mc['month2']} Expenses:** ${mc['month2_expenses']:,.2f}\n"
                    f"- **Difference:** Spending {arrow} by **${abs(diff):,.2f}** ({mc.get('expense_percentage_change', 0.0):+.1f}%)\n\n"
                    f"**Category Breakdown:**\n"
                )
                for c in mc.get("category_breakdown", [])[:5]:
                    parts.append(f"- **{c['category']}:** ${c['month1_amount']:,.2f} ➔ ${c['month2_amount']:,.2f} (diff: ${c['difference']:+,.2f})")
                parts.append("\n*Evidence:* Aggregation comparing database records between target months.")

            elif "unusual_spending" in evidence:
                us = evidence["unusual_spending"]
                anomalies = us.get("unusual_transactions", [])
                count = us.get("anomalies_detected", 0)
                parts.append(
                    f"### ⚠️ Unusual Spending Detection\n"
                    f"Statistical analysis (Z-Score standard deviation threshold = {us.get('threshold_z', 2.0)}) identified **{count}** unusual transactions:\n"
                )
                if anomalies:
                    for a in anomalies[:5]:
                        parts.append(f"- **${a['amount']:,.2f}** for *{a['description']}* on {a['date']} ({a['category']}) ➔ {a['reason']}")
                else:
                    parts.append("✅ No unusual spending spikes detected. All transactions are within normal statistical ranges.")
                parts.append("\n*Method:* Sample standard deviation and Z-score per category (transparent statistics).")

            elif "monthly_summary" in evidence:
                ms = evidence["monthly_summary"]
                if "income" in ms:
                    parts.append(
                        f"### 📅 Monthly Summary for {ms['month']}\n"
                        f"- **Income:** ${ms.get('income', 0.0):,.2f}\n"
                        f"- **Expenses:** ${ms.get('expenses', 0.0):,.2f}\n"
                        f"- **Net Balance:** ${ms.get('net_balance', 0.0):,.2f}\n"
                        f"- **Transaction Count:** {ms.get('transaction_count', 0)}"
                    )
                else:
                    parts.append("### 📅 Monthly Spending Trends\n")
                    for m in ms.get("all_months", [])[-6:]:
                        parts.append(f"- **{m['month']}:** Income ${m['income']:,.2f} | Expenses ${m['expenses']:,.2f} | Net ${m['net']:,.2f}")

            return "\n\n".join(parts) if parts else "I analyzed the transaction data, but found no records matching your query."

        if route.route == "rag_knowledge":
            if not rag_sources:
                return (
                    "Based on the available financial knowledge documents in the knowledge base, "
                    "I do not have enough supporting information to answer this question accurately."
                )

            # Build comprehensive knowledge synthesis from top chunk
            top_source = rag_sources[0]
            doc_name = top_source.document_name
            content = top_source.content

            response_text = (
                f"### 📚 Financial Knowledge Explanation\n\n"
                f"{content}\n\n"
                f"---\n"
                f"**References & Sources:**\n"
            )
            for s in rag_sources:
                response_text += f"- 📄 **{s.document_name}** (Chunk {s.chunk_index}, Similarity: {s.similarity_score:.2f})\n"
            return response_text

        if route.route == "hybrid":
            # Combine SQL and RAG
            sql_text = self.synthesize_mock_response(message, RoutingDecision(route="sql_tool", confidence=1.0, reason=""), tools_called, [], evidence)
            rag_text = self.synthesize_mock_response(message, RoutingDecision(route="rag_knowledge", confidence=1.0, reason=""), [], rag_sources, {})
            return (
                f"## 📊 Your Transaction Data\n{sql_text}\n\n"
                f"---\n\n"
                f"## 📖 Financial Knowledge Concept\n{rag_text}"
            )

        return "How can I assist your financial analysis or educational questions?"

    def process_chat(self, chat_request: ChatRequest, db: Session) -> ChatResponse:
        """
        Main pipeline entry point for end-to-end conversation processing:
        1. Routes question
        2. Executes tools or queries RAG
        3. Generates grounded response
        """
        user_message = chat_request.message.strip()
        logger.info(f"Processing chat message: '{user_message}'")

        # Step 1: Route the query
        route = self.route_query(user_message)
        logger.info(f"Routing decision: {route.route} (Confidence: {route.confidence})")

        tools_called: List[ToolCallRecord] = []
        evidence: Dict[str, Any] = {}
        rag_sources: List[RAGSourceRecord] = []

        # Step 2: Execute SQL Tools if needed
        if route.route in ("sql_tool", "hybrid"):
            tools_called, evidence = self.extract_and_execute_tools(user_message, db)

        # Step 3: Execute RAG Retrieval if needed
        if route.route in ("rag_knowledge", "hybrid"):
            retrieved = self.rag_pipeline.retrieve(user_message, top_k=3, min_score=0.20)
            rag_sources = self.rag_pipeline.format_sources(retrieved)

        # Step 4: Synthesize Final Response
        model_used = "mock-rule-orchestrator"
        final_answer = ""

        # Try Live Gemini if available
        if self.llm_client.is_live:
            try:
                system_instruction = FINANCIAL_ANALYST_SYSTEM_PROMPT
                prompt_content = f"User Question: {user_message}\n\n"

                if route.route == "sql_tool":
                    system_instruction = FINANCIAL_ANALYST_SYSTEM_PROMPT
                    prompt_content += f"Verified Database Tool Evidence:\n{evidence}\n\nPlease formulate a clear, professional, evidence-backed answer based strictly on the above numbers."
                elif route.route == "rag_knowledge":
                    system_instruction = RAG_KNOWLEDGE_SYSTEM_PROMPT
                    rag_context_str = self.rag_pipeline.build_context_prompt(
                        [(s.model_dump(), s.similarity_score) for s in rag_sources]
                    )
                    prompt_content += f"Retrieved Knowledge Context:\n{rag_context_str}\n\nPlease formulate an educational answer based strictly on the retrieved context."
                elif route.route == "hybrid":
                    system_instruction = HYBRID_SYSTEM_PROMPT
                    rag_context_str = self.rag_pipeline.build_context_prompt(
                        [(s.model_dump(), s.similarity_score) for s in rag_sources]
                    )
                    prompt_content += f"Verified Transaction Evidence:\n{evidence}\n\nRetrieved Knowledge Context:\n{rag_context_str}"
                else:
                    system_instruction = "You are FinQuery, a professional AI financial assistant. Greet the user courteously and briefly explain what you can do."

                gen_result = self.llm_client.generate(
                    prompt=prompt_content,
                    system_instruction=system_instruction
                )

                if gen_result.get("success") and gen_result.get("text"):
                    final_answer = gen_result["text"].strip()
                    model_used = f"Live Gemini ({self.llm_client.model_name})"
                else:
                    logger.warning(f"Live Gemini generation failed or returned empty: {gen_result.get('error')}. Using deterministic fallback.")
                    final_answer = self.synthesize_mock_response(user_message, route, tools_called, rag_sources, evidence)
                    model_used = "Mock/Demo Engine (Gemini fallback)"
            except Exception as e:
                logger.error(f"Error in Live LLM synthesis: {e}. Falling back to mock engine.")
                final_answer = self.synthesize_mock_response(user_message, route, tools_called, rag_sources, evidence)
                model_used = "Mock/Demo Engine (Exception fallback)"
        else:
            final_answer = self.synthesize_mock_response(user_message, route, tools_called, rag_sources, evidence)
            model_used = "Mock/Demo Engine (Configure GEMINI_API_KEY in .env for Live API)"

        return ChatResponse(
            answer=final_answer,
            routing=route,
            tools_called=tools_called,
            rag_sources=rag_sources,
            evidence=evidence,
            model_used=model_used
        )
