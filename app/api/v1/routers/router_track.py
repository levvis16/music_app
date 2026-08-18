from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.database.schemas import SongProvider, OrderResponse, OrderStatus
from app.services import QueueService, OrderService, broadcast_queue_update

router = APIRouter(prefix="/api/v1/track", tags=["track"])

@router.post("/{venue_id}/skip")
async def skip_current(venue_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    order_service = OrderService(db)

    current = await queue_service.get_current()
    if current:
        await order_service.mark_as_skipped(current["order_id"])

    next_track = await queue_service.pop_next()

    await broadcast_queue_update(venue_id)

    return {"status": "skipped", "next": next_track}

@router.post("/{venue_id}/pause")
async def pause_track(venue_id: int):
    return {"status": "paused"}

@router.post("/{venue_id}/resume")
async def resume_track(venue_id: int):
    return {"status": "resumed"}

@router.get("/{venue_id}/history", response_model=List[OrderResponse])
async def get_history(venue_id: int, db: AsyncSession = Depends(get_db), limit: int = 50):
    order_service = OrderService(db)
    orders = await order_service.get_orders_by_venue(
        venue_id=venue_id,
        status=OrderStatus.PLAYED,
        limit=limit,
    )

    return orders