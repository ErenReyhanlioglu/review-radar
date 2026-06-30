import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.review import Review

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "reviews_clean.json"


def _prev_month_start(d: date) -> date:
    """Returns the first day of the month before d."""
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def _load_json() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


async def load_reviews_for_month(simulated_date: date, db: AsyncSession) -> list[dict]:
    """
    Returns unprocessed reviews for the month ending at simulated_date.
    date_from = first day of previous month (relative to simulated_date)
    date_to   = simulated_date (exclusive upper bound)
    """
    date_from = _prev_month_start(simulated_date)
    date_to = simulated_date

    all_reviews = _load_json()

    # Filter by date range
    in_range = [
        r for r in all_reviews
        if r.get("date") and date_from <= date.fromisoformat(r["date"]) < date_to
    ]

    if not in_range:
        return []

    # Exclude already-processed review_ids
    ids_in_range = [r["reviewId"] for r in in_range]
    result = await db.execute(
        select(Review.review_id).where(Review.review_id.in_(ids_in_range))
    )
    already_done = {row[0] for row in result.fetchall()}

    return [r for r in in_range if r["reviewId"] not in already_done]
