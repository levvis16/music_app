import inspect
import json
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.database.models import Venue
from app.database.schemas import VenueResponse
from app.services import QueueService
from app.websocket.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_remove_by_order_id_uses_raw_redis_value():
    raw_item = json.dumps(
        {
            "order_id": 42,
            "song_title": "Test Song",
            "song_artist": "Artist",
            "song_provider": "youtube",
            "song_duration": 180,
        }
    )
    redis = AsyncMock()
    redis.lrange.return_value = [raw_item]

    service = QueueService(venue_id=1, redis=redis)
    removed = await service.remove_by_order_id(42)

    assert removed is True
    redis.lrem.assert_awaited_once_with("queue:venue:1", 1, raw_item)


@pytest.mark.asyncio
async def test_remove_by_order_id_returns_false_when_missing():
    redis = AsyncMock()
    redis.lrange.return_value = []

    service = QueueService(venue_id=1, redis=redis)
    removed = await service.remove_by_order_id(99)

    assert removed is False
    redis.lrem.assert_not_awaited()


def test_websocket_disconnect_is_sync():
    assert not inspect.iscoroutinefunction(ConnectionManager.disconnect)


def test_venue_response_reads_min_price_from_model():
    venue = Venue(
        id=1,
        name="Test",
        min_price=999,
        max_queue_size=15,
        qr_code_id="qr1",
        is_active=True,
        created_at=datetime.now(),
    )

    response = VenueResponse.model_validate(venue)

    assert response.min_prise == 999
