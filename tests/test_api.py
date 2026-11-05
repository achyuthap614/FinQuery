"""End-to-End API endpoint integration tests using FastAPI TestClient."""
import io
import pytest

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "rag_pipeline" in data
    assert "llm_engine" in data

def test_transactions_crud_and_listing(client, sample_csv_data):
    # Upload transactions
    files = {"file": ("test.csv", io.BytesIO(sample_csv_data.encode("utf-8")), "text/csv")}
    upload_res = client.post("/api/transactions/upload", files=files)
    assert upload_res.status_code == 200
    summary = upload_res.json()
    assert summary["inserted_count"] == 7

    # List transactions
    list_res = client.get("/api/transactions")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 7
    assert len(list_data["transactions"]) == 7

    # Retrieve single transaction
    t_id = list_data["transactions"][0]["id"]
    get_res = client.get(f"/api/transactions/{t_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == t_id

def test_analytics_endpoints(client, sample_csv_data):
    # Upload data first
    files = {"file": ("test.csv", io.BytesIO(sample_csv_data.encode("utf-8")), "text/csv")}
    client.post("/api/transactions/upload", files=files)

    # Summary
    summary_res = client.get("/api/analytics/summary")
    assert summary_res.status_code == 200
    s_data = summary_res.json()
    assert s_data["total_income"] == 5000.00
    assert s_data["total_expenses"] == pytest.approx(2495.50, 0.01)

    # Categories
    cat_res = client.get("/api/analytics/categories")
    assert cat_res.status_code == 200
    assert len(cat_res.json()) > 0

    # Unusual spending
    unusual_res = client.get("/api/analytics/unusual?threshold_z=1.0")
    assert unusual_res.status_code == 200

def test_chat_endpoint_sql_query(client, sample_csv_data):
    # Upload data
    files = {"file": ("test.csv", io.BytesIO(sample_csv_data.encode("utf-8")), "text/csv")}
    client.post("/api/transactions/upload", files=files)

    chat_payload = {"message": "How much did I spend on Groceries?"}
    chat_res = client.post("/api/chat", json=chat_payload)
    assert chat_res.status_code == 200
    resp = chat_res.json()
    assert resp["routing"]["route"] == "sql_tool"
    assert "Groceries" in resp["answer"]
    assert len(resp["tools_called"]) > 0

def test_chat_endpoint_rag_query(client):
    chat_payload = {"message": "What is compound interest?"}
    chat_res = client.post("/api/chat", json=chat_payload)
    assert chat_res.status_code == 200
    resp = chat_res.json()
    assert resp["routing"]["route"] == "rag_knowledge"
    assert len(resp["rag_sources"]) > 0
    assert "compound_interest" in resp["rag_sources"][0]["document_name"].lower()

def test_rag_query_endpoint(client):
    payload = {"query": "Explain ETFs vs Mutual Funds", "top_k": 2}
    rag_res = client.post("/api/rag/query", json=payload)
    assert rag_res.status_code == 200
    sources = rag_res.json()
    assert len(sources) > 0
    assert "mutual_funds_vs_etfs" in sources[0]["document_name"].lower()
