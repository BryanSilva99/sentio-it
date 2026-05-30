from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


DEVICES = [
    {"device_id": "sentio-lima-001", "district": "San Isidro", "lat": -12.0972, "lng": -77.0365, "base_pm25": 14},
    {"device_id": "sentio-lima-002", "district": "Ate", "lat": -12.0261, "lng": -76.9192, "base_pm25": 38},
    {"device_id": "sentio-lima-003", "district": "Miraflores", "lat": -12.1211, "lng": -77.0297, "base_pm25": 18},
]


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


def main() -> None:
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    topic_prefix = os.getenv("MQTT_TOPIC_PREFIX", "sentio/devices")
    interval = float(os.getenv("SIM_INTERVAL_SECONDS", "3"))

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(mqtt_host, mqtt_port, keepalive=60)
    client.loop_start()

    while True:
        for device in DEVICES:
            payload = build_payload(device)
            topic = f"{topic_prefix}/{device['device_id']}/telemetry"
            client.publish(topic, json.dumps(payload), qos=0)
            print(f"published {topic}: {payload}", flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    main()

