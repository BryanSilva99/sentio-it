from __future__ import annotations

import json
import logging

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from .models import Telemetry
from .settings import settings
from .storage import store

logger = logging.getLogger(__name__)


def on_connect(client: mqtt.Client, _userdata, _flags, reason_code, _properties=None):
    logger.info("Connected to MQTT with code %s", reason_code)
    client.subscribe(settings.mqtt_topic)


def on_message(_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        telemetry = Telemetry.model_validate(payload)
        store.save(telemetry)
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        logger.warning("Invalid telemetry on %s: %s", message.topic, exc)
    except Exception:
        logger.exception("Could not process telemetry")


def start_mqtt_listener() -> mqtt.Client:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if settings.mqtt_username and settings.mqtt_password:
        client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
    client.loop_start()
    return client
