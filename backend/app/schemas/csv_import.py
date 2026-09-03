from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class CSVTransactionRow(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID from source")
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="INR")
    status: str = Field(default="FAILED")  # SUCCESS, CAPTURED, FAILED, PENDING, CANCELLED, REFUNDED, ABANDONED
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    payment_method: str = Field(default="CARD")  # CARD, UPI, NETBANKING, WALLET, SUBSCRIPTION
    timestamp: str = Field(..., description="Transaction timestamp in ISO/standard format")
    invoice_id: Optional[str] = None
    subscription_id: Optional[str] = None


class CSVPreviewResponse(BaseModel):
    headers_detected: List[str] = Field(default_factory=list)
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list, description="First 10 raw rows from CSV")
    rows_detected: int
    valid_rows_count: int
    invalid_rows_count: int
    duplicate_rows_count: int
    sample_rows: List[Dict[str, Any]]
    errors: List[str]


class CSVImportRequest(BaseModel):
    rows: List[CSVTransactionRow]


class CSVImportSummaryResponse(BaseModel):
    imported_count: int
    failed_recoveries_triggered: int
    skipped_count: int
    duplicate_count: int
    errors: List[str]
