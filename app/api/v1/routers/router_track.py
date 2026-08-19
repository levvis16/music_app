from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.schemas import SongProvider, OrderResponse, OrderStatus, SongSearchResult
from app.services import QueueService, OrderService, broadcast_queue_update
from app.integrations.youtube import youtube_client

router = APIRouter(prefix="/api/v1/track", tags=["track"])

@router.post("/{venue_id}/skip")
async def skip_current(venue_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    order_service = OrderService(db)

    current = await queue_service.get_current()
    if current:
        await order_service.mark_as_skipped(current["order_id"])

    next_track = await queue_service.pop_next()

    await broadcast_queue_update(venue_id)

    return {"status": "skipped", "next": next_track}

@router.post("/{venue_id}/pause")
async def pause_track(venue_id: int):
    return {"status": "paused"}

@router.post("/{venue_id}/resume")
async def resume_track(venue_id: int):
    return {"status": "resumed"}

@router.get("/{venue_id}/history", response_model=List[OrderResponse])
async def get_history(venue_id: int, db: AsyncSession = Depends(get_db), limit: int = 50):
    order_service = OrderService(db)
    orders = await order_service.get_orders_by_venue(
        venue_id=venue_id,
        status=OrderStatus.PLAYED,
        limit=limit,
    )

    return orders

@router.get("/{venue_id}/current")
async def get_current_track(venue_id: int):
    queue_service = QueueService(venue_id)
    current = await queue_service.get_current()

    if not current:
        return {"current": None, "remaining": 0}

    started_at = current.get("started_at")
    duration = current.get("song_duration", 0)

    if started_at:
        elapsed = (datetime.now() - datetime.fromisoformat(started_at)).total_seconds()
        remaining = max(0, duration - elapsed)
    else:
        remaining = duration

    return {
        "current": current,
        "remaining_seconds": int(remaining)
    }

@router.post("/{venue_id}/next")
async def next_track(venue_id: int, db: AsyncSession = Depends(get_db)):
    queue_service = QueueService(venue_id)
    order_service = OrderService(db)

    current = await queue_service.get_current()
    if current:
        await order_service.mark_as_played(current["order_id"])

    next_track = await queue_service.pop_next()
    if next_track:
        current_data = next_track.copy()
        current_data["started_at"] = datetime.now().isoformat()
        pass

    await broadcast_queue_update(venue_id)
    return {"status": "next", "next": next_track}


@router.get("/search", response_model=List[SongSearchResult])
async def search_tracks(
    query: str = Query(..., min_length=1, description="Search query"),
    provider: Optional[SongProvider] = Query(default=SongProvider.YOUTUBE, description="Music provider"),
    limit: int = Query(default=10, ge=1, le=20, description="Maximum number of results"),
):
    """
    Search for music tracks.
    
    Currently supports only YouTube provider.
    Results are cached in Redis for 1 hour.
    """
    if provider != SongProvider.YOUTUBE:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider}' not supported yet. Only 'youtube' is available."
        )
    
    results = await youtube_client.search(query=query, limit=limit)
    return results