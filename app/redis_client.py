import redis.asyncio as redis
from core.config import settings

class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()

        return cls._instance
    
    def _initialize(self):
        self.pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections = settings.redis_max_connections,
            decode_responces = True
        )
        self.client = redis.Redis(connection_pool=self.pool)

    async def get(self) -> redis.Redis:
        return self.client

    async def close(self):
        await self.client.close()
        await self.pool.disconnect()

redis_client = RedisClient()

async def get_redis() -> redis.Redis:
    return await redis_client.get()