from fastapi import APIRouter, Depends, WebSocket, HTTPException
from database.schemas import QueueResponse
from database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services import QueueService, OrderService, OrderStatus
router = APIRouter(prefix="admin", tags=['admin'])

@router.get("/queue", response_model=QueueResponse)
async def get_queue(venue_id: int):
    queue_service = QueueService(venue_id)
    queue = await queue_service.get_all()
    current = await queue_service.get_current()

    return {
        "current": current,
        "queue": queue,
        "total_in_queue": len(queue)
    }

@router.post("/queue")
async def add_track_to_queue(venue_id: int, track_data: dict, db: AsyncSession = Depends(get_db)):
    order_service = OrderService(db)
    order = await order_service.create_order(
        venue_id = venue_id,
        user_fingerprint= "admin_manual",
        song_data=track_data,
        price=0
    )

    order.status = OrderStatus.PAID
    await db.commit()
    await db.refresh(order)

    queue_service = QueueService(venue_id)
    await queue_service.push(order.id, track_data)

    return {"status": "added", "order_id": order.id}

@router.delete("/queue/{order_id}")
async def remove_track(venue_id: int, order_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    removed = await queue_service.remove_by_order_id(order_id)

    if not removed:
        raise HTTPException(status_code=404, detail="order not in queue")

    return {"status": "removed"}

@router.delete("/queue/clear")
async def clear_queue(venue_id: int):
    queue_service = QueueService(venue_id)
    removed = await queue_service.clear()

    return {"status": "cleared"}