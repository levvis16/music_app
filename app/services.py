import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis
from app.websocket.websocket import manager

from app.database.models import Order, OrderStatus
from app.redis_client import get_redis


class QueueService:
    def __init__(self, venue_id: int, redis: Optional[Redis] = None):
        self.venue_id = venue_id
        self.redis = redis
        self.queue_key = f"queue:venue:{venue_id}"
        self.current_key = f"current:venue:{venue_id}"
    
    async def _get_redis(self) -> Redis:
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis
    
    async def push(self, order_id: int, song_data: Dict[str, Any]) -> int:
        redis = await self._get_redis()
        item = json.dumps({
            "order_id": order_id,
            "song_title": song_data.get("title"),
            "song_artist": song_data.get("artist"),
            #"song_external_id": song_data.get("external_id"),
            "song_provider": song_data.get("provider"),
            "song_duration": song_data.get("duration")
        })
        return await redis.rpush(self.queue_key, item)
    
    async def pop_next(self) -> Optional[Dict[str, Any]]:
        redis = await self._get_redis()  # <-- добавил
        next_item = await redis.lpop(self.queue_key)
        if next_item:
            data = json.loads(next_item)
            await redis.setex(self.current_key, 3600, next_item)
            return data
        return None
    
    async def get_all(self) -> List[Dict[str, Any]]:
        redis = await self._get_redis()
        items = await redis.lrange(self.queue_key, 0, -1)
        return [json.loads(item) for item in items]
    
    async def get_current(self) -> Optional[Dict[str, Any]]:
        redis = await self._get_redis()  # <-- добавил
        current = await redis.get(self.current_key)
        return json.loads(current) if current else None
    
    async def clear(self) -> None:
        redis = await self._get_redis()  # <-- добавил
        await redis.delete(self.queue_key)
    
    async def remove_by_order_id(self, order_id: int) -> bool:
        redis = await self._get_redis()
        raw_items = await redis.lrange(self.queue_key, 0, -1)
        for raw_item in raw_items:
            item = json.loads(raw_item)
            if item.get("order_id") == order_id:
                await redis.lrem(self.queue_key, 1, raw_item)
                return True
        return False


class OrderService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_order(
        self,
        venue_id: int,
        user_fingerprint: str,
        song_data: Dict[str, Any],
        price: int
    ) -> Order:
        order = Order(
            venue_id=venue_id,
            user_fingerprint=user_fingerprint,
            song_title=song_data.get("title"),
            song_artist=song_data.get("artist"),
            song_provider=song_data.get("provider"),
            #song_external_id=song_data.get("external_id"),
            song_duration=song_data.get("duration"),
            price_paid=price,
            status=OrderStatus.PENDING,
            expires_at=datetime.now() + timedelta(minutes=10)
        )
        self.db.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def confirm_payment(self, order_id: int, payment_id: str) -> Order:
        order = await self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} status is {order.status}, not PENDING")
        
        order.status = OrderStatus.PAID
        order.payment_id = payment_id
        await self.db.commit()
        await self.db.refresh(order)
        
        queue_service = QueueService(order.venue_id)
        await queue_service.push(
            order_id=order.id,
            song_data={
                "title": order.song_title,
                "artist": order.song_artist,
                #"external_id": order.song_external_id,
                "provider": order.song_provider,
                "duration": order.song_duration
            }
        )
        return order
    
    async def mark_as_played(self, order_id: int) -> Order:
        order = await self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        order.status = OrderStatus.PLAYED
        order.played_at = datetime.now()
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def mark_as_skipped(self, order_id: int) -> Order:
        order = await self.db.get(Order, order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        order.status = OrderStatus.SKIPPED
        await self.db.commit()
        await self.db.refresh(order)
        return order
    
    async def get_order(self, order_id: int) -> Optional[Order]:
        return await self.db.get(Order, order_id)
    
    async def get_orders_by_venue(
        self,
        venue_id: int,
        status: Optional[OrderStatus] = None,
        limit: Optional[int] = None,
    ):
        query = select(Order).where(Order.venue_id == venue_id)
        if status:
            query = query.where(Order.status == status)
        query = query.order_by(Order.id.desc())
        if limit is not None:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_orders_by_user(self, user_fingerprint: str, limit: int = 10) -> List[Order]:
        query = (
            select(Order)
            .where(Order.user_fingerprint == user_fingerprint)
            .order_by(Order.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()


async def broadcast_queue_update(venue_id: int):
    queue_service = QueueService(venue_id)
    current = await queue_service.get_current()
    queue = await queue_service.get_all()

    await manager.broadcast(
        str(venue_id),
        "queue_update",
        {
            "current": current,
            "queue": queue,
            "total": len(queue)
        }
    )