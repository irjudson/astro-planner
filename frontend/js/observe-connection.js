/**
 * Observe View Connection Management
 *
 * Handles telescope connection and API communication.
 */

const API_BASE = '';  // Same origin

/**
 * Connect to telescope
 */
async function handleConnect() {
  const { status } = observeState.connection;

  // If already connected, disconnect
  if (status === 'connected') {
    await disconnectTelescope();
    return;
  }

  // Connect
  await connectTelescope();
}

/**
 * Connect to telescope
 */
async function connectTelescope() {
  const host = document.getElementById('telescope-host').value;
  const port = parseInt(document.getElementById('telescope-port').value);

  // Update state to connecting
  updateState('connection', {
    status: 'connecting',
    host,
    port,
    error: null
  });

  try {
    const response = await fetch(`${API_BASE}/api/telescope/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, port })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    // Update state to connected
    updateState('connection', {
      status: 'connected',
      firmware: data.firmware || 'Unknown',
      lastUpdate: Date.now()
    });

    // Start telemetry polling
    startTelemetryPolling();

  } catch (error) {
    console.error('Connection failed:', error);
    updateState('connection', {
      status: 'error',
      error: error.message
    });
  }
}

/**
 * Disconnect from telescope
 */
async function disconnectTelescope() {
  try {
    await fetch(`${API_BASE}/api/telescope/disconnect`, {
      method: 'POST'
    });

    // Stop polling
    stopTelemetryPolling();

    // Update state
    updateState('connection', {
      status: 'disconnected',
      firmware: null,
      lastUpdate: null
    });

  } catch (error) {
    console.error('Disconnect failed:', error);
  }
}

/**
 * Telemetry polling
 */
let telemetryPollInterval = null;

function startTelemetryPolling() {
  if (telemetryPollInterval) {
    clearInterval(telemetryPollInterval);
  }

  telemetryPollInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/telescope/status`);
      if (response.ok) {
        const data = await response.json();
        updateState('telemetry', {
          deviceState: data,
          lastUpdate: Date.now()
        });
      }
    } catch (error) {
      console.error('Telemetry update failed:', error);
    }
  }, 1000);  // Poll every 1 second
}

function stopTelemetryPolling() {
  if (telemetryPollInterval) {
    clearInterval(telemetryPollInterval);
    telemetryPollInterval = null;
  }
}

/**
 * Send telescope command
 * @param {string} command - Command name
 * @param {object} params - Command parameters
 * @returns {Promise<any>} Command response
 */
async function sendTelescopeCommand(command, params = {}) {
  const response = await fetch(`${API_BASE}/api/telescope/command/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params)
  });

  if (!response.ok) {
    throw new Error(`Command failed: ${response.statusText}`);
  }

  return response.json();
}
