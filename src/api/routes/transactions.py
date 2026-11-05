"""Transaction management and CSV ingestion API endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.api.dependencies import get_db
from src.services.transaction_service import TransactionService
from src.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionFilterParams,
    TransactionListResponse,
    TransactionUploadSummary
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

@router.post("/upload", response_model=TransactionUploadSummary, summary="Upload CSV file of transactions")
async def upload_transactions_csv(
    file: UploadFile = File(..., description="CSV file containing financial records"),
    db: Session = Depends(get_db)
):
    """
    Accepts a CSV file of transactions, validates headers and rows,
    deduplicates identical records, and persists valid records into SQLite.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a .csv file."
        )

    try:
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {str(e)}"
        )

    summary = TransactionService.import_csv(db, content_str)
    return summary

@router.get("", response_model=TransactionListResponse, summary="List transactions with filters and pagination")
def list_transactions(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(None, description="Category filter (case-insensitive)"),
    transaction_type: Optional[str] = Query(None, description="'income' or 'expense'"),
    min_amount: Optional[float] = Query(None, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, description="Maximum transaction amount"),
    search_query: Optional[str] = Query(None, description="Search merchant, description, or category"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    """Retrieves paginated transactions filtered by optional query parameters."""
    params = TransactionFilterParams(
        start_date=start_date,
        end_date=end_date,
        category=category,
        transaction_type=transaction_type,
        min_amount=min_amount,
        max_amount=max_amount,
        search_query=search_query,
        limit=limit,
        offset=offset
    )
    return TransactionService.list_transactions(db, params)

@router.get("/{transaction_id}", response_model=TransactionRead, summary="Get single transaction by ID")
def get_transaction(transaction_id: int, db: Session = Depends(get_db)):
    """Retrieves a single transaction by primary key."""
    record = TransactionService.get_by_id(db, transaction_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found."
        )
    return TransactionRead.model_validate(record)

@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED, summary="Create single transaction")
def create_transaction(trans_data: TransactionCreate, db: Session = Depends(get_db)):
    """Manually creates a new transaction with validation and duplicate protection."""
    record, err = TransactionService.create_transaction(db, trans_data)
    if err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err
        )
    return TransactionRead.model_validate(record)

@router.delete("/all", summary="Reset/Clear all transactions")
def clear_transactions(db: Session = Depends(get_db)):
    """Deletes all transactions from the database (for demonstration resets)."""
    count = TransactionService.clear_all(db)
    return {"message": f"Successfully deleted {count} transactions."}
