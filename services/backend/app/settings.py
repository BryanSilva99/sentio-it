from __future__ import annotations

import os


class Settings:
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "sentio/devices/+/telemetry")
    influx_url = os.getenv("INFLUX_URL", "http://localhost:8086")
    influx_token = os.getenv("INFLUX_TOKEN", "sentio-dev-token")
    influx_org = os.getenv("INFLUX_ORG", "sentio")
    influx_bucket = os.getenv("INFLUX_BUCKET", "air_quality")


settings = Settings()

