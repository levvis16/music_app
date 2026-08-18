from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.database import get_db
from app.database.models import Venue
from app.services import QueueService, OrderService, broadcast_queue_update
from app.database.schemas import (
    OrderCreate, OrderResponse, OrderStatus,
    QueueResponse, CurrentTrack, QueueItem, TrackAdd
)

router = APIRouter(prefix="/admin", tags=['admin'])

@router.get("/queue", response_model=QueueResponse)
async def get_queue(venue_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    queue = await queue_service.get_all()
    current = await queue_service.get_current()
    
    venue = await db.get(Venue, venue_id)
    max_queue_size = venue.max_queue_size if venue else 50  
    
    queue_with_positions = []
    for idx, item in enumerate(queue):
        queue_with_positions.append({
            **item,
            "position": idx + 1
        })
    
    return {
        "current": current,
        "queue": queue_with_positions, 
        "total_in_queue": len(queue),
        "max_queue_size": max_queue_size
    }

@router.post("/queue")
async def add_track_to_queue(venue_id: int, track_data: TrackAdd, db: AsyncSession = Depends(get_db)):
    order_service = OrderService(db)
    order = await order_service.create_order(
        venue_id = venue_id,
        user_fingerprint= "admin_manual",
        song_data=track_data.dict(),
        price=0
    )

    order.status = OrderStatus.PAID
    await db.commit()
    await db.refresh(order)
    
    queue_service = QueueService(venue_id)
    await queue_service.push(order.id, track_data.dict())  # <-- ПРЕВРАЩАЕМ В СЛОВАРЬ
    
    await broadcast_queue_update(venue_id)
    
    return {"status": "added", "order_id": order.id}



@router.delete("/queue/{order_id}")
async def remove_from_queue(venue_id: int, order_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    removed = await queue_service.remove_by_order_id(order_id)

    if not removed:
        raise HTTPException(status_code=404, detail="order not in queue")

    await broadcast_queue_update(venue_id)
    return {"status": "removed"}

@router.delete("/queue/clear")
async def clear_queue(venue_id: int):
    queue_service = QueueService(venue_id)
    removed = await queue_service.clear()

    await broadcast_queue_update(venue_id)
    return {"status": "cleared"}



@router.post("/guest/order")
async def guest_order(request: Request, order_data: OrderCreate, db: AsyncSession = Depends(get_db)):
    import hashlib

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    fingerprint = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()

    order_service = OrderService(db)
    order = await order_service.create_order(
        venue_id=order_data.venue_id,
        user_fingerprint=fingerprint,
        song_data={
            "title": order_data.song_title,
            "artist": order_data.song_artist,
            "provider": order_data.song_provider,
            #"external_id": order_data.song_external_id,
            "duration": order_data.song_duration
        },
        price=order_data.price
    )

    return {
        "order_id": order.id,
        "order_status": order.status,
        "message": "order created, waiting for poayment"
    }

@router.post("/guest/order/{order_id}/pay")
async def pay_order(order_id: int, db: AsyncSession = Depends(get_db)):
    order_service = OrderService(db)
    order = await order_service.get_order(order_id)

    if not order: 
        raise HTTPException(status_code=404, detail="order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="order already paid or cancelled")

    return {
        "order_id": order.id,
        "payment_url": f"/payment/mock/{order.id}",
        "amount": order.price_paid
    }

@router.post("/guest/orders")
async def get_my_orders(request: Request, db: AsyncSession = Depends(get_db)):
    import hashlib

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    fingerprint = hashlib.md5(f"{client_ip}:{user_agent}".encode()).hexdigest()

    order_service = OrderService(db)
    orders = await order_service.get_orders_by_user(fingerprint)

    return orders

@router.get("/guest/order/{order_id}/status")
async def get_order_status(order_id: int, db: AsyncSession = Depends(get_db)):
    order_service = OrderService(db)
    order = await order_service.get_order(order_id)

    if not order:
        raise HTTPException(status_code=404, detail="order not found")

    return {
        "order_id": order.id,
        "status": order.status,
        "song_title": order.song_title,
        "price_paid": order.price_paid
    }

