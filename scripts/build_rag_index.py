"""Script to build and persist FAISS vector index from financial knowledge documents."""
from src.rag.retrieval import RAGPipeline
from src.utils.logger import logger

def main():
    logger.info("Initializing RAG pipeline for vector indexing...")
    pipeline = RAGPipeline()
    result = pipeline.build_or_refresh_index()
    logger.info(f"Indexing completed: {result}")
    print(f"\n✅ FAISS Vector Index Successfully Created!")
    print(f"Documents Ingested: {result.get('documents_count')}")
    print(f"Chunks Indexed:     {result.get('chunks_count')}")
    print(f"Vector Dimension:   {result.get('vector_dimension')}")

if __name__ == "__main__":
    main()
