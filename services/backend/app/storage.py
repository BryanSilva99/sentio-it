from __future__ import annotations

from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from .air_quality import classify_pm25, recommendation
from .models import Telemetry
from .settings import settings


class AirQualityStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._recent: deque[dict[str, Any]] = deque(maxlen=500)
        self._latest_by_device: dict[str, dict[str, Any]] = {}
        self._client = InfluxDBClient(
            url=settings.influx_url,
            token=settings.influx_token,
            org=settings.influx_org,
        )
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)

    def save(self, telemetry: Telemetry) -> dict[str, Any]:
        enriched = telemetry.model_dump(mode="json")
        enriched["air_quality"] = classify_pm25(telemetry.pm25)
        enriched["recommendation"] = recommendation(telemetry.pm25)

        point = (
            Point("air_quality")
            .tag("device_id", telemetry.device_id)
            .tag("district", telemetry.location.district)
            .field("pm25", telemetry.pm25)
            .field("pm10", telemetry.pm10)
            .field("co", telemetry.co)
            .field("no2", telemetry.no2)
            .field("temperature", telemetry.temperature)
            .field("humidity", telemetry.humidity)
            .time(telemetry.timestamp)
        )
        self._write_api.write(bucket=settings.influx_bucket, org=settings.influx_org, record=point)

        with self._lock:
            self._recent.appendleft(enriched)
            self._latest_by_device[telemetry.device_id] = enriched
        return enriched

    def latest(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._latest_by_device.values())

    def readings(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._recent)[:limit]

    def summary(self) -> dict[str, Any]:
        readings = self.readings(200)
        if not readings:
            return {
                "devices": 0,
                "samples": 0,
                "avg_pm25": None,
                "worst_level": None,
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
        avg_pm25 = sum(item["pm25"] for item in readings) / len(readings)
        latest_items = self.latest()
        worst = min(latest_items, key=lambda item: item["air_quality"]["score"]) if latest_items else None
        return {
            "devices": len(latest_items),
            "samples": len(readings),
            "avg_pm25": round(avg_pm25, 2),
            "worst_level": worst["air_quality"]["level"] if worst else None,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }


store = AirQualityStore()
