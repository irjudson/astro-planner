/**
 * Observe View Telemetry Display
 *
 * Handles telemetry data display and updates.
 */

/**
 * Safely format number with fallback
 */
function safeFormatNumber(value, decimals = 1) {
  if (value === null || value === undefined || isNaN(value)) {
    return '--';
  }
  return value.toFixed(decimals);
}

/**
 * Update telemetry display
 */
function updateTelemetryDisplay() {
  const { position, deviceState, lastUpdate } = observeState.telemetry;

  // Guard against missing DOM elements
  const raEl = document.getElementById('telem-ra');
  const decEl = document.getElementById('telem-dec');
  const altEl = document.getElementById('telem-alt');
  const azEl = document.getElementById('telem-az');
  const deviceDiv = document.getElementById('telemetry-device');

  if (!raEl || !decEl || !altEl || !azEl || !deviceDiv) {
    console.warn('Telemetry DOM elements not found');
    return;
  }

  // Update position display
  raEl.textContent = formatRA(position.ra);
  decEl.textContent = formatDec(position.dec);
  altEl.textContent = `${safeFormatNumber(position.alt)}°`;
  azEl.textContent = `${safeFormatNumber(position.az)}°`;

  // Update device status

  if (observeState.connection.status !== 'connected') {
    deviceDiv.innerHTML = '<p class="text-secondary">Not connected</p>';
    return;
  }

  if (Object.keys(deviceState).length === 0) {
    deviceDiv.innerHTML = '<p class="text-secondary">No data available</p>';
    return;
  }

  deviceDiv.innerHTML = `
    <div class="text-sm">
      <div class="mb-sm">
        <span class="text-secondary">Firmware:</span>
        <span>${deviceState.firmware || '--'}</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">Temperature:</span>
        <span>${deviceState.temperature || '--'}°C</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">WiFi:</span>
        <span>${deviceState.wifi_status || '--'}</span>
      </div>
      <div class="mb-sm">
        <span class="text-secondary">Last Update:</span>
        <span>${formatTimestamp(lastUpdate)}</span>
      </div>
    </div>
  `;
}

/**
 * Format RA (hours to HMS)
 */
function formatRA(hours) {
  if (hours === null || hours === undefined || isNaN(hours)) {
    return '--:--:--';
  }

  // Normalize to 0-24 range
  hours = ((hours % 24) + 24) % 24;

  const h = Math.floor(hours);
  const m = Math.floor((hours - h) * 60);
  const s = Math.floor(((hours - h) * 60 - m) * 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

/**
 * Format Dec (degrees to DMS)
 */
function formatDec(degrees) {
  if (degrees === null || degrees === undefined || isNaN(degrees)) {
    return '--°--\'--"';
  }

  // Clamp to valid range
  degrees = Math.max(-90, Math.min(90, degrees));

  const sign = degrees >= 0 ? '+' : '-';
  const absDeg = Math.abs(degrees);
  const d = Math.floor(absDeg);
  const m = Math.floor((absDeg - d) * 60);
  const s = Math.floor(((absDeg - d) * 60 - m) * 60);
  return `${sign}${d}°${m.toString().padStart(2, '0')}'${s.toString().padStart(2, '0')}"`;
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '--';
  const now = Date.now();
  const diff = Math.floor((now - timestamp) / 1000);

  if (diff < 5) return 'Just now';
  if (diff < 60) return `${diff}s ago`;

  const minutes = Math.floor(diff / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

// Subscribe to telemetry state changes
onStateChange('telemetry', updateTelemetryDisplay);
