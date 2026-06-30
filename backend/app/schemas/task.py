import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class TaskCreate(BaseModel):
    prompt: str
    target_date: date


class TaskResponse(BaseModel):
    id: uuid.UUID
    prompt: str
    target_date: date
    status: str
    result: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
