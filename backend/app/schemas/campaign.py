from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.models.campaign import CampaignChannel


class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    target_segment: str = "ALL_FAILURES"
    channel: CampaignChannel = CampaignChannel.MULTI_CHANNEL
    is_active: bool = True
    configuration: Optional[Dict[str, Any]] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_segment: Optional[str] = None
    channel: Optional[CampaignChannel] = None
    is_active: Optional[bool] = None
    configuration: Optional[Dict[str, Any]] = None


class CampaignResponse(CampaignBase):
    id: str
    total_targeted_count: int
    total_recovered_count: int
    total_revenue_recovered: float
    recovery_rate: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
