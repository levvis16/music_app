import asyncio
from datetime import datetime
from app.services import QueueService, OrderService, broadcast_queue_update
from app.database.database import async_session

async def check_and_advance_queue(venue_id: int):
    queue_service = QueueService(venue_id)
    current = await queue_service.get_current()

    if not current:
        return

    started_at = current.get("started_at")
    duration = current.get("song_duration", 0)

    if not started_at:
        return

    elapsed = (datetime.now() - datetime.isoformat(started_at)).total_seconds()
    remaining = max(0, duration - elapsed)

    if remaining <= 0:
        async with async_session() as db:
            order_service = OrderService(db)
            order_id = current.get("order_id")
            if order_id:
                await order_service.mark_as_played(order_id)

            next_track = await queue_service.pop_next()

            await broadcast_queue_update(venue_id)
            print(f"автоматически переключил трек {venue_id}")
            