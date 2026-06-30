from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Numeric, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.aggregate import ReviewAggregate
from app.models.review import Review
from app.schemas.chart import (
    CompanySizeCount,
    CompanySizeResponse,
    SentimentPoint,
    SentimentResponse,
    TopicCount,
    TopicSentimentCount,
    TopicSentimentResponse,
    TopicsResponse,
    TrendPoint,
    TrendResponse,
)

router = APIRouter()


@router.get("/trend", response_model=TrendResponse)
async def get_trend(
    company_size: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Aylık ortalama puan trendi. rating=0 scraper hatası — hariç tutulur."""
    month_expr = func.date_trunc("month", Review.date)

    stmt = (
        select(
            month_expr.label("month"),
            func.round(func.avg(Review.rating).cast(Numeric(10, 2)), 2).label("avg_rating"),
            func.count().label("count"),
        )
        .where(Review.rating > 0)
        .group_by(month_expr)
        .order_by(month_expr)
    )

    if company_size:
        stmt = stmt.where(Review.company_size == company_size)
    if topic:
        stmt = stmt.where(Review.topics.contains([topic]))
    if date_from:
        stmt = stmt.where(Review.date >= date_from)
    if date_to:
        stmt = stmt.where(Review.date <= date_to)

    rows = (await db.execute(stmt)).fetchall()
    return TrendResponse(
        data=[TrendPoint(month=r.month, avg_rating=float(r.avg_rating), count=r.count) for r in rows]
    )


@router.get("/topics", response_model=TopicsResponse)
async def get_topics(
    company_size: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Konu dağılımı (toplam review sayısı). Kaynak: review_aggregates."""
    count_expr = func.sum(ReviewAggregate.count)

    stmt = (
        select(ReviewAggregate.topic, count_expr.label("count"))
        .group_by(ReviewAggregate.topic)
        .order_by(count_expr.desc())
    )

    if company_size:
        stmt = stmt.where(ReviewAggregate.company_size == company_size)
    if sentiment:
        stmt = stmt.where(ReviewAggregate.sentiment == sentiment)
    if date_from:
        stmt = stmt.where(ReviewAggregate.month >= date_from)
    if date_to:
        stmt = stmt.where(ReviewAggregate.month <= date_to)

    rows = (await db.execute(stmt)).fetchall()
    return TopicsResponse(data=[TopicCount(topic=r.topic, count=int(r.count)) for r in rows])


@router.get("/sentiment", response_model=SentimentResponse)
async def get_sentiment(
    company_size: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Aylık sentiment dağılımı. Kaynak: reviews (her review bir kez sayılır)."""
    month_expr = func.date_trunc("month", Review.date)
    stmt = (
        select(
            month_expr.label("month"),
            Review.sentiment,
            func.count().label("count"),
        )
        .where(Review.sentiment.isnot(None))
        .group_by(month_expr, Review.sentiment)
        .order_by(month_expr, Review.sentiment)
    )

    if company_size:
        stmt = stmt.where(Review.company_size == company_size)
    if topic:
        stmt = stmt.where(Review.topics.contains([topic]))
    if date_from:
        stmt = stmt.where(Review.date >= date_from)
    if date_to:
        stmt = stmt.where(Review.date <= date_to)

    rows = (await db.execute(stmt)).fetchall()
    return SentimentResponse(
        data=[SentimentPoint(month=r.month, sentiment=r.sentiment, count=int(r.count)) for r in rows]
    )


@router.get("/company-size", response_model=CompanySizeResponse)
async def get_company_size(
    topic: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Şirket büyüklüğüne göre review dağılımı. Kaynak: reviews (her review bir kez sayılır)."""
    stmt = (
        select(Review.company_size, func.count().label("count"))
        .group_by(Review.company_size)
        .order_by(func.count().desc())
    )

    if topic:
        stmt = stmt.where(Review.topics.contains([topic]))
    if sentiment:
        stmt = stmt.where(Review.sentiment == sentiment)
    if date_from:
        stmt = stmt.where(Review.date >= date_from)
    if date_to:
        stmt = stmt.where(Review.date <= date_to)

    rows = (await db.execute(stmt)).fetchall()
    return CompanySizeResponse(
        data=[CompanySizeCount(company_size=r.company_size or "bilinmiyor", count=int(r.count)) for r in rows]
    )


@router.get("/topic-sentiment", response_model=TopicSentimentResponse)
async def get_topic_sentiment(
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Tüm konulardaki sentiment dağılımı (konu mention toplamları). Kaynak: review_aggregates."""
    count_expr = func.sum(ReviewAggregate.count)
    stmt = (
        select(ReviewAggregate.sentiment, count_expr.label("count"))
        .group_by(ReviewAggregate.sentiment)
        .order_by(count_expr.desc())
    )

    if date_from:
        stmt = stmt.where(ReviewAggregate.month >= date_from)
    if date_to:
        stmt = stmt.where(ReviewAggregate.month <= date_to)

    rows = (await db.execute(stmt)).fetchall()
    return TopicSentimentResponse(
        data=[TopicSentimentCount(sentiment=r.sentiment, count=int(r.count)) for r in rows]
    )
