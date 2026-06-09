const statusEl = document.querySelector("#status");
const nodeStateEl = document.querySelector("#nodeState");
const alertStateEl = document.querySelector("#alertState");
const rainStateEl = document.querySelector("#rainState");
const signalStateEl = document.querySelector("#signalState");
const currentReadingEl = document.querySelector("#currentReading");
const readingsEl = document.querySelector("#readings");
const DEVICE_ID = "sentio-lima-esp32-001";

function formatTime(value) {
  return new Intl.DateTimeFormat("es-PE", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "-";
  }
  return Number(value).toFixed(digits);
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function labelOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : escapeHtml(value);
}

function alertLabel(value) {
  const labels = {
    normal: "Normal",
    warning: "Alerta",
    critical: "Critica",
  };
  return labels[value] || labelOrDash(value);
}

function alertClass(value) {
  if (value === "normal") {
    return "green";
  }
  if (value === "warning") {
    return "orange";
  }
  if (value === "critical") {
    return "red";
  }
  return "yellow";
}

function rainLabel(value) {
  const labels = {
    dry: "Seco",
    moist: "Humedo",
    wet: "Mojado",
  };
  return labels[value] || labelOrDash(value);
}

function rainClass(value) {
  if (value === "dry") {
    return "green";
  }
  if (value === "moist") {
    return "yellow";
  }
  if (value === "wet") {
    return "blue";
  }
  return "gray";
}

function formatUptime(ms) {
  if (ms === null || ms === undefined || Number.isNaN(Number(ms))) {
    return "-";
  }

  const totalSeconds = Math.floor(Number(ms) / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  if (days > 0) {
    return `${days}d ${hours}h`;
  }
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  return `${minutes}m`;
}

function formatRssi(value) {
  return value === null || value === undefined ? "-" : `${formatNumber(value, 0)} dBm`;
}

function formatPercent(value, digits = 0) {
  return value === null || value === undefined ? "-" : `${formatNumber(value, digits)}%`;
}

function formatMilliseconds(value) {
  return value === null || value === undefined ? "-" : `${formatNumber(value, 0)} ms`;
}

function renderCurrentReading(item) {
  if (!item) {
    currentReadingEl.className = "current-reading empty-state";
    currentReadingEl.textContent = "Esperando datos del ESP32";
    nodeStateEl.textContent = "Sin datos";
    alertStateEl.textContent = "-";
    rainStateEl.textContent = "-";
    signalStateEl.textContent = "-";
    return;
  }

  const aq = item.air_quality;
  const alert = item.alert_level || "normal";
  currentReadingEl.className = "current-reading";
  currentReadingEl.innerHTML = `
    <header class="reading-header">
      <div>
        <span class="label">Nodo activo</span>
        <strong>${escapeHtml(item.device_id)}</strong>
        <small>${escapeHtml(item.location.district)} - ${formatTime(item.timestamp)}</small>
      </div>
      <div class="badge-group">
        <span class="badge ${alertClass(alert)}">${alertLabel(alert)}</span>
        <span class="badge ${aq.color}">${escapeHtml(aq.level)}</span>
      </div>
    </header>

    <div class="alert-message ${alert === "normal" ? "is-normal" : ""}">
      ${labelOrDash(item.alert_message)}
    </div>

    <div class="sensor-grid">
      <div class="sensor primary">
        <span>PM2.5</span>
        <strong>${formatNumber(item.pm25)}</strong>
        <small>ug/m3 - ${labelOrDash(item.pm25_source)}</small>
      </div>
      <div class="sensor">
        <span>PM10</span>
        <strong>${formatNumber(item.pm10)}</strong>
        <small>ug/m3 - ${labelOrDash(item.pm10_source)}</small>
      </div>
      <div class="sensor">
        <span>CO</span>
        <strong>${formatNumber(item.co, 3)}</strong>
        <small>ppm - ${labelOrDash(item.co_source)}</small>
      </div>
      <div class="sensor">
        <span>NO2</span>
        <strong>${formatNumber(item.no2, 3)}</strong>
        <small>ppm - ${labelOrDash(item.no2_source)}</small>
      </div>
      <div class="sensor">
        <span>Temperatura</span>
        <strong>${formatNumber(item.temperature)}</strong>
        <small>C - ${labelOrDash(item.temperature_source)}</small>
      </div>
      <div class="sensor">
        <span>Humedad</span>
        <strong>${formatNumber(item.humidity, 0)}</strong>
        <small>% - ${labelOrDash(item.humidity_source)}</small>
      </div>
      <div class="sensor">
        <span>Lluvia</span>
        <strong>${formatPercent(item.rain_percent, 0)}</strong>
        <small>${rainLabel(item.rain_status)} - ${labelOrDash(item.rain_source)}</small>
      </div>
      <div class="sensor">
        <span>Lectura lluvia</span>
        <strong>${formatNumber(item.rain_analog, 0)}</strong>
        <small>analogico</small>
      </div>
      <div class="sensor">
        <span>Senal WiFi</span>
        <strong>${formatRssi(item.wifi_rssi)}</strong>
        <small>RSSI</small>
      </div>
      <div class="sensor">
        <span>Uptime</span>
        <strong>${formatUptime(item.uptime_ms)}</strong>
        <small>${formatMilliseconds(item.uptime_ms)}</small>
      </div>
    </div>

    <dl class="device-meta">
      <div>
        <dt>Firmware</dt>
        <dd>${labelOrDash(item.firmware_version)}</dd>
      </div>
      <div>
        <dt>Modo</dt>
        <dd>${labelOrDash(item.data_mode)}</dd>
      </div>
      <div>
        <dt>Sensor</dt>
        <dd>${labelOrDash(item.sensor_status)}</dd>
      </div>
      <div>
        <dt>Muestras</dt>
        <dd id="currentSamples">-</dd>
      </div>
    </dl>
  `;
  nodeStateEl.textContent = "Activo";
  alertStateEl.textContent = alertLabel(alert);
  rainStateEl.textContent =
    item.rain_percent === null || item.rain_percent === undefined
      ? rainLabel(item.rain_status)
      : `${rainLabel(item.rain_status)} ${formatPercent(item.rain_percent, 0)}`;
  signalStateEl.textContent = formatRssi(item.wifi_rssi);
}

function renderReadings(items) {
  if (!items.length) {
    readingsEl.innerHTML = '<tr><td colspan="11" class="empty-cell">Sin lecturas del ESP32</td></tr>';
    return;
  }

  readingsEl.innerHTML = items
    .slice(0, 15)
    .map((item) => {
      const aq = item.air_quality;
      return `
        <tr>
          <td>${formatTime(item.timestamp)}</td>
          <td>${formatNumber(item.pm25)}</td>
          <td>${formatNumber(item.pm10)}</td>
          <td>${formatNumber(item.co, 3)}</td>
          <td>${formatNumber(item.no2, 3)}</td>
          <td>${formatNumber(item.temperature)} C</td>
          <td>${formatNumber(item.humidity, 0)}%</td>
          <td><span class="badge ${rainClass(item.rain_status)}">${rainLabel(item.rain_status)}</span></td>
          <td>${formatRssi(item.wifi_rssi)}</td>
          <td><span class="badge ${alertClass(item.alert_level || "normal")}">${alertLabel(item.alert_level || "normal")}</span></td>
          <td><span class="badge ${aq.color}">${escapeHtml(aq.level)}</span></td>
        </tr>
      `;
    })
    .join("");
}

async function refresh() {
  try {
    const [latestRes, readingsRes] = await Promise.all([
      fetch("/api/latest"),
      fetch("/api/readings?limit=100"),
    ]);
    const [latest, readings] = await Promise.all([
      latestRes.json(),
      readingsRes.json(),
    ]);
    const matchingLatest = latest.find((item) => item.device_id === DEVICE_ID);
    const deviceLatest = matchingLatest || latest[0] || null;
    const activeDeviceId = deviceLatest && deviceLatest.device_id ? deviceLatest.device_id : DEVICE_ID;
    const deviceReadings = readings.filter((item) => item.device_id === activeDeviceId);
    const avgPm25 =
      deviceReadings.length === 0
        ? null
        : deviceReadings.reduce((total, item) => total + item.pm25, 0) / deviceReadings.length;

    renderCurrentReading(deviceLatest);
    const currentSamplesEl = document.querySelector("#currentSamples");
    if (currentSamplesEl) {
      currentSamplesEl.textContent = deviceReadings.length;
    }
    renderReadings(deviceReadings);
    statusEl.textContent = `Actualizado - PM2.5 prom. ${avgPm25 === null ? "-" : formatNumber(avgPm25)}`;
  } catch (error) {
    statusEl.textContent = "Sin conexion";
  }
}

refresh();
setInterval(refresh, 3000);
