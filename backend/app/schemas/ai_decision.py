from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class AIDecisionBase(BaseModel):
    case_id: str
    failure_category: str
    root_cause_explanation: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    recovery_probability: float = Field(ge=0.0, le=1.0)
    reasoning_steps: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    recommended_action: str
    recommended_delay_minutes: int = 0
    recommended_channel: str = "GATEWAY"
    model_name: str = "gemini-2.5-flash"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0


class AIDecisionCreate(AIDecisionBase):
    pass


class AIDecisionResponse(AIDecisionBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
