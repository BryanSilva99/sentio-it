# Sentio-IT

Dashboard para recibir telemetria real de calidad del aire desde un ESP32 por MQTT.

El alcance actual del proyecto esta enfocado en una estacion real:

```text
sentio-lima-esp32-001
```

## Arquitectura de servidor

```text
ESP32 -> Mosquitto MQTT publico :1884 -> FastAPI backend -> InfluxDB -> Dashboard/API :8000
```

Componentes principales:

- `docker-compose.yml`: levanta Mosquitto, InfluxDB y el backend.
- `services/backend/`: API, listener MQTT, almacenamiento y dashboard.
- `mosquitto/config/mosquitto.conf`: broker MQTT con autenticacion obligatoria.
- `real_mqtt_backend.py`: backend standalone para uso local sin Docker. Para servidor se recomienda Docker.

El proyecto ya no incluye simuladores ni publicadores de datos de prueba en la ruta de despliegue.

## Requisitos

- Servidor Linux con Docker Engine y Docker Compose.
- Puerto `1884/tcp` accesible desde el ESP32.
- Puerto `8000/tcp` accesible para el dashboard o para Nginx.
- Red y firewall configurados para que la placa pueda llegar al servidor.

## Configuracion

Crea el archivo `.env` desde la plantilla:

```bash
cp .env.example .env
```

Edita `.env` y reemplaza todos los valores `change-this-*` por secretos reales. Usa una clave MQTT que tambien colocaras en el firmware del ESP32.

Variables requeridas:

```text
MQTT_USERNAME
MQTT_PASSWORD
INFLUX_USERNAME
INFLUX_PASSWORD
INFLUX_ORG
INFLUX_BUCKET
INFLUX_TOKEN
```

## Ejecutar en servidor

Desde la raiz del proyecto:

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f backend mosquitto
```

Abrir el dashboard:

```text
http://IP_DEL_SERVIDOR:8000
```

API:

```text
GET /api/health
GET /api/latest
GET /api/readings?limit=100
GET /api/summary
```

## Configuracion del ESP32

El ESP32 debe conectarse al broker MQTT usando la IP o dominio del servidor, el usuario y la clave definidos en `.env`.

El firmware incluido en `SentioFirmwareSimulado.ino` no guarda secretos en Git. Antes de compilarlo en Arduino IDE, crea tu archivo local:

```bash
cp SentioFirmwareConfig.h.example SentioFirmwareConfig.h
```

Luego edita `SentioFirmwareConfig.h` con tu WiFi y la clave MQTT real. Ese archivo esta ignorado por Git.

Ejemplo:

```cpp
const char* WIFI_SSID = "TU_WIFI";
const char* WIFI_PASSWORD = "TU_CLAVE_WIFI";

const char* MQTT_HOST = "IP_DEL_SERVIDOR";
const int MQTT_PORT = 1884;
const char* MQTT_USERNAME = "sentio_device";
const char* MQTT_PASSWORD = "CLAVE_REAL_MQTT";
const char* DEVICE_ID = "sentio-lima-esp32-001";
```

Topico MQTT:

```text
sentio/devices/sentio-lima-esp32-001/telemetry
```

Payload esperado:

```json
{
  "device_id": "sentio-lima-esp32-001",
  "timestamp": "2026-05-30T23:23:31Z",
  "location": {
    "district": "Ate",
    "lat": -12.0261,
    "lng": -76.9192
  },
  "pm25": 48.05,
  "pm10": 90.47,
  "co": 0.483,
  "no2": 0.076,
  "temperature": 25.48,
  "humidity": 82.42,
  "rain_analog": 2800,
  "rain_percent": 31.62,
  "rain_status": "moist",
  "wifi_rssi": -61,
  "uptime_ms": 123456,
  "sensor_status": "ok",
  "firmware_version": "0.2.2",
  "data_mode": "partial_real",
  "alert_level": "warning",
  "alert_message": "Humedad alta",
  "temperature_source": "DHT11",
  "humidity_source": "DHT11",
  "rain_source": "HW-028_AO",
  "pm25_source": "simulated",
  "pm10_source": "simulated",
  "co_source": "simulated",
  "no2_source": "simulated"
}
```

## Firewall

En Ubuntu con `ufw`, permitir MQTT desde la LAN:

```bash
sudo ufw allow from 192.168.18.0/24 to any port 1884 proto tcp
sudo ufw reload
```

Para abrir tambien el dashboard en la LAN:

```bash
sudo ufw allow from 192.168.18.0/24 to any port 8000 proto tcp
sudo ufw reload
```

Ajusta `192.168.18.0/24` si tu red usa otro rango. Si expones el dashboard a internet, coloca Nginx o un proxy equivalente con HTTPS delante del backend.

## Datos

InfluxDB guarda las lecturas en el volumen Docker `influxdb_data`. No borres ese volumen si quieres conservar el historico.

El servicio InfluxDB no publica el puerto `8086` hacia el exterior por defecto; solo el backend accede a el dentro de la red Docker.

## Permisos Arduino Nano ESP32

Si la carga falla con `LIBUSB_ERROR_ACCESS`, instalar la regla permanente:

```bash
sudo ./fix_arduino_permissions.sh
```

Luego desconectar y volver a conectar la placa.
