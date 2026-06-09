#include <WiFi.h>
#include <PubSubClient.h>
#include <time.h>
#include <DHT.h>
#include "SentioFirmwareConfig.h"

// WiFi
const char* WIFI_SSID = SENTIO_WIFI_SSID;
const char* WIFI_PASSWORD = SENTIO_WIFI_PASSWORD;

// MQTT público VPS
const char* MQTT_HOST = SENTIO_MQTT_HOST;
const int MQTT_PORT = SENTIO_MQTT_PORT;
const char* MQTT_USERNAME = SENTIO_MQTT_USERNAME;
const char* MQTT_PASSWORD = SENTIO_MQTT_PASSWORD;

// Identidad del dispositivo
const char* DEVICE_ID = "sentio-lima-esp32-001";
const char* DISTRICT = "Ate";
const float LATITUDE = -12.0261;
const float LONGITUDE = -76.9192;

const char* FIRMWARE_VERSION = "0.2.2";
const char* DATA_MODE = "partial_real";

// DHT11 conectado al pin D4
#define DHTPIN D4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// HW-028 sensor de lluvia conectado por AO al pin A0
#define RAIN_ANALOG_PIN A0

// LEDs
#define LED_RED D5
#define LED_GREEN D6
#define LED_YELLOW D7
#define GREEN_BRIGHTNESS 128  // 50% de 255

const unsigned long PUBLISH_INTERVAL_MS = 5000;

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastPublishMs = 0;
char telemetryTopic[96];

float randomFloat(float minValue, float maxValue) {
  float value = (float)random(0, 10000) / 10000.0;
  return minValue + value * (maxValue - minValue);
}

float simulatedPm25() {
  float base = 35.0;
  float variation = randomFloat(-12.0, 14.0);
  float value = base + variation;

  if (value < 1.0) {
    return 1.0;
  }

  return value;
}

bool leerDHT(float &temperatura, float &humedad) {
  for (int i = 0; i < 3; i++) {
    humedad = dht.readHumidity();
    temperatura = dht.readTemperature();

    if (!isnan(humedad) && !isnan(temperatura)) {
      return true;
    }

    delay(1000);
  }

  return false;
}

void setLedStatus(bool red, bool green, bool yellow) {
  digitalWrite(LED_RED, red ? HIGH : LOW);
  analogWrite(LED_GREEN, green ? GREEN_BRIGHTNESS : 0);
  digitalWrite(LED_YELLOW, yellow ? HIGH : LOW);
}

void blinkLed(int pin, int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(pin, HIGH);
    delay(delayMs);
    digitalWrite(pin, LOW);
    delay(delayMs);
  }
}

void buildTimestamp(char* buffer, size_t size) {
  struct tm timeinfo;

  if (getLocalTime(&timeinfo, 1000)) {
    strftime(buffer, size, "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return;
  }

  snprintf(buffer, size, "1970-01-01T00:00:%02luZ", (millis() / 1000) % 60);
}

void connectWifi() {
  Serial.print("Conectando a WiFi");

  setLedStatus(false, false, true);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    blinkLed(LED_YELLOW, 1, 80);
  }

  Serial.println();
  Serial.print("WiFi conectado. IP: ");
  Serial.println(WiFi.localIP());

  setLedStatus(false, true, false);
}

void connectMqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Conectando a MQTT...");

    setLedStatus(false, false, true);

    if (mqttClient.connect(DEVICE_ID, MQTT_USERNAME, MQTT_PASSWORD)) {
      Serial.println(" conectado");
      setLedStatus(false, true, false);
    } else {
      Serial.print(" fallo, rc=");
      Serial.print(mqttClient.state());
      Serial.println(". Reintentando en 3s");

      blinkLed(LED_RED, 3, 150);
      delay(3000);
    }
  }
}

void publishTelemetry() {
  char timestamp[32];
  buildTimestamp(timestamp, sizeof(timestamp));

  blinkLed(LED_YELLOW, 1, 100);

  // Datos simulados porque aún no tienes sensores PM, CO o NO2
  float pm25 = simulatedPm25();
  float pm10 = pm25 * randomFloat(1.6, 2.5);
  float co = randomFloat(0.1, 1.4);
  float no2 = randomFloat(0.01, 0.09);

  // Datos reales desde el DHT11
  float temperature;
  float humidity;

  bool okDht = leerDHT(temperature, humidity);

  if (!okDht) {
    Serial.println("Error leyendo DHT11 después de 3 intentos. No se publicará esta lectura.");

    setLedStatus(true, false, false);
    blinkLed(LED_RED, 3, 200);

    return;
  }

  // Lectura real del HW-028 como sensor de lluvia/humedad superficial
  int rainAnalog = analogRead(RAIN_ANALOG_PIN);

  // En este sensor normalmente:
  // 4095 = seco
  // valores menores = más humedad/agua detectada
  float rainPercent = 100.0 - ((rainAnalog / 4095.0) * 100.0);

  const char* rainStatus = "dry";

  if (rainPercent >= 70.0) {
    rainStatus = "wet";
  } else if (rainPercent >= 30.0) {
    rainStatus = "moist";
  } else {
    rainStatus = "dry";
  }

  const char* sensorStatus = "ok";
  const char* alertLevel = "normal";
  const char* alertMessage = "Sin alertas";

  if (temperature >= 30.0 && humidity >= 70.0) {
    alertLevel = "warning";
    alertMessage = "Temperatura y humedad altas";
  } else if (temperature >= 30.0) {
    alertLevel = "warning";
    alertMessage = "Temperatura alta";
  } else if (humidity >= 70.0) {
    alertLevel = "warning";
    alertMessage = "Humedad alta";
  }

  bool hasAlert = strcmp(alertLevel, "normal") != 0;

  if (hasAlert) {
    blinkLed(LED_RED, 2, 150);
  }

  int wifiRssi = WiFi.RSSI();
  unsigned long uptimeMs = millis();

  char payload[1500];

  snprintf(
    payload,
    sizeof(payload),
    "{"
      "\"device_id\":\"%s\","
      "\"timestamp\":\"%s\","
      "\"location\":{"
        "\"district\":\"%s\","
        "\"lat\":%.4f,"
        "\"lng\":%.4f"
      "},"
      "\"pm25\":%.2f,"
      "\"pm10\":%.2f,"
      "\"co\":%.3f,"
      "\"no2\":%.3f,"
      "\"temperature\":%.2f,"
      "\"humidity\":%.2f,"
      "\"rain_analog\":%d,"
      "\"rain_percent\":%.2f,"
      "\"rain_status\":\"%s\","
      "\"wifi_rssi\":%d,"
      "\"uptime_ms\":%lu,"
      "\"sensor_status\":\"%s\","
      "\"firmware_version\":\"%s\","
      "\"data_mode\":\"%s\","
      "\"alert_level\":\"%s\","
      "\"alert_message\":\"%s\","
      "\"temperature_source\":\"DHT11\","
      "\"humidity_source\":\"DHT11\","
      "\"rain_source\":\"HW-028_AO\","
      "\"pm25_source\":\"simulated\","
      "\"pm10_source\":\"simulated\","
      "\"co_source\":\"simulated\","
      "\"no2_source\":\"simulated\""
    "}",
    DEVICE_ID,
    timestamp,
    DISTRICT,
    LATITUDE,
    LONGITUDE,
    pm25,
    pm10,
    co,
    no2,
    temperature,
    humidity,
    rainAnalog,
    rainPercent,
    rainStatus,
    wifiRssi,
    uptimeMs,
    sensorStatus,
    FIRMWARE_VERSION,
    DATA_MODE,
    alertLevel,
    alertMessage
  );

  bool ok = mqttClient.publish(telemetryTopic, payload);

  Serial.print("MQTT topic: ");
  Serial.println(telemetryTopic);

  Serial.print("MQTT payload: ");
  Serial.println(payload);

  Serial.print("Rain analog: ");
  Serial.println(rainAnalog);

  Serial.print("Rain percent: ");
  Serial.println(rainPercent);

  Serial.print("Rain status: ");
  Serial.println(rainStatus);

  Serial.println(ok ? "Publicado" : "Error al publicar");

  if (ok) {
    if (hasAlert) {
      setLedStatus(true, true, false);
    } else {
      setLedStatus(false, true, false);
    }
  } else {
    setLedStatus(true, false, false);
    blinkLed(LED_RED, 3, 150);
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(LED_YELLOW, OUTPUT);

  pinMode(RAIN_ANALOG_PIN, INPUT);

  setLedStatus(false, false, false);

  randomSeed(esp_random());

  dht.begin();

  snprintf(
    telemetryTopic,
    sizeof(telemetryTopic),
    "sentio/devices/%s/telemetry",
    DEVICE_ID
  );

  connectWifi();

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setBufferSize(1600);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setLedStatus(true, false, false);
    connectWifi();
  }

  if (!mqttClient.connected()) {
    setLedStatus(false, false, true);
    connectMqtt();
  }

  mqttClient.loop();

  unsigned long now = millis();

  if (now - lastPublishMs >= PUBLISH_INTERVAL_MS) {
    lastPublishMs = now;
    publishTelemetry();
  }
}
