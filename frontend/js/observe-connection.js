/**
 * Observe View Connection Management
 *
 * Handles telescope connection and API communication.
 */

const API_BASE = '';  // Same origin

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

  const data = await response.json();
  return data.result;
}

/**
 * Connect to telescope
 */
async function handleConnect() {
  const { status } = observeState.connection;

  // Handle each state explicitly
  if (status === 'connecting') {
    return;  // Ignore clicks while connecting
  }

  if (status === 'connected') {
    await disconnectTelescope();
    return;
  }

  if (status === 'disconnected' || status === 'error') {
    await connectTelescope();
  }
}

/**
 * Connect to telescope
 */
async function connectTelescope() {
  const host = document.getElementById('telescope-host').value.trim();
  const port = parseInt(document.getElementById('telescope-port').value);

  // Validate inputs
  if (!host) {
    updateState('connection', {
      status: 'error',
      error: 'Host address is required'
    });
    return;
  }

  if (isNaN(port) || port < 1 || port > 65535) {
    updateState('connection', {
      status: 'error',
      error: 'Port must be between 1 and 65535'
    });
    return;
  }

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
    stopTelemetryPolling();  // Clean up polling on error
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
  // Only start if not already polling
  if (telemetryPollInterval !== null) {
    return;
  }

  telemetryPollInterval = setInterval(async () => {
    try {
      // Get device state
      const statusResponse = await fetch(`${API_BASE}/api/telescope/status`);
      if (statusResponse.ok) {
        const data = await statusResponse.json();
        updateState('telemetry', {
          deviceState: data,
          lastUpdate: Date.now()
        });
      }

      // Get position (if connected)
      if (observeState.connection.status === 'connected') {
        await updateTelemetryPosition();
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
 * Update telemetry with position data
 */
async function updateTelemetryPosition() {
  try {
    const response = await sendTelescopeCommand('get_current_coordinates');

    updateState('telemetry', {
      position: {
        ra: response.ra || 0,
        dec: response.dec || 0,
        alt: response.alt || 0,
        az: response.az || 0
      }
    });
  } catch (error) {
    console.error('Failed to update position:', error);
  }
}
