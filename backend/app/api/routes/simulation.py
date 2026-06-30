import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.jobs.monthly_pipeline import _INITIAL_DATE, _get_simulated_date, _set_simulated_date, run_pipeline
from app.models.config import SystemConfig
from app.models.report import Report
from app.schemas.simulation import AdvanceResponse, SimulationStatus

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_config(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(SystemConfig.value).where(SystemConfig.key == key))
    return result.scalar_one_or_none()


async def _pipeline_task() -> None:
    """Background task creates its own DB session — request session may close before task finishes."""
    from app.api.deps import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            await run_pipeline(db)
        except Exception:
            logger.exception("Pipeline hatası")


@router.post("/advance", response_model=AdvanceResponse)
async def advance_simulation(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    running = await _get_config(db, "pipeline_running")
    if running == "true":
        current = await _get_simulated_date(db)
        return AdvanceResponse(status="zaten_çalışıyor", simulated_date=current)

    # Set running=true BEFORE starting background task so the first poll sees it
    stmt = (
        pg_insert(SystemConfig)
        .values(key="pipeline_running", value="true")
        .on_conflict_do_update(index_elements=["key"], set_={"value": "true"})
    )
    await db.execute(stmt)
    await db.commit()

    background_tasks.add_task(_pipeline_task)
    current = await _get_simulated_date(db)
    return AdvanceResponse(status="başladı", simulated_date=current)


@router.get("/status", response_model=SimulationStatus)
async def get_simulation_status(db: AsyncSession = Depends(get_db)):
    simulated_date_str = await _get_config(db, "simulated_date")
    last_run_str = await _get_config(db, "pipeline_last_run")
    running = await _get_config(db, "pipeline_running")

    return SimulationStatus(
        simulated_date=date.fromisoformat(simulated_date_str) if simulated_date_str else _INITIAL_DATE,
        pipeline_last_run=date.fromisoformat(last_run_str) if last_run_str else None,
        is_running=running == "true",
    )


@router.post("/reset")
async def reset_simulation(db: AsyncSession = Depends(get_db)):
    # Delete only generated reports — reviews, aggregates, and Qdrant are preserved
    await db.execute(delete(Report))

    # Reset simulation state
    await _set_simulated_date(db, _INITIAL_DATE)
    stmt = (
        pg_insert(SystemConfig)
        .values(key="pipeline_running", value="false")
        .on_conflict_do_update(index_elements=["key"], set_={"value": "false"})
    )
    await db.execute(stmt)
    await db.commit()

    return {"status": "sıfırlandı", "simulated_date": _INITIAL_DATE.isoformat()}
