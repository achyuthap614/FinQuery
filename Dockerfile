# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

WORKDIR /app

# Install system dependencies (build tools for scientific libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Initialize directories
RUN mkdir -p data/vector_store documents/financial_knowledge

# Expose backend (8000) and frontend (8501) ports
EXPOSE 8000 8501

# Default command starts backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
