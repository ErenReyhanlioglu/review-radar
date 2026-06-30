from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.chat import ChatResponse, ChartPayload, ChatRequest
from app.services import chat as chat_svc

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await chat_svc.answer(request.message, db, simulated_date=request.simulated_date)
    return ChatResponse(
        answer=result.answer,
        chart_data=[ChartPayload(**c) for c in result.charts],
    )
