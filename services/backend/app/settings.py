from __future__ import annotations

import os


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


class Settings:
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "sentio/devices/+/telemetry")
    mqtt_username = os.getenv("MQTT_USERNAME")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    influx_url = os.getenv("INFLUX_URL", "http://localhost:8086")
    influx_token = required_env("INFLUX_TOKEN")
    influx_org = required_env("INFLUX_ORG")
    influx_bucket = required_env("INFLUX_BUCKET")


settings = Settings()
