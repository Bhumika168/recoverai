import csv
import io
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, or_, and_, func
from app.database import get_db
from app.models.customer import Customer
from app.models.transaction import Transaction, TransactionStatus, PaymentMethod
from app.models.payment_attempt import PaymentAttempt, AttemptStatus
from app.models.recovery_case import RecoveryCase, CaseStatus
from app.models.audit_log import AuditLog, calculate_hash
from app.models.organization import Organization, OrganizationMembership
from app.schemas.transaction import TransactionCreate, TransactionResponse, FailedTransactionIngest, ManualTransactionCreate
from app.schemas.csv_import import CSVPreviewResponse, CSVImportRequest, CSVImportSummaryResponse, CSVTransactionRow
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, RecoverAIException
from app.agents.orchestrator import recover_transaction
from app.api.deps import get_current_org_context, require_write_access
from app.logging_config import logger

router = APIRouter(prefix="/transactions", tags=["Transactions"])


def parse_flexible_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse standard date/time strings using built-in formats."""
    if not ts_str or not ts_str.strip():
        return datetime.now(timezone.utc)
    ts = ts_str.strip().replace("Z", "+00:00")
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    ):
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


@router.post("/ingest-failure", response_model=APIResponse[TransactionResponse], status_code=status.HTTP_201_CREATED)
async def ingest_failed_transaction(
    payload: FailedTransactionIngest,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a failed payment event from payment provider webhook or gateway.
    Automatically ensures customer exists, creates transaction, initial payment attempt,
    opens a RecoveryCase, and appends a cryptographically chained audit log.
    """
    # 1. Find or create customer
    cust_res = await db.execute(select(Customer).where(Customer.email == payload.customer_email.strip().lower()))
    customer = cust_res.scalar_one_or_none()
    if not customer:
        customer = Customer(
            email=payload.customer_email.strip().lower(),
            name=payload.customer_name or payload.customer_email.split("@")[0].capitalize(),
            phone=payload.customer_phone,
            extra_metadata={},
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)

    # 2. Create failed transaction record
    txn = Transaction(
        transaction_id=payload.transaction_id or f"txn_hook_{uuid.uuid4().hex[:8]}",
        customer_id=customer.id,
        customer_email=customer.email,
        amount=payload.amount,
        currency=payload.currency,
        status=TransactionStatus.FAILED,
        payment_method=payload.payment_method,
        rzp_order_id=payload.rzp_order_id,
        rzp_payment_id=payload.rzp_payment_id,
        failure_code=payload.failure_code,
        failure_reason=payload.failure_reason,
        failure_source=payload.failure_source,
        error_step=payload.error_step,
        extra_metadata=payload.extra_metadata or {},
        transaction_time=datetime.now(timezone.utc),
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)

    # 3. Create initial PaymentAttempt
    attempt = PaymentAttempt(
        transaction_id=txn.id,
        attempt_number=1,
        rzp_payment_id=payload.rzp_payment_id,
        status=AttemptStatus.FAILED,
        error_code=payload.failure_code,
        error_description=payload.failure_reason,
        gateway_response={"source": payload.failure_source, "step": payload.error_step},
    )
    db.add(attempt)

    # 4. Open RecoveryCase
    recovery_case = RecoveryCase(
        transaction_id=txn.id,
        customer_id=customer.id,
        status=CaseStatus.OPEN,
        amount_at_risk=payload.amount,
        recovered_amount=0.0,
        recovery_score=50,
        risk_level="MEDIUM",
        retry_count=0,
        max_retries_allowed=3,
        strategy_summary="Pending AI diagnostic triage",
        requires_human_approval="NO",
    )
    db.add(recovery_case)
    await db.flush()
    await db.refresh(recovery_case)

    # 5. Append SHA-256 Chained Audit Log
    latest_audit = (await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(1))).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    state_after = {
        "transaction_id": txn.id,
        "customer_id": customer.id,
        "case_id": recovery_case.id,
        "amount": txn.amount,
        "failure_code": txn.failure_code,
        "status": txn.status.value,
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="FAILURE_INGESTED",
        entity_name="Transaction",
        entity_id=txn.id,
        actor="INGESTION_GATEWAY",
        state_after=state_after,
        timestamp_iso=now_iso,
    )

    audit_entry = AuditLog(
        entity_name="Transaction",
        entity_id=txn.id,
        event_type="FAILURE_INGESTED",
        actor="INGESTION_GATEWAY",
        state_before={},
        state_after=state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Failed transaction ingested: {payload.failure_code} ({payload.amount} {payload.currency})",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()
    await db.refresh(txn)

    return APIResponse(
        message="Failed transaction ingested and recovery case opened",
        data=TransactionResponse.model_validate(txn),
    )


@router.post("", response_model=APIResponse[TransactionResponse], status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: ManualTransactionCreate,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually register a transaction for the authenticated organization.
    Validates all inputs server-side, detects duplicate external transaction IDs,
    and runs autonomous recovery diagnostics on failed transactions.
    """
    org, membership = org_context

    if payload.amount <= 0:
        raise RecoverAIException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction amount must be greater than zero.",
            error_code="INVALID_AMOUNT",
        )

    # 1. Resolve transaction ID (generate if empty)
    ext_txn_id = payload.transaction_id.strip() if payload.transaction_id and payload.transaction_id.strip() else f"txn_{uuid.uuid4().hex[:10]}"
    
    # Check duplicate external transaction_id within this organization
    existing_txn = (
        await db.execute(
            select(Transaction).where(
                Transaction.organization_id == org.id,
                or_(Transaction.id == ext_txn_id, Transaction.transaction_id == ext_txn_id),
            )
        )
    ).scalar_one_or_none()
    if existing_txn:
        raise RecoverAIException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Transaction ID '{ext_txn_id}' already exists in your organization workspace.",
            error_code="DUPLICATE_TRANSACTION_ID",
        )

    # 2. Find or create customer scoped to this organization
    cust_email = (payload.customer_email.strip().lower() if payload.customer_email and "@" in payload.customer_email else f"customer_{uuid.uuid4().hex[:6]}@workspace.local")
    cust_name = payload.customer_name or payload.customer_id or cust_email.split("@")[0].capitalize()

    cust_res = await db.execute(
        select(Customer).where(
            Customer.organization_id == org.id,
            Customer.email == cust_email,
        )
    )
    customer = cust_res.scalar_one_or_none()
    if not customer:
        customer = Customer(
            organization_id=org.id,
            email=cust_email,
            name=cust_name,
            extra_metadata={},
        )
        db.add(customer)
        await db.flush()
        await db.refresh(customer)

    # 3. Status and Method resolution
    raw_status = payload.status.upper() if payload.status else "FAILED"
    txn_status = TransactionStatus.FAILED
    if "RECOVER" in raw_status:
        txn_status = TransactionStatus.RECOVERED
    elif "CAPTUR" in raw_status or "SUCCESS" in raw_status:
        txn_status = TransactionStatus.CAPTURED
    elif "ABANDON" in raw_status:
        txn_status = TransactionStatus.ABANDONED
    elif "AUTH" in raw_status:
        txn_status = TransactionStatus.AUTHORIZED
    else:
        txn_status = TransactionStatus.FAILED

    method = PaymentMethod.CARD
    try:
        method = PaymentMethod(payload.payment_method.upper())
    except Exception:
        method = PaymentMethod.CARD

    parsed_dt = parse_flexible_timestamp(payload.timestamp) or datetime.now(timezone.utc)

    # 4. Create Transaction record
    txn = Transaction(
        id=ext_txn_id,
        organization_id=org.id,
        transaction_id=ext_txn_id,
        customer_id=customer.id,
        customer_email=cust_email,
        amount=payload.amount,
        currency=payload.currency or org.currency or "INR",
        status=txn_status,
        payment_method=method,
        invoice_id=payload.invoice_id,
        subscription_id=payload.subscription_id,
        failure_code=payload.failure_code or ("MANUAL_ENTRY_FAILURE" if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else None),
        failure_reason=payload.failure_reason or ("Manual entry payment failure" if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else None),
        failure_source="merchant_manual",
        error_step="payment_authorization",
        transaction_time=parsed_dt,
        created_at=parsed_dt,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)

    # 5. Create PaymentAttempt
    attempt = PaymentAttempt(
        transaction_id=txn.id,
        attempt_number=1,
        status=AttemptStatus.FAILED if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else AttemptStatus.SUCCESS,
        error_code=txn.failure_code,
        error_description=txn.failure_reason,
        created_at=parsed_dt,
    )
    db.add(attempt)
    await db.flush()

    # 6. If Failed, run recovery analysis engine
    if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED]:
        await recover_transaction(
            transaction_id=txn.id,
            db=db,
            actor=f"USER:{membership.user_id}",
        )

    # 7. Audit log
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    latest_audit = (
        await db.execute(
            select(AuditLog).where(AuditLog.organization_id == org.id).order_by(desc(AuditLog.created_at)).limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"

    audit_state_after = {
        "transaction_id": txn.id,
        "amount": txn.amount,
        "currency": txn.currency,
        "status": txn.status.value,
        "customer_email": cust_email,
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="TRANSACTION_MANUALLY_CREATED",
        entity_name="Transaction",
        entity_id=txn.id,
        actor=f"USER:{membership.user_id}",
        state_after=audit_state_after,
        timestamp_iso=now_iso,
    )

    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="Transaction",
        entity_id=txn.id,
        event_type="TRANSACTION_MANUALLY_CREATED",
        actor=f"USER:{membership.user_id}",
        state_before={},
        state_after=audit_state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Manually registered transaction {txn.id} for {cust_email} ({txn.amount} {txn.currency})",
        created_at=now_dt,
    )
    db.add(audit_entry)

    await db.commit()
    await db.refresh(txn)

    return APIResponse(
        message="Transaction created successfully",
        data=TransactionResponse.model_validate(txn),
    )


def sanitize_csv_formula_injection(value: Any) -> Any:
    """Neutralize potential CSV formula injection (=, +, -, @, \\t, \\r)."""
    if isinstance(value, str) and value:
        stripped = value.lstrip()
        if stripped.startswith(("=", "+", "-", "@", "\t", "\r")):
            return f"'{value}"
    return value


@router.post("/preview-csv", response_model=APIResponse[CSVPreviewResponse])
async def preview_csv_import(
    file: UploadFile = File(...),
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Parse CSV, validate required columns, detect duplicate transaction IDs
    (both within file and in organization), validate amounts and timestamps,
    and generate a structured preview summary.
    """
    org, _ = org_context

    # 1. Validate file extension
    filename = file.filename or ""
    if not any(filename.lower().endswith(ext) for ext in [".csv", ".tsv", ".txt"]):
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV or TSV files are permitted.",
            error_code="INVALID_FILE_TYPE",
        )

    # 2. Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise RecoverAIException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum limit of 10MB.",
            error_code="FILE_TOO_LARGE",
        )

    try:
        text_content = content.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text_content))
    except Exception as e:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read CSV file: {str(e)}",
            error_code="INVALID_CSV",
        )

    raw_headers = list(reader.fieldnames or [])
    fieldnames = [f.strip().lower() for f in raw_headers]
    
    has_txn_id = any(f in ["transaction_id", "txnid", "id", "payment_id"] for f in fieldnames)
    has_amount = any(f in ["amount", "value", "total"] for f in fieldnames)
    has_status = any(f in ["status", "payment_status", "state"] for f in fieldnames)
    has_timestamp = any(f in ["timestamp", "date", "created_at", "time"] for f in fieldnames)

    # Fetch existing transaction IDs for this org to detect cross-system duplicates
    existing_txn_ids_res = await db.execute(
        select(Transaction.transaction_id, Transaction.id).where(Transaction.organization_id == org.id)
    )
    existing_org_txn_ids = set()
    for row in existing_txn_ids_res.all():
        if row[0]: existing_org_txn_ids.add(str(row[0]).strip().lower())
        if row[1]: existing_org_txn_ids.add(str(row[1]).strip().lower())

    seen_file_txn_ids = set()
    valid_rows = []
    invalid_rows = []
    duplicate_rows = []
    preview_raw_rows = []
    errors = []
    total_detected = 0

    for idx, row in enumerate(reader, start=1):
        total_detected += 1
        if len(preview_raw_rows) < 10:
            preview_raw_rows.append({k: (v.strip() if v else "") for k, v in row.items() if k})

        clean_row = {k.strip().lower(): (v.strip() if v else "") for k, v in row.items() if k}
        
        txn_id = clean_row.get("transaction_id") or clean_row.get("txnid") or clean_row.get("id") or clean_row.get("payment_id")
        amount_str = clean_row.get("amount") or clean_row.get("value") or clean_row.get("total")
        status_val = clean_row.get("status") or clean_row.get("payment_status") or clean_row.get("state") or "FAILED"
        timestamp_str = clean_row.get("timestamp") or clean_row.get("date") or clean_row.get("created_at") or clean_row.get("time")
        
        cust_email = clean_row.get("customer_email") or clean_row.get("email") or ""
        cust_id = clean_row.get("customer_id") or clean_row.get("customer") or ""
        failure_code = clean_row.get("failure_code") or ""
        failure_reason = clean_row.get("failure_reason") or clean_row.get("reason") or clean_row.get("failure_code") or ""
        payment_method = clean_row.get("payment_method") or clean_row.get("method") or "CARD"
        currency = clean_row.get("currency") or org.currency or "INR"
        invoice_id = clean_row.get("invoice_id") or ""
        subscription_id = clean_row.get("subscription_id") or ""

        # 1. Validate transaction_id
        if not txn_id:
            errors.append(f"Row {idx}: Missing required 'transaction_id'")
            invalid_rows.append(clean_row)
            continue

        txn_id_norm = txn_id.lower()

        # 2. Check Duplicates (both inside file and existing org records)
        if txn_id_norm in seen_file_txn_ids:
            errors.append(f"Row {idx}: Duplicate transaction_id '{txn_id}' within CSV file")
            duplicate_rows.append(clean_row)
            continue
        if txn_id_norm in existing_org_txn_ids:
            errors.append(f"Row {idx}: Transaction '{txn_id}' already exists in workspace")
            duplicate_rows.append(clean_row)
            continue

        seen_file_txn_ids.add(txn_id_norm)

        # 3. Validate Amount
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be > 0")
        except (ValueError, TypeError):
            errors.append(f"Row {idx}: Invalid numeric amount '{amount_str}'")
            invalid_rows.append(clean_row)
            continue

        # 4. Validate Timestamp
        parsed_dt = parse_flexible_timestamp(timestamp_str)
        if not parsed_dt:
            errors.append(f"Row {idx}: Invalid date/timestamp '{timestamp_str}'")
            invalid_rows.append(clean_row)
            continue

        valid_rows.append({
            "transaction_id": txn_id,
            "customer_id": cust_id or f"cust_{uuid.uuid4().hex[:8]}",
            "customer_email": cust_email,
            "amount": amount,
            "currency": currency.upper(),
            "status": status_val.upper(),
            "failure_code": failure_code,
            "failure_reason": failure_reason or ("Payment failed at gateway" if "FAIL" in status_val.upper() else ""),
            "payment_method": payment_method.upper(),
            "timestamp": parsed_dt.isoformat(),
            "invoice_id": invoice_id,
            "subscription_id": subscription_id,
        })

    return APIResponse(
        message="CSV preview generated successfully",
        data=CSVPreviewResponse(
            headers_detected=raw_headers,
            preview_rows=preview_raw_rows,
            rows_detected=total_detected,
            valid_rows_count=len(valid_rows),
            invalid_rows_count=len(invalid_rows),
            duplicate_rows_count=len(duplicate_rows),
            sample_rows=valid_rows[:15],
            errors=errors[:30],
        ),
    )


@router.post("/import-csv", response_model=APIResponse[CSVImportSummaryResponse])
async def import_csv_transactions(
    payload: CSVImportRequest,
    org_context: tuple = Depends(require_write_access),
    db: AsyncSession = Depends(get_db),
):
    """
    Commit validated CSV transaction batch into the authenticated organization,
    link/create customers, and run autonomous recovery analysis on all failed transactions.
    """
    org, membership = org_context

    # Cap max rows per batch to prevent server exhaustion
    if len(payload.rows) > 5000:
        raise RecoverAIException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 5,000 transactions per import.",
            error_code="BATCH_SIZE_EXCEEDED",
        )

    imported_count = 0
    failed_recoveries = 0
    skipped_count = 0
    duplicate_count = 0
    errors = []

    for row in payload.rows:
        try:
            # Check duplicate against existing org transactions
            existing_txn = (
                await db.execute(
                    select(Transaction).where(
                        Transaction.organization_id == org.id,
                        or_(Transaction.id == row.transaction_id, Transaction.transaction_id == row.transaction_id),
                    )
                )
            ).scalar_one_or_none()
            if existing_txn:
                duplicate_count += 1
                skipped_count += 1
                continue

            # Customer resolution
            email = row.customer_email.strip().lower() if row.customer_email and "@" in row.customer_email else f"{row.customer_id or row.transaction_id}@workspace.local"
            name = row.customer_id or email.split("@")[0].capitalize()

            cust_res = await db.execute(
                select(Customer).where(
                    Customer.organization_id == org.id,
                    Customer.email == email,
                )
            )
            customer = cust_res.scalar_one_or_none()
            if not customer:
                customer = Customer(
                    organization_id=org.id,
                    email=email,
                    name=name,
                )
                db.add(customer)
                await db.flush()
                await db.refresh(customer)

            # Status resolution
            raw_st = row.status.upper()
            if "RECOVER" in raw_st:
                txn_status = TransactionStatus.RECOVERED
            elif "CAPTUR" in raw_st or "SUCCESS" in raw_st:
                txn_status = TransactionStatus.CAPTURED
            elif "ABANDON" in raw_st:
                txn_status = TransactionStatus.ABANDONED
            elif "AUTH" in raw_st:
                txn_status = TransactionStatus.AUTHORIZED
            else:
                txn_status = TransactionStatus.FAILED

            # Method resolution
            method = PaymentMethod.CARD
            try:
                method = PaymentMethod(row.payment_method.upper())
            except Exception:
                method = PaymentMethod.CARD

            parsed_dt = parse_flexible_timestamp(row.timestamp) or datetime.now(timezone.utc)

            txn = Transaction(
                id=row.transaction_id,
                organization_id=org.id,
                transaction_id=row.transaction_id,
                customer_id=customer.id,
                customer_email=email,
                amount=row.amount,
                currency=row.currency or org.currency or "INR",
                status=txn_status,
                payment_method=method,
                invoice_id=row.invoice_id,
                subscription_id=row.subscription_id,
                failure_code=row.failure_code or ("CSV_IMPORT_FAILURE" if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else None),
                failure_reason=row.failure_reason or ("Imported failure event" if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else None),
                failure_source="gateway",
                error_step="payment_authorization",
                transaction_time=parsed_dt,
                created_at=parsed_dt,
            )
            db.add(txn)
            await db.flush()

            attempt = PaymentAttempt(
                transaction_id=txn.id,
                attempt_number=1,
                status=AttemptStatus.FAILED if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED] else AttemptStatus.SUCCESS,
                error_code=txn.failure_code,
                error_description=txn.failure_reason,
                created_at=parsed_dt,
            )
            db.add(attempt)
            await db.flush()

            # Automatic Analysis on failed transactions
            if txn_status in [TransactionStatus.FAILED, TransactionStatus.ABANDONED]:
                await recover_transaction(
                    transaction_id=txn.id,
                    db=db,
                    actor=f"CSV_IMPORT:{membership.user_id}",
                )
                failed_recoveries += 1

            imported_count += 1

        except Exception as e:
            errors.append(f"Failed to import {row.transaction_id}: {str(e)}")
            skipped_count += 1
            continue

    # Record Audit Log for the CSV Import Event
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    latest_audit = (
        await db.execute(
            select(AuditLog).where(AuditLog.organization_id == org.id).order_by(desc(AuditLog.created_at)).limit(1)
        )
    ).scalar_one_or_none()
    prev_hash = latest_audit.sha256_hash if latest_audit else "GENESIS_RECOVERAI"

    audit_state_after = {
        "imported_count": imported_count,
        "failed_recoveries_triggered": failed_recoveries,
        "duplicate_count": duplicate_count,
        "skipped_count": skipped_count,
    }
    sha_hash = calculate_hash(
        prev_hash=prev_hash,
        event_type="CSV_TRANSACTIONS_IMPORTED",
        entity_name="Organization",
        entity_id=org.id,
        actor=f"USER:{membership.user_id}",
        state_after=audit_state_after,
        timestamp_iso=now_iso,
    )

    audit_entry = AuditLog(
        organization_id=org.id,
        entity_name="Organization",
        entity_id=org.id,
        event_type="CSV_TRANSACTIONS_IMPORTED",
        actor=f"USER:{membership.user_id}",
        state_before={},
        state_after=audit_state_after,
        prev_hash=prev_hash,
        sha256_hash=sha_hash,
        timestamp_iso=now_iso,
        notes=f"Imported {imported_count} transactions from CSV; triggered {failed_recoveries} recovery cases.",
        created_at=now_dt,
    )
    db.add(audit_entry)
    await db.commit()

    return APIResponse(
        message=f"Successfully imported {imported_count} transactions.",
        data=CSVImportSummaryResponse(
            imported_count=imported_count,
            failed_recoveries_triggered=failed_recoveries,
            skipped_count=skipped_count,
            duplicate_count=duplicate_count,
            errors=errors[:15],
        ),
    )


@router.get("", response_model=APIResponse[List[TransactionResponse]])
async def list_transactions(
    status_filter: Optional[TransactionStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    failure_reason: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|amount|status|transaction_id)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions strictly scoped to the authenticated organization with
    search, status filter, failure reason filter, date range filter, sort, and pagination.
    """
    org, _ = org_context
    query = select(Transaction).where(Transaction.organization_id == org.id)

    if status_filter:
        query = query.where(Transaction.status == status_filter)

    if failure_reason and failure_reason != "ALL":
        query = query.where(Transaction.failure_reason.ilike(f"%{failure_reason}%"))

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                Transaction.id.ilike(s),
                Transaction.transaction_id.ilike(s),
                Transaction.customer_email.ilike(s),
                Transaction.customer_id.ilike(s),
                Transaction.failure_code.ilike(s),
                Transaction.failure_reason.ilike(s),
            )
        )

    if date_from:
        dt_from = parse_flexible_timestamp(date_from)
        if dt_from:
            query = query.where(Transaction.created_at >= dt_from)

    if date_to:
        dt_to = parse_flexible_timestamp(date_to)
        if dt_to:
            query = query.where(Transaction.created_at <= dt_to)

    # Sorting
    sort_column = getattr(Transaction, sort_by, Transaction.created_at)
    query = query.order_by(desc(sort_column) if sort_order == "desc" else asc(sort_column))
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    txns = result.scalars().all()

    return APIResponse(
        message="Transactions retrieved successfully",
        data=[TransactionResponse.model_validate(t) for t in txns],
    )


@router.get("/{transaction_id}", response_model=APIResponse[TransactionResponse])
async def get_transaction(
    transaction_id: str,
    org_context: tuple = Depends(get_current_org_context),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve single transaction strictly scoped to the authenticated organization."""
    org, _ = org_context
    result = await db.execute(
        select(Transaction).where(
            Transaction.organization_id == org.id,
            or_(Transaction.id == transaction_id, Transaction.transaction_id == transaction_id),
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise EntityNotFoundException("Transaction", transaction_id)

    return APIResponse(
        message="Transaction found",
        data=TransactionResponse.model_validate(txn),
    )
