from typing import Optional

from pydantic import BaseModel


class ChartPayload(BaseModel):
    type: str  # "trend" | "breakdown" | "examples"
    group_by: Optional[str] = None  # breakdown için: "topic" | "sentiment" | "company_size"
    title: Optional[str] = None
    data: list[dict]


class ChatRequest(BaseModel):
    message: str
    simulated_date: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    chart_data: list[ChartPayload] = []
