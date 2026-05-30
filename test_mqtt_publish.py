from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone


def encode_remaining_length(length: int) -> bytes:
    encoded = bytearray()
    while True:
        digit = length % 128
        length //= 128
        if length > 0:
            digit |= 128
        encoded.append(digit)
        if length == 0:
            return bytes(encoded)


def utf8_field(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def packet(packet_type_flags: int, body: bytes) -> bytes:
    return bytes([packet_type_flags]) + encode_remaining_length(len(body)) + body


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MQTT_HOST", "127.0.0.1")
    payload = {
        "device_id": "sentio-test-python-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {"district": "Ate", "lat": -12.0261, "lng": -76.9192},
        "pm25": 42.5,
        "pm10": 91.3,
        "co": 0.7,
        "no2": 0.04,
        "temperature": 24.8,
        "humidity": 70.0,
    }
    topic = "sentio/devices/sentio-test-python-001/telemetry"

    connect_body = (
        utf8_field("MQTT")
        + b"\x04"
        + b"\x02"
        + (60).to_bytes(2, "big")
        + utf8_field("sentio-python-test")
    )
    publish_body = utf8_field(topic) + json.dumps(payload).encode("utf-8")

    with socket.create_connection((host, 1883), timeout=5) as sock:
        sock.sendall(packet(0x10, connect_body))
        response = sock.recv(4)
        if response != b"\x20\x02\x00\x00":
            raise RuntimeError(f"CONNACK invalido: {response!r}")
        sock.sendall(packet(0x30, publish_body))
        sock.sendall(packet(0xE0, b""))

    print(f"Mensaje MQTT de prueba publicado en {host}:1883")


if __name__ == "__main__":
    main()
