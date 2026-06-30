import logging
from datetime import date

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemConfig
from app.services.aggregator import save_reviews
from app.services.embedder import embed_reviews
from app.services.loader import load_reviews_for_month
from app.services.processor import enrich_reviews
from app.services.reporter import generate_report
from app.services.vector_store import ensure_collection, upsert_reviews

logger = logging.getLogger(__name__)

_INITIAL_DATE = date(2025, 7, 1)


async def _get_simulated_date(db: AsyncSession) -> date:
    result = await db.execute(
        select(SystemConfig.value).where(SystemConfig.key == "simulated_date")
    )
    row = result.scalar_one_or_none()
    return date.fromisoformat(row) if row else _INITIAL_DATE


async def _set_simulated_date(db: AsyncSession, d: date) -> None:
    stmt = (
        pg_insert(SystemConfig)
        .values(key="simulated_date", value=d.isoformat())
        .on_conflict_do_update(
            index_elements=["key"],
            set_={"value": d.isoformat()},
        )
    )
    await db.execute(stmt)
    await db.commit()


async def _set_pipeline_running(db: AsyncSession, running: bool) -> None:
    stmt = (
        pg_insert(SystemConfig)
        .values(key="pipeline_running", value=str(running).lower())
        .on_conflict_do_update(
            index_elements=["key"],
            set_={"value": str(running).lower()},
        )
    )
    await db.execute(stmt)
    await db.commit()


def _next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


async def run_pipeline(db: AsyncSession) -> dict:
    """
    Advances simulated_date by one month and processes that month's reviews.
    Returns a summary dict.
    """
    await _set_pipeline_running(db, True)
    try:
        current = await _get_simulated_date(db)
        new_date = _next_month(current)
        logger.info("Pipeline başladı: %s → %s", current, new_date)

        # 1. Load unprocessed reviews for the month
        reviews = await load_reviews_for_month(new_date, db)
        logger.info("Yüklenecek review sayısı: %d", len(reviews))

        if reviews:
            # 2. Enrich via Claude Batch API
            enrichments = await enrich_reviews(reviews)

            # 3. Embed via OpenAI
            embeddings = await embed_reviews(reviews)

            # 4. Upsert into Qdrant
            await ensure_collection()
            await upsert_reviews(reviews, enrichments, embeddings)

            # 5. Save to PostgreSQL (reviews + aggregates)
            await save_reviews(reviews, enrichments, db)

        # 6. Advance simulated_date
        await _set_simulated_date(db, new_date)

        # 7. Generate monthly report (current = the month we just processed)
        await generate_report(current, db)

        logger.info("Pipeline tamamlandı. Yeni tarih: %s", new_date)

        return {
            "processed": len(reviews),
            "new_simulated_date": new_date.isoformat(),
        }
    except Exception:
        logger.exception("Pipeline içi hata (asıl sebep)")
        raise
    finally:
        # Rollback any aborted transaction before writing pipeline_running=false
        try:
            await db.rollback()
        except Exception:
            pass
        await _set_pipeline_running(db, False)
