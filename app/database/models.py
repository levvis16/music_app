from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, func, Text

from sqlalchemy.orm import relationship
from database.database import Base
import enum
from datetime import datetime

class OrderStatus(str, enum.Enum):
    PENDING = 'pending'
    PAID = 'paid'
    PLAYED = 'played'
    SKIPPED = 'skipped'
    CANCELLED = 'cancelled'

class Venue(Base):
    __tablename__ = 'venues'
    id = Column(Integer, primary_key= True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(400))
    min_price = Column(Integer, default=100)
    max_queue_size = Column(Integer, default=15)
    qr_code_id = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    orders = relationship("Order", back_populates="venue", cascade="all, delete-orphan")
    play_logs = relationship("PlayLog", back_populates="venue", cascade="all, delete-orphan")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    song_title = Column(String(500), nullable=False)
    song_artist = Column(String(70))
    #song_external_id возможно, если у музыки из внешних сервисов будет id
    song_provider = Column(String(50))
    song_duration = Column(Integer)

    price_paid = Column(Integer, nullable=False)
    payment_id = Column(String(255))

    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)

    venue = relationship("Venue", back_populates="orders")

class PlayLog(Base):
    __tablename__ = 'play_log'
    id = Column(Integer, nullable=False, index=True, primary_key=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False, index=True)

    song_title = Column(String(500))
    song_artist = Column(String(500))
    song_provider = Column(String(50))
    #song_external_id = Column(String(255))

    skipped = Column(Boolean, default=False)
    price_paid = Column(Integer)

    venue = relationship("Venue", back_populates="play_logs")