from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db import Base


class SensorRecordDB(Base):
    __tablename__ = "sensor_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    device_id: Mapped[str] = mapped_column(String(64), index=True)
    plant_id: Mapped[str] = mapped_column(String(64), index=True)
    soil_moisture_raw: Mapped[int] = mapped_column(Integer)
    soil_moisture_percent: Mapped[float] = mapped_column(Float)
    light_lux: Mapped[float] = mapped_column(Float)
    air_temperature: Mapped[float] = mapped_column(Float)
    air_humidity: Mapped[float] = mapped_column(Float)
    pump_status: Mapped[str] = mapped_column(String(16), default="off")
    status: Mapped[str] = mapped_column(String(16), index=True)
    message: Mapped[str] = mapped_column(String(255))


class WateringEventDB(Base):
    __tablename__ = "watering_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    mode: Mapped[str] = mapped_column(String(16), index=True)
    duration_ms: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))


class AdviceRecordDB(Base):
    __tablename__ = "advice_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    plant_id: Mapped[str] = mapped_column(String(64), index=True)
    input_summary: Mapped[str] = mapped_column(Text)
    advice: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(64))
