from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Location(BaseModel):
    district: str
    lat: float
    lng: float


class Telemetry(BaseModel):
    device_id: str
    timestamp: datetime
    location: Location
    pm25: float = Field(ge=0)
    pm10: float = Field(ge=0)
    co: float = Field(ge=0)
    no2: float = Field(ge=0)
    temperature: float
    humidity: float = Field(ge=0, le=100)

