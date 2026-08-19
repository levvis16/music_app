from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PLAYED = "played"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


#пускай пока просто висит, в дальнейшем может пригодиться
class SongProvider(str, Enum):
    YOUTUBE = "youtube"
    VK = "vk"
    YANDEX = "yandex"


class VenueBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str
    address: Optional[str] = None
    min_prise: int = Field(default=100, ge=0, alias="min_price")
    max_queue_size: int = Field(default=15, gt=1)
    qr_code_id: str
    is_active: bool = True

class VenueCreate(VenueBase):
    pass

class VenueUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    min_prise: Optional[int] = Field(default=None, ge=0)
    max_queue_size: Optional[int] = Field(default=None, gt=1    )
    is_active: Optional[bool] = None

class VenueResponse(VenueBase):
    id: int
    created_at: datetime


class OrderBase(BaseModel):
    song_title: str = Field(max_length=500)
    song_artist: Optional[str] = Field(default=None, max_length=70)
    song_provider: SongProvider
    song_duration: Optional[int] = Field(default=None, ge=0)

class OrderCreate(BaseModel):
    venue_id: int
    song_title: str = Field(max_length=500)
    song_artist: Optional[str] = Field(default=None, max_length=70)
    song_provider: SongProvider
    #song_external_id: str
    song_duration: Optional[int] = Field(default=None, ge=0)
    price: int = Field(ge=0)

class OrderResponse(BaseModel):
    id: int
    venue_id: int
    song_title: str
    song_artist: Optional[str] = None
    song_provider: Optional[str] = None
    song_duration: Optional[int] = None
    price_paid: int
    payment_id: Optional[str] = None
    status: OrderStatus

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    skip_reason: Optional[str] = Field(default=None, max_length=500)

class PlayLogResponse(BaseModel):
    id: int
    venue_id: int
    order_id: int
    song_title: Optional[str] = None
    song_artist: Optional[str] = None
    song_provider: Optional[str] = None
    skipped: bool
    price_paid: Optional[int] = None
    
    class Config:
        from_attributes = True

class QueueItem(BaseModel):
    order_id: int
    song_title: str 
    song_artist: Optional[str] = None
    song_provider: Optional[str] = None
    song_duration: Optional[int] = None
    position: int

#для интерфейса персонала
class CurrentTrack(BaseModel):
    order_id: int
    song_title: str
    song_artist: Optional[str] = None
    song_provider: Optional[str] = None
    song_duration: Optional[int] = None
    started_at: datetime
    remaining_seconds: Optional[int] = None

class QueueResponse(BaseModel):
    current: Optional[CurrentTrack] = None
    queue: List[QueueItem] = []
    total_in_queue: int
    max_queue_size: int 

class TrackAdd(BaseModel):
    title: str
    artist: Optional[str] = None
    external_id: str
    provider: SongProvider
    duration: Optional[int] = None


class SongSearchResult(BaseModel):
    external_id: str
    title: str
    artist: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    provider: SongProvider

#добавить схемы платежной системы