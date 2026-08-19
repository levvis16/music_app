import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    url_connection: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/music_app")
    
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_max_connections: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")

    class Config():
        env_file = '.env'

settings = Settings()