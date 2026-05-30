from __future__ import annotations

import json
import random
import sqlite3
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
DB_PATH = ROOT / "sentio_mvp.sqlite3"
STATIC_DIR = ROOT / "services" / "backend" / "app" / "static"

DEVICES = [
    {"device_id": "sentio-lima-001", "district": "San Isidro", "lat": -12.0972, "lng": -77.0365, "base_pm25": 14},
    {"device_id": "sentio-lima-002", "district": "Ate", "lat": -12.0261, "lng": -76.9192, "base_pm25": 38},
    {"device_id": "sentio-lima-003", "district": "Miraflores", "lat": -12.1211, "lng": -77.0297, "base_pm25": 18},
]


def classify_pm25(pm25: float) -> dict[str, str | int]:
    if pm25 <= 12:
        return {"level": "Bueno", "color": "green", "score": 100}
    if pm25 <= 35.4:
        return {"level": "Moderado", "color": "yellow", "score": 70}
    if pm25 <= 55.4:
        return {"level": "Malo para sensibles", "color": "orange", "score": 45}
    if pm25 <= 150.4:
        return {"level": "Malo", "color": "red", "score": 20}
    return {"level": "Peligroso", "color": "purple", "score": 5}


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                district TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                pm25 REAL NOT NULL,
                pm10 REAL NOT NULL,
                co REAL NOT NULL,
                no2 REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL
            )
            """
        )


def build_payload(device: dict) -> dict:
    pm25 = max(1, random.gauss(device["base_pm25"], 7))
    return {
        "device_id": device["device_id"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {
            "district": device["district"],
            "lat": device["lat"],
            "lng": device["lng"],
        },
        "pm25": round(pm25, 2),
        "pm10": round(pm25 * random.uniform(1.6, 2.5), 2),
        "co": round(random.uniform(0.1, 1.4), 3),
        "no2": round(random.uniform(0.01, 0.09), 3),
        "temperature": round(random.uniform(18, 28), 2),
        "humidity": round(random.uniform(55, 85), 2),
    }


def save_reading(reading: dict) -> None:
    location = reading["location"]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO readings (
                device_id, timestamp, district, lat, lng, pm25, pm10, co, no2, temperature, humidity
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading["device_id"],
                reading["timestamp"],
                location["district"],
                location["lat"],
                location["lng"],
                reading["pm25"],
                reading["pm10"],
                reading["co"],
                reading["no2"],
                reading["temperature"],
                reading["humidity"],
            ),
        )


def row_to_payload(row: sqlite3.Row) -> dict:
    item = {
        "device_id": row["device_id"],
        "timestamp": row["timestamp"],
        "location": {
            "district": row["district"],
            "lat": row["lat"],
            "lng": row["lng"],
        },
        "pm25": row["pm25"],
        "pm10": row["pm10"],
        "co": row["co"],
        "no2": row["no2"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
    }
    item["air_quality"] = classify_pm25(item["pm25"])
    item["recommendation"] = "Datos simulados para validar el flujo del MVP."
    return item


def get_readings(limit: int = 100) -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [row_to_payload(row) for row in rows]


def get_latest() -> list[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT r.*
            FROM readings r
            INNER JOIN (
                SELECT device_id, MAX(id) AS id
                FROM readings
                GROUP BY device_id
            ) latest ON latest.id = r.id
            ORDER BY r.device_id
            """
        ).fetchall()
    return [row_to_payload(row) for row in rows]


def simulator(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        for device in DEVICES:
            save_reading(build_payload(device))
        stop_event.wait(3)


class SentioHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path.removeprefix("/static/"))
            return
        if parsed.path == "/api/health":
            self.send_json({"status": "ok", "mode": "local-sqlite-simulator"})
            return
        if parsed.path == "/api/latest":
            self.send_json(get_latest())
            return
        if parsed.path == "/api/readings":
            query = parse_qs(parsed.query)
            limit = min(max(int(query.get("limit", ["100"])[0]), 1), 500)
            self.send_json(get_readings(limit))
            return
        if parsed.path == "/api/summary":
            latest_items = get_latest()
            reading_items = get_readings(200)
            avg_pm25 = None
            if reading_items:
                avg_pm25 = round(sum(item["pm25"] for item in reading_items) / len(reading_items), 2)
            worst = min(latest_items, key=lambda item: item["air_quality"]["score"]) if latest_items else None
            self.send_json(
                {
                    "devices": len(latest_items),
                    "samples": len(reading_items),
                    "avg_pm25": avg_pm25,
                    "worst_level": worst["air_quality"]["level"] if worst else None,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def serve_static(self, relative_path: str) -> None:
        path = (STATIC_DIR / relative_path).resolve()
        if not path.is_file() or STATIC_DIR.resolve() not in path.parents:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = "text/plain"
        if path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        elif path.suffix == ".html":
            content_type = "text/html; charset=utf-8"
        self.send_file(path, content_type)

    def send_json(self, payload) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(f"{self.address_string()} - {fmt % args}")


def main() -> None:
    init_db()
    stop_event = threading.Event()
    thread = threading.Thread(target=simulator, args=(stop_event,), daemon=True)
    thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", 8000), SentioHandler)
    print("Sentio-IT MVP local disponible en http://localhost:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        thread.join(timeout=2)
        server.server_close()


if __name__ == "__main__":
    main()
