# Sentio-IT

Dashboard local para recibir telemetria de calidad del aire desde un ESP32 por MQTT.

El alcance actual del proyecto esta enfocado en una estacion real:

```text
sentio-lima-esp32-001
```

## Arquitectura

```text
ESP32 -> MQTT :1883 -> Python backend -> SQLite -> Dashboard/API :8000
```

Componentes principales:

- `real_mqtt_backend.py`: backend principal. Levanta un listener MQTT en `1883`, guarda lecturas en SQLite y sirve el dashboard/API en `8000`.
- `services/backend/app/static/`: HTML, CSS y JavaScript del dashboard.
- `test_mqtt_publish.py`: publicador MQTT local para probar sin placa.
- `local_mvp.py`: modo demo con datos simulados internos.
- `docker-compose.yml`: alternativa Docker con Mosquitto, InfluxDB, backend y simulador.

## Requisitos

Modo recomendado sin Docker:

- Linux, macOS o Windows con Python.
- Python 3.10 o superior.
- Red local donde el ESP32 pueda alcanzar la maquina que ejecuta el backend.

No se requieren dependencias externas para `real_mqtt_backend.py`.

## Ejecutar el backend real

Desde la raiz del proyecto:

```bash
python real_mqtt_backend.py
```

Salida esperada:

```text
MQTT escuchando en 0.0.0.0:1883
Dashboard/API disponible en http://localhost:8000
```

Abrir el dashboard:

```text
http://localhost:8000
```

Si accedes desde otra maquina de la red:

```text
http://IP_DEL_SERVIDOR:8000
```

## Configuracion del ESP32

El ESP32 debe conectarse al broker MQTT usando la IP de la maquina donde corre el backend.

Ejemplo:

```cpp
const char* WIFI_SSID = "BRYAN_2.4G";
const char* WIFI_PASSWORD = "";

const char* MQTT_HOST = "192.168.18.2";
const int MQTT_PORT = 1883;
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
  "humidity": 82.42
}
```

## Firewall

Si el ESP32 conecta a WiFi pero MQTT falla con `rc=-2`, normalmente no puede abrir TCP contra el broker.

En Ubuntu con `ufw`, permitir MQTT desde la LAN:

```bash
sudo ufw allow from 192.168.18.0/24 to any port 1883 proto tcp
sudo ufw reload
```

Para abrir tambien el dashboard en la LAN:

```bash
sudo ufw allow from 192.168.18.0/24 to any port 8000 proto tcp
sudo ufw reload
```

Ajusta `192.168.18.0/24` si tu red usa otro rango.

## Probar sin ESP32

Con el backend corriendo:

```bash
python test_mqtt_publish.py
curl http://localhost:8000/api/latest
```

El dashboard deberia mostrar la lectura de prueba, aunque la UI esta filtrada para la placa real `sentio-lima-esp32-001`.

## API

Endpoints disponibles:

```text
GET /api/health
GET /api/latest
GET /api/readings?limit=100
GET /api/summary
```

Ejemplos:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/latest
```

## Ejecutar como demo local

Si no tienes placa ni MQTT, puedes levantar datos simulados internos:

```bash
python local_mvp.py
```

Abrir:

```text
http://localhost:8000
```

## Ejecutar con Docker

Alternativa para levantar Mosquitto, InfluxDB, backend y simulador:

```bash
docker compose up --build
```

Servicios:

- Dashboard/API: `http://localhost:8000`
- MQTT: `localhost:1883`
- InfluxDB: `http://localhost:8086`

Para el alcance actual de un solo ESP32, el modo sin Docker con `real_mqtt_backend.py` es suficiente.

## Despliegue recomendado

Para una laptop vieja con Ubuntu Server o una VPS pequena:

- CPU: 1 core minimo, 2 cores recomendado.
- RAM: 512 MB minimo, 1-2 GB recomendado.
- Disco: 5 GB minimo, 10-20 GB recomendado.
- Python 3.10+.

Recomendacion practica:

1. Ejecutar `real_mqtt_backend.py` como servicio `systemd`.
2. Exponer el dashboard con Nginx en `80/443`.
3. Mantener MQTT `1883` solo abierto para la LAN o protegerlo antes de exponerlo a internet.

## Permisos Arduino Nano ESP32

Si la carga falla con `LIBUSB_ERROR_ACCESS`, instalar la regla permanente:

```bash
sudo ./fix_arduino_permissions.sh
```

Luego desconectar y volver a conectar la placa.

## Datos locales

Las lecturas se guardan en:

```text
sentio_mvp.sqlite3
```

Ese archivo esta ignorado por Git para no subir datos generados.
