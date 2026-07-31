# app/services.py
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.database.models import Order, OrderStatus
from app.redis_client import get_redis


class QueueService:
    def __init__(self, venue_id: int, redis: Optional[Redis] = None):
        self.venue_id = venue_id
        self.redis = redis or get_redis()
        self.queue_key = f"queue:venue:{venue_id}"
        self.current_key = f"current:venue:{venue_id}"
    
    async def push(self, order_id: int, song_data: Dict[str, Any]) -> int:
        item = json.dumps({
            "order_id": order_id,
            "song_title": song_data.get("title"),
            "song_artist": song_data.get("artist"),
            "song_external_id": song_data.get("external_id"),
            "song_provider": song_data.get("provider"),
            "song_duration": song_data.get("duration")
        })
        return await self.redis.rpush(self.queue_key, item)
    
    async def pop_next(self) -> Optional[Dict[str, Any]]:
        next_item = await self.redis.lpop(self.queue_key)
        if next_item:
            data = json.loads(next_item)
            await self.redis.setex(self.current_key, 3600, next_item)
            return data
        return None
    
    async def get_all(self):
        items = await self.redis.lrange(self.queue_key, 0, -1)
        return [json.loads(item) for item in items]
    
    async def get_current(self):
        current = await self.redis.get(self.current_key)
        return json.loads(current) if current else None
    
    async def clear(self):
        await self.redis.delete(self.queue_key)
    
    async def remove_by_order_id(self, order_id: int) -> bool:
        all_items = await self.get_all()
        for item in all_items:
            if item.get("order_id") == order_id:
                await self.redis.lrem(self.queue_key, 1, json.dumps(item))
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
            song_external_id=song_data.get("external_id"),
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
                "external_id": order.song_external_id,
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
    
    async def get_orders_by_venue(self, venue_id: int, status: Optional[OrderStatus] = None):
        query = select(Order).where(Order.venue_id == venue_id)
        if status:
            query = query.where(Order.status == status)
        query = query.order_by(Order.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()