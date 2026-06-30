import logging
import uuid
from datetime import date

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aggregate import ReviewAggregate
from app.models.review import Review

logger = logging.getLogger(__name__)


def _month_start(d: date) -> date:
    return d.replace(day=1)


async def save_reviews(
    reviews: list[dict],
    enrichments: dict[str, dict],
    db: AsyncSession,
) -> None:
    """
    Inserts enriched reviews into `reviews` table and
    upserts counts into `review_aggregates`.
    """
    for r in reviews:
        rid = r["reviewId"]
        enr = enrichments.get(rid, {})
        raw_date = r.get("date")
        review_date = date.fromisoformat(raw_date) if raw_date else None

        # Insert into reviews
        review_row = Review(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, rid),
            review_id=rid,
            likes=r.get("likes"),
            dislikes=r.get("dislikes"),
            rating=r.get("starRating"),
            date=review_date,
            company_size=r.get("company_size"),
            topics=enr.get("topics", []),
            sentiment=enr.get("sentiment", "nötr"),
            summary=enr.get("summary", ""),
        )
        db.add(review_row)

        # Upsert aggregates: one row per (month, topic, sentiment, company_size)
        if review_date:
            month = _month_start(review_date)
            sentiment = enr.get("sentiment", "nötr")
            company_size = r.get("company_size") or "bilinmiyor"
            topics = enr.get("topics") or ["genel olumlu"]

            for topic in topics:
                stmt = (
                    pg_insert(ReviewAggregate)
                    .values(
                        month=month,
                        topic=topic,
                        sentiment=sentiment,
                        company_size=company_size,
                        count=1,
                    )
                    .on_conflict_do_update(
                        index_elements=["month", "topic", "sentiment", "company_size"],
                        set_={"count": ReviewAggregate.count + 1},
                    )
                )
                await db.execute(stmt)

    await db.commit()
    logger.info("%d review kaydedildi.", len(reviews))
