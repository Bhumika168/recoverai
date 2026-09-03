from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.common import APIResponse
from app.exceptions import EntityNotFoundException, ValidationException
from app.logging_config import logger

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("", response_model=APIResponse[CustomerResponse], status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    existing = await db.execute(select(Customer).where(Customer.email == payload.email))
    if existing.scalar_one_or_none():
        raise ValidationException(f"Customer with email '{payload.email}' already exists.")

    customer = Customer(
        email=payload.email,
        phone=payload.phone,
        name=payload.name,
        rzp_customer_id=payload.rzp_customer_id,
        risk_score=payload.risk_score,
        recovery_receptivity_score=payload.recovery_receptivity_score,
        extra_metadata=payload.extra_metadata or {},
    )
    db.add(customer)
    await db.flush()
    await db.refresh(customer)
    logger.info(f"Created customer: {customer.id} ({customer.email})")
    
    return APIResponse(
        message="Customer created successfully",
        data=CustomerResponse.model_validate(customer)
    )


@router.get("", response_model=APIResponse[List[CustomerResponse]])
async def list_customers(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    query = select(Customer).order_by(desc(Customer.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return APIResponse(
        message="Customers retrieved successfully",
        data=[CustomerResponse.model_validate(c) for c in customers]
    )


@router.get("/{customer_id}", response_model=APIResponse[CustomerResponse])
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise EntityNotFoundException("Customer", customer_id)
        
    return APIResponse(
        message="Customer found",
        data=CustomerResponse.model_validate(customer)
    )
