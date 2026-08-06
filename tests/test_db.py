# tests/test_db.py
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from sqlalchemy import text
from app.database.database import async_session

async def test():
    async with async_session() as session:
        # Проверяем подключение
        result = await session.execute(text("SELECT 1"))
        print("Подключение к БД:", result.scalar())
        
        # Смотрим таблицы
        result = await session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        tables = result.scalars().all()
        print("Таблицы:", tables)

asyncio.run(test())