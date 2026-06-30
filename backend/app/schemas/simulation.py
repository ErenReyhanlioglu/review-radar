from datetime import date
from typing import Optional
from pydantic import BaseModel


class SimulationStatus(BaseModel):
    simulated_date: Optional[date]
    pipeline_last_run: Optional[date]
    is_running: bool


class AdvanceResponse(BaseModel):
    status: str
    simulated_date: Optional[date]
