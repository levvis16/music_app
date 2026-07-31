from fastapi import APIRouter, Depends, HTTPException
from database.schemas import QueueResponse
from app.services import QueueService
router = APIRouter(prefix="admin", tags=['admin'])

@router.get("/queue", response_model=QueueResponse)
async def get_queue(venue_id: int):
    pass