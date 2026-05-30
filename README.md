# Sentio-IT MVP local simulado

MVP para simular nodos IoT de calidad del aire antes de tener sensores físicos.

Incluye dos formas de ejecución:

- **Modo local sin Docker**: servidor HTTP con Python estándar + simulador interno + SQLite.
- **Modo real MQTT sin Docker**: servidor HTTP + listener MQTT en `1883` + SQLite.
- **Modo Docker**: Mosquitto + InfluxDB + backend + simulador MQTT.

## Payload MQTT / Telemetría

```json
{
  "device_id": "sentio-lima-001",
  "timestamp": "2026-05-30T22:30:00Z",
  "location": {
    "district": "San Isidro",
    "lat": -12.0972,
    "lng": -77.0365
  },
  "pm25": 18.4,
  "pm10": 42.1,
  "co": 0.4,
  "no2": 0.02,
  "temperature": 22.5,
  "humidity": 68
}
```

Tópico MQTT:

```text
sentio/devices/{device_id}/telemetry
```

## Ejecutar sin Docker

Backend real para ESP32/Arduino por MQTT:

```bash
python real_mqtt_backend.py
```

Abrir:

```text
http://localhost:8000
```

El ESP32 debe publicar en:

```text
sentio/devices/{device_id}/telemetry
```

Prueba local de MQTT sin placa:

```bash
python test_mqtt_publish.py
curl http://localhost:8000/api/latest
```

Backend con datos simulados internos:

```bash
python local_mvp.py
```

Abrir:

```text
http://localhost:8000
```

## Ejecutar con Docker

Cuando Docker esté instalado:

```bash
docker compose up --build
```

Servicios:

- Dashboard/API: `http://localhost:8000`
- MQTT: `localhost:1883`
- InfluxDB: `http://localhost:8086`

## Endpoints

- `GET /api/health`
- `GET /api/latest`
- `GET /api/readings?limit=100`
- `GET /api/summary`

## Permisos Arduino Nano ESP32

Si la carga falla con `LIBUSB_ERROR_ACCESS`, instalar la regla permanente:

```bash
sudo ./fix_arduino_permissions.sh
```

Luego desconectar y volver a conectar la placa.
