from __future__ import annotations

import json
import socket
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
HTTP_PORT = 8000
MQTT_PORT = 1883


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


def validate_payload(payload: dict) -> dict:
    location = payload["location"]
    return {
        "device_id": str(payload["device_id"]),
        "timestamp": str(payload.get("timestamp") or datetime.now(timezone.utc).isoformat()),
        "location": {
            "district": str(location["district"]),
            "lat": float(location["lat"]),
            "lng": float(location["lng"]),
        },
        "pm25": float(payload["pm25"]),
        "pm10": float(payload["pm10"]),
        "co": float(payload["co"]),
        "no2": float(payload["no2"]),
        "temperature": float(payload["temperature"]),
        "humidity": float(payload["humidity"]),
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
    item["recommendation"] = "Lectura recibida por MQTT desde un nodo Sentio."
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


def read_remaining_length(conn: socket.socket) -> int | None:
    multiplier = 1
    value = 0
    while True:
        encoded = conn.recv(1)
        if not encoded:
            return None
        digit = encoded[0]
        value += (digit & 127) * multiplier
        if (digit & 128) == 0:
            return value
        multiplier *= 128
        if multiplier > 128 * 128 * 128:
            raise ValueError("MQTT remaining length invalido")


def read_exact(conn: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = conn.recv(remaining)
        if not chunk:
            raise ConnectionError("Cliente MQTT desconectado")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def decode_utf8_field(data: bytes, offset: int) -> tuple[str, int]:
    size = int.from_bytes(data[offset : offset + 2], "big")
    offset += 2
    return data[offset : offset + size].decode("utf-8"), offset + size


def handle_publish(packet_type_flags: int, body: bytes) -> None:
    topic, offset = decode_utf8_field(body, 0)
    qos = (packet_type_flags >> 1) & 0x03
    if qos:
        offset += 2

    raw_payload = body[offset:].decode("utf-8")
    if not topic.startswith("sentio/devices/") or not topic.endswith("/telemetry"):
        print(f"MQTT ignorado topic={topic}")
        return

    payload = validate_payload(json.loads(raw_payload))
    save_reading(payload)
    print(f"MQTT recibido topic={topic} device={payload['device_id']} pm25={payload['pm25']}")


def handle_mqtt_client(conn: socket.socket, address) -> None:
    with conn:
        print(f"MQTT cliente conectado {address[0]}:{address[1]}")
        conn.settimeout(30)
        while True:
            fixed_header = conn.recv(1)
            if not fixed_header:
                return

            packet_type_flags = fixed_header[0]
            packet_type = packet_type_flags >> 4
            remaining_length = read_remaining_length(conn)
            if remaining_length is None:
                return
            body = read_exact(conn, remaining_length)

            if packet_type == 1:
                conn.sendall(b"\x20\x02\x00\x00")
            elif packet_type == 3:
                handle_publish(packet_type_flags, body)
            elif packet_type == 12:
                conn.sendall(b"\xD0\x00")
            elif packet_type == 14:
                return


def run_mqtt_server(stop_event: threading.Event) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", MQTT_PORT))
        server.listen()
        server.settimeout(1)
        print(f"MQTT escuchando en 0.0.0.0:{MQTT_PORT}")
        while not stop_event.is_set():
            try:
                conn, address = server.accept()
            except socket.timeout:
                continue
            thread = threading.Thread(target=handle_mqtt_client, args=(conn, address), daemon=True)
            thread.start()


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
            self.send_json({"status": "ok", "mode": "real-mqtt-backend", "mqtt_port": MQTT_PORT})
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
    mqtt_thread = threading.Thread(target=run_mqtt_server, args=(stop_event,), daemon=True)
    mqtt_thread.start()

    server = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), SentioHandler)
    print(f"Dashboard/API disponible en http://localhost:{HTTP_PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        mqtt_thread.join(timeout=2)
        server.server_close()


if __name__ == "__main__":
    main()
