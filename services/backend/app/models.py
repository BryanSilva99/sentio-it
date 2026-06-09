from __future__ import annotations

from datetime import datetime
from typing import Literal

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
    rain_analog: int | None = Field(default=None, ge=0)
    rain_percent: float | None = Field(default=None, ge=0, le=100)
    rain_status: Literal["dry", "moist", "wet"] | None = None
    wifi_rssi: int | None = None
    uptime_ms: int | None = Field(default=None, ge=0)
    sensor_status: str | None = None
    firmware_version: str | None = None
    data_mode: str | None = None
    alert_level: str | None = None
    alert_message: str | None = None
    temperature_source: str | None = None
    humidity_source: str | None = None
    rain_source: str | None = None
    pm25_source: str | None = None
    pm10_source: str | None = None
    co_source: str | None = None
    no2_source: str | None = None
