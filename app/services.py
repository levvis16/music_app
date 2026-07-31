import json
from typing import Optional, Dict, Any
from app.redis_client import get_redis

class QueueService:
    def __init__(self, venue_id: int):
        self.venue_id = venue_id
        self.redis = get_redis()
        self.queue_key = f"queue:venue:{venue_id}"
        self.current_key = f"current:venue:{venue_id}"

    async def push(self, order_id: int, song_data: Dict[str, Any]) -> int:
        item = json.dump({
            "order_id": order_id,
            "song_title": song_data.get("title"),
            "song_artist": song_data.get("artist"),
            #"song_external_id": song_data.get("external_id")
            "song_provider": song_data.get("provider")
        })
        return await self.redis.rpush(self.queue_key, item)

    async def pop_next(self) -> Optional[Dict[str, Any]]:
        next_item = await self.redis.lpop(self.queue_key)
        if next_item:
            data = json.loads(next_item)
            await self.redis.setex(self.current_key, 3600, next_item)
            return data
        return None

    async def get_all(self) -> list[Dict[str,Any]]:
        items = await self.redis.lrange(self.queue_key, 0, -1)
        return [json.loads(items) for item in items]

    async def get_current(self) -> Optional[Dict[str, Any]]:
        current = await self.redis.get(self.current_key)
        return json.loads(current) if current else None

    async def clear_queue(self):
        await self.redis.delete(self.queue_key)