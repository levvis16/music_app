from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.database import get_db
from app.database.models import Venue
from app.database.schemas import VenueCreate, VenueResponse

router = APIRouter(prefix="/api/v1/venues", tags=["venues"])

@router.post("/", response_model=VenueResponse)
async def create_venue(venue_data: VenueCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Venue).where(Venue.qr_code_id == venue_data.qr_code_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="venue already exists")

    venue = Venue(
        name = venue_data.name,
        address = venue_data.address,
        min_price = venue_data.min_prise,
        max_queue_size = venue_data.max_queue_size,
        qr_code_id=venue_data.qr_code_id,
        is_active=venue_data.is_active
    )
    db.add(venue)
    await db.commit()
    await db.refresh(venue)

    return venue

@router.get("/{venue_id}", response_model=VenueResponse)
async def get_venue(venue_id: int, db: AsyncSession = Depends(get_db)):
    venue = await db.get(Venue, venue_id)

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

@router.get("/by-qr/{venue_id}", response_model=VenueResponse)
async def get_venue_by_qr(qr_code_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Venue).where(Venue.qr_code_id == qr_code_id))

    venue = result.scalar_one_or_none()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

@router.get("/", response_model=List[VenueResponse])
async def get_all_venues(db:AsyncSession = Depends(get_db)):
    result = await db.execute(select(Venue))
    return result.scalars().all()

@router.delete("/{venue_id}", response_model=VenueResponse)
async def delete_venue(venue_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.get(Venue, venue_id)
    if not result:
        raise HTTPException(status_code=404, detail="venue doesnt found")
    
    await db.delete(result)
    await db.commit()

    return {"status": "deleted", "venue_id": venue_id}
