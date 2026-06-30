import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.report import Report
from app.models.task import Task
from app.services import mailer, reporter

router = APIRouter()


class PmSection(BaseModel):
    prompt: str
    answer: str
    charts: list[Any] = []


class ReportResponse(BaseModel):
    month: date
    content: str
    pm_sections: list[PmSection] = []

    model_config = {"from_attributes": True}


class AppendRequest(BaseModel):
    prompt: str
    answer: str
    chart_data: list[Any] = []


class SendRequest(BaseModel):
    recipients: list[str]
    pm_email: str | None = None


async def _get_pm_sections(month_start: date, db: AsyncSession) -> list[PmSection]:
    tasks = (
        await db.execute(
            select(Task)
            .where(
                Task.target_date == month_start,
                Task.status == "tamamlandı",
                Task.result.isnot(None),
            )
            .order_by(Task.created_at)
        )
    ).scalars().all()
    return [
        PmSection(prompt=t.prompt, answer=t.result or "", charts=t.chart_data or [])
        for t in tasks
    ]


@router.get("", response_model=list[ReportResponse])
async def list_reports(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Report).order_by(Report.month.desc()))).scalars().all()
    return [ReportResponse(month=r.month, content=r.content) for r in rows]


@router.get("/latest", response_model=ReportResponse)
async def get_latest_report(db: AsyncSession = Depends(get_db)):
    row = (
        await db.execute(select(Report).order_by(Report.month.desc()).limit(1))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Henüz rapor yok.")
    pm_sections = await _get_pm_sections(row.month, db)
    return ReportResponse(month=row.month, content=row.content, pm_sections=pm_sections)


@router.post("/{month}/append", response_model=ReportResponse)
async def append_to_report(month: date, body: AppendRequest, db: AsyncSession = Depends(get_db)):
    month_start = month.replace(day=1)

    # Save as already-completed task — no re-execution
    task = Task(
        id=uuid.uuid4(),
        prompt=body.prompt,
        target_date=month_start,
        status="tamamlandı",
        result=body.answer,
        chart_data=body.chart_data or [],
    )
    db.add(task)
    await db.commit()

    row = (
        await db.execute(select(Report).where(Report.month == month_start))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Bu aya ait rapor bulunamadı.")

    pm_sections = await _get_pm_sections(month_start, db)
    return ReportResponse(month=month_start, content=row.content, pm_sections=pm_sections)


@router.post("/{month}/send")
async def send_report_email(month: date, body: SendRequest, db: AsyncSession = Depends(get_db)):
    month_start = month.replace(day=1)
    row = (
        await db.execute(select(Report).where(Report.month == month_start))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Bu aya ait rapor bulunamadı.")
    success = await mailer.send_report(month_start, row.content, recipients=body.recipients, pm_email=body.pm_email)
    return {"success": success}


@router.get("/{month}", response_model=ReportResponse)
async def get_report(month: date, db: AsyncSession = Depends(get_db)):
    month_start = month.replace(day=1)
    row = (
        await db.execute(select(Report).where(Report.month == month_start))
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Bu aya ait rapor bulunamadı.")
    pm_sections = await _get_pm_sections(month_start, db)
    return ReportResponse(month=month_start, content=row.content, pm_sections=pm_sections)
