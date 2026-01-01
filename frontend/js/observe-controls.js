/**
 * Observe View Telescope Controls
 *
 * Handles telescope control actions: imaging, focus, goto, execution monitoring.
 */

/**
 * Send telescope command
 * @param {string} command - Command name
 * @param {object} params - Command parameters
 * @returns {Promise<any>} Command response
 */
async function sendTelescopeCommand(command, params = {}) {
  const API_BASE = '';  // Same origin
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

// ============================================================================
// Imaging Controls
// ============================================================================

/**
 * Start preview imaging
 */
async function handleStartPreview() {
  const { connected } = observeState.connection;
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  try {
    const exposure = observeState.controls.imaging.previewExposure;
    await sendTelescopeCommand('start_preview', { exposure });
    console.log('Preview started');
  } catch (error) {
    console.error('Failed to start preview:', error);
    alert('Failed to start preview: ' + error.message);
  }
}

/**
 * Stop preview imaging
 */
async function handleStopPreview() {
  if (observeState.connection.status !== 'connected') return;

  try {
    await sendTelescopeCommand('stop_preview');
    console.log('Preview stopped');
  } catch (error) {
    console.error('Failed to stop preview:', error);
    alert('Failed to stop preview: ' + error.message);
  }
}

/**
 * Start stack imaging
 */
async function handleStartStack() {
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  try {
    const { stackExposure, gain, filter } = observeState.controls.imaging;
    await sendTelescopeCommand('start_stack', {
      exposure: stackExposure,
      gain,
      filter
    });
    console.log('Stack started');
  } catch (error) {
    console.error('Failed to start stack:', error);
    alert('Failed to start stack: ' + error.message);
  }
}

/**
 * Stop stack imaging
 */
async function handleStopStack() {
  if (observeState.connection.status !== 'connected') return;

  try {
    await sendTelescopeCommand('stop_stack');
    console.log('Stack stopped');
  } catch (error) {
    console.error('Failed to stop stack:', error);
    alert('Failed to stop stack: ' + error.message);
  }
}

/**
 * Update imaging settings from UI controls
 */
function handleUpdateImagingSettings() {
  const updates = {
    stackExposure: parseFloat(document.getElementById('stack-exposure').value),
    previewExposure: parseFloat(document.getElementById('preview-exposure').value),
    gain: parseInt(document.getElementById('gain').value),
    gainAuto: document.getElementById('gain-auto').checked,
    filter: document.getElementById('filter-select').value
  };

  updateState('controls', { imaging: updates });
}

// ============================================================================
// Focus Controls
// ============================================================================

/**
 * Start autofocus
 */
async function handleAutofocus() {
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  try {
    await sendTelescopeCommand('autofocus');
    console.log('Autofocus started');
  } catch (error) {
    console.error('Failed to start autofocus:', error);
    alert('Failed to start autofocus: ' + error.message);
  }
}

/**
 * Manual focus adjustment
 * @param {number} steps - Focus steps (positive = out, negative = in)
 */
async function handleManualFocus(steps) {
  if (observeState.connection.status !== 'connected') return;

  try {
    await sendTelescopeCommand('focus_move', { steps });
    console.log(`Focus moved ${steps} steps`);
  } catch (error) {
    console.error('Failed to move focus:', error);
    alert('Failed to move focus: ' + error.message);
  }
}

// ============================================================================
// Goto Controls
// ============================================================================

/**
 * Goto coordinates (RA/Dec)
 */
async function handleGoto() {
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  const raInput = document.getElementById('goto-ra').value.trim();
  const decInput = document.getElementById('goto-dec').value.trim();

  if (!raInput || !decInput) {
    alert('Please enter both RA and Dec coordinates');
    return;
  }

  try {
    // Parse RA (hours) and Dec (degrees)
    const ra = parseCoordinate(raInput, 'ra');
    const dec = parseCoordinate(decInput, 'dec');

    await sendTelescopeCommand('goto', { ra, dec });
    console.log(`Slewing to RA=${ra}, Dec=${dec}`);
  } catch (error) {
    console.error('Failed to goto coordinates:', error);
    alert('Failed to goto coordinates: ' + error.message);
  }
}

/**
 * Goto target by name
 */
async function handleGotoTarget() {
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  const target = document.getElementById('goto-target').value.trim();
  if (!target) {
    alert('Please enter a target name');
    return;
  }

  try {
    await sendTelescopeCommand('goto_target', { target });
    console.log(`Slewing to target: ${target}`);
  } catch (error) {
    console.error('Failed to goto target:', error);
    alert('Failed to goto target: ' + error.message);
  }
}

/**
 * Stop slew/tracking
 */
async function handleStop() {
  if (observeState.connection.status !== 'connected') return;

  try {
    await sendTelescopeCommand('stop_slew');
    console.log('Slew stopped');
  } catch (error) {
    console.error('Failed to stop slew:', error);
    alert('Failed to stop slew: ' + error.message);
  }
}

/**
 * Parse coordinate string to decimal
 * @param {string} coord - Coordinate string (e.g., "12:30:45" or "12.5125")
 * @param {string} type - 'ra' or 'dec'
 * @returns {number} Decimal coordinate
 */
function parseCoordinate(coord, type) {
  // Check if already decimal
  if (!coord.includes(':')) {
    return parseFloat(coord);
  }

  // Parse HMS/DMS format
  const parts = coord.split(':').map(p => parseFloat(p.trim()));
  if (parts.length !== 3 || parts.some(isNaN)) {
    throw new Error(`Invalid ${type} format: ${coord}`);
  }

  const [hours, minutes, seconds] = parts;
  const decimal = hours + (minutes / 60) + (seconds / 3600);

  // Validate range
  if (type === 'ra' && (decimal < 0 || decimal >= 24)) {
    throw new Error('RA must be between 0 and 24 hours');
  }
  if (type === 'dec' && (decimal < -90 || decimal > 90)) {
    throw new Error('Dec must be between -90 and +90 degrees');
  }

  return decimal;
}

// ============================================================================
// Hardware Controls
// ============================================================================

/**
 * Toggle dew heater
 */
async function handleToggleDewHeater() {
  if (observeState.connection.status !== 'connected') return;

  try {
    const enabled = !observeState.controls.dewHeater.enabled;
    const power = observeState.controls.dewHeater.power;

    await sendTelescopeCommand('set_dew_heater', { enabled, power });
    updateState('controls', {
      dewHeater: { enabled, power }
    });
    console.log(`Dew heater ${enabled ? 'enabled' : 'disabled'}`);
  } catch (error) {
    console.error('Failed to toggle dew heater:', error);
    alert('Failed to toggle dew heater: ' + error.message);
  }
}

/**
 * Update dew heater power
 */
async function handleUpdateDewHeaterPower() {
  if (observeState.connection.status !== 'connected') return;

  try {
    const power = parseInt(document.getElementById('dew-heater-power').value);
    const enabled = observeState.controls.dewHeater.enabled;

    if (enabled) {
      await sendTelescopeCommand('set_dew_heater', { enabled: true, power });
    }

    updateState('controls', {
      dewHeater: { power }
    });
  } catch (error) {
    console.error('Failed to update dew heater power:', error);
    alert('Failed to update dew heater power: ' + error.message);
  }
}

// ============================================================================
// Plan Execution
// ============================================================================

/**
 * Start plan execution
 * @param {object} plan - Observation plan to execute
 */
async function handleExecutePlan(plan) {
  if (observeState.connection.status !== 'connected') {
    alert('Not connected to telescope');
    return;
  }

  if (observeState.execution.isExecuting) {
    alert('A plan is already executing');
    return;
  }

  try {
    // Update execution state
    updateState('execution', {
      isExecuting: true,
      currentPlan: plan,
      currentTargetIndex: 0,
      totalTargets: plan.targets.length,
      currentTarget: plan.targets[0],
      currentPhase: 'slewing',
      progress: 0,
      startTime: Date.now(),
      elapsedSeconds: 0,
      estimatedRemainingSeconds: 0,
      framesCurrent: 0,
      framesTotal: 0,
      errors: []
    });

    // Start execution monitoring
    startExecutionPolling();

    // Send execute command to backend
    await sendTelescopeCommand('execute_plan', { plan });
    console.log('Plan execution started');

  } catch (error) {
    console.error('Failed to start plan execution:', error);
    updateState('execution', {
      isExecuting: false,
      errors: [error.message]
    });
    alert('Failed to start plan execution: ' + error.message);
  }
}

/**
 * Stop plan execution
 */
async function handleStopExecution() {
  if (!observeState.execution.isExecuting) return;

  if (!confirm('Are you sure you want to stop the current plan execution?')) {
    return;
  }

  try {
    await sendTelescopeCommand('stop_execution');
    stopExecutionPolling();

    updateState('execution', {
      isExecuting: false,
      currentPhase: 'stopped'
    });

    console.log('Plan execution stopped');
  } catch (error) {
    console.error('Failed to stop execution:', error);
    alert('Failed to stop execution: ' + error.message);
  }
}

/**
 * Skip to next target in plan
 */
async function handleSkipTarget() {
  if (!observeState.execution.isExecuting) return;

  try {
    await sendTelescopeCommand('skip_target');
    console.log('Skipped to next target');
  } catch (error) {
    console.error('Failed to skip target:', error);
    alert('Failed to skip target: ' + error.message);
  }
}

// ============================================================================
// Execution Monitoring
// ============================================================================

let executionPollInterval = null;

/**
 * Start execution polling
 */
function startExecutionPolling() {
  if (executionPollInterval !== null) {
    return;
  }

  executionPollInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/telescope/execution/status`);
      if (response.ok) {
        const status = await response.json();
        updateExecutionState(status);
      }
    } catch (error) {
      console.error('Execution status update failed:', error);
    }
  }, 1000);  // Poll every 1 second
}

/**
 * Stop execution polling
 */
function stopExecutionPolling() {
  if (executionPollInterval) {
    clearInterval(executionPollInterval);
    executionPollInterval = null;
  }
}

/**
 * Update execution state from status
 * @param {object} status - Execution status from API
 */
function updateExecutionState(status) {
  const updates = {
    isExecuting: status.is_executing,
    currentPhase: status.phase,
    progress: status.progress,
    currentTargetIndex: status.current_target_index,
    framesCurrent: status.frames_current,
    framesTotal: status.frames_total
  };

  // Calculate elapsed time
  if (observeState.execution.startTime) {
    updates.elapsedSeconds = Math.floor((Date.now() - observeState.execution.startTime) / 1000);
  }

  // Update current target if index changed
  if (status.current_target_index !== observeState.execution.currentTargetIndex) {
    const plan = observeState.execution.currentPlan;
    if (plan && plan.targets[status.current_target_index]) {
      updates.currentTarget = plan.targets[status.current_target_index];
    }
  }

  // Handle completion
  if (!status.is_executing && observeState.execution.isExecuting) {
    updates.currentPhase = 'complete';
    stopExecutionPolling();
  }

  // Handle errors
  if (status.errors && status.errors.length > 0) {
    updates.errors = status.errors;
  }

  updateState('execution', updates);
}

/**
 * Update execution display (called by UI updates)
 */
function updateExecutionDisplay() {
  const { execution } = observeState;

  // Update execution banner (if exists)
  const banner = document.getElementById('execution-banner');
  if (banner) {
    banner.style.display = execution.isExecuting ? 'flex' : 'none';
  }

  // Update target info (if exists)
  const targetInfo = document.getElementById('info-target');
  if (targetInfo && execution.currentTarget) {
    const target = execution.currentTarget;
    targetInfo.textContent = `${target.name} (${execution.currentTargetIndex + 1}/${execution.totalTargets})`;
  }

  // Update phase info (if exists)
  const phaseInfo = document.getElementById('info-phase');
  if (phaseInfo) {
    phaseInfo.textContent = execution.currentPhase || 'Idle';
  }

  // Update progress (if exists)
  const progressBar = document.getElementById('execution-progress-bar');
  if (progressBar) {
    progressBar.style.width = `${execution.progress}%`;
  }

  // Update frame count (if exists)
  const frameInfo = document.getElementById('info-frames');
  if (frameInfo) {
    frameInfo.textContent = `${execution.framesCurrent}/${execution.framesTotal}`;
  }

  // Update elapsed time (if exists)
  const timeInfo = document.getElementById('info-elapsed');
  if (timeInfo) {
    timeInfo.textContent = formatElapsedTime(execution.elapsedSeconds);
  }

  // Show errors (if exist)
  const errorContainer = document.getElementById('execution-errors');
  if (errorContainer && execution.errors.length > 0) {
    errorContainer.style.display = 'block';
    errorContainer.innerHTML = execution.errors.map(err =>
      `<div class="error-message">${err}</div>`
    ).join('');
  } else if (errorContainer) {
    errorContainer.style.display = 'none';
  }
}

/**
 * Format elapsed seconds as HH:MM:SS
 * @param {number} seconds - Elapsed seconds
 * @returns {string} Formatted time
 */
function formatElapsedTime(seconds) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

// ============================================================================
// State Change Listeners
// ============================================================================

// Listen for execution state changes and update display
onStateChange('execution', updateExecutionDisplay);
