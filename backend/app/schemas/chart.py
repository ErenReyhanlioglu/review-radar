from datetime import date
from typing import Optional
from pydantic import BaseModel


class TrendPoint(BaseModel):
    month: date
    avg_rating: float
    count: int


class TopicCount(BaseModel):
    topic: str
    count: int


class SentimentPoint(BaseModel):
    month: date
    sentiment: str
    count: int


class CompanySizeCount(BaseModel):
    company_size: str
    count: int


class TrendResponse(BaseModel):
    data: list[TrendPoint]


class TopicsResponse(BaseModel):
    data: list[TopicCount]


class SentimentResponse(BaseModel):
    data: list[SentimentPoint]


class CompanySizeResponse(BaseModel):
    data: list[CompanySizeCount]


class TopicSentimentCount(BaseModel):
    sentiment: str
    count: int


class TopicSentimentResponse(BaseModel):
    data: list[TopicSentimentCount]
