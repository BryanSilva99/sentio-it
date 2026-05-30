const statusEl = document.querySelector("#status");
const nodeStateEl = document.querySelector("#nodeState");
const samplesEl = document.querySelector("#samples");
const avgPm25El = document.querySelector("#avgPm25");
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
  return Number(value).toFixed(digits);
}

function renderCurrentReading(item) {
  if (!item) {
    currentReadingEl.className = "current-reading empty-state";
    currentReadingEl.textContent = "Esperando datos del ESP32";
    nodeStateEl.textContent = "Sin datos";
    return;
  }

  const aq = item.air_quality;
  currentReadingEl.className = "current-reading";
  currentReadingEl.innerHTML = `
    <header class="reading-header">
      <div>
        <span class="label">Nodo activo</span>
        <strong>${item.device_id}</strong>
        <small>${item.location.district} - ${formatTime(item.timestamp)}</small>
      </div>
      <span class="badge ${aq.color}">${aq.level}</span>
    </header>

    <div class="sensor-grid">
      <div class="sensor primary">
        <span>PM2.5</span>
        <strong>${formatNumber(item.pm25)}</strong>
        <small>ug/m3</small>
      </div>
      <div class="sensor">
        <span>PM10</span>
        <strong>${formatNumber(item.pm10)}</strong>
        <small>ug/m3</small>
      </div>
      <div class="sensor">
        <span>CO</span>
        <strong>${formatNumber(item.co, 3)}</strong>
        <small>ppm</small>
      </div>
      <div class="sensor">
        <span>NO2</span>
        <strong>${formatNumber(item.no2, 3)}</strong>
        <small>ppm</small>
      </div>
      <div class="sensor">
        <span>Temperatura</span>
        <strong>${formatNumber(item.temperature)}</strong>
        <small>C</small>
      </div>
      <div class="sensor">
        <span>Humedad</span>
        <strong>${formatNumber(item.humidity, 0)}</strong>
        <small>%</small>
      </div>
    </div>
  `;
  nodeStateEl.textContent = "Activo";
}

function renderReadings(items) {
  if (!items.length) {
    readingsEl.innerHTML = '<tr><td colspan="8" class="empty-cell">Sin lecturas del ESP32</td></tr>';
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
          <td><span class="badge ${aq.color}">${aq.level}</span></td>
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
    const deviceLatest = latest.find((item) => item.device_id === DEVICE_ID);
    const deviceReadings = readings.filter((item) => item.device_id === DEVICE_ID);
    const avgPm25 =
      deviceReadings.length === 0
        ? null
        : deviceReadings.reduce((total, item) => total + item.pm25, 0) / deviceReadings.length;

    samplesEl.textContent = deviceReadings.length;
    avgPm25El.textContent = avgPm25 === null ? "-" : formatNumber(avgPm25);
    renderCurrentReading(deviceLatest);
    renderReadings(deviceReadings);
    statusEl.textContent = "Actualizado";
  } catch (error) {
    statusEl.textContent = "Sin conexion";
  }
}

refresh();
setInterval(refresh, 3000);
