from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    row = Task(prompt=task.prompt, target_date=task.target_date)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    return result.scalars().all()
