from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import charts, chat, reports, tasks, simulation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: clear any stuck pipeline_running flag from a previous crash/reload
    from app.api.deps import AsyncSessionLocal
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from app.models.config import SystemConfig
    async with AsyncSessionLocal() as db:
        stmt = (
            pg_insert(SystemConfig)
            .values(key="pipeline_running", value="false")
            .on_conflict_do_update(index_elements=["key"], set_={"value": "false"})
        )
        await db.execute(stmt)
        await db.commit()
    yield


app = FastAPI(title="Review Radar", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation.router, prefix="/simulation", tags=["simulation"])
app.include_router(charts.router, prefix="/charts", tags=["charts"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])


@app.get("/health")
async def health():
    return {"status": "ok"}


